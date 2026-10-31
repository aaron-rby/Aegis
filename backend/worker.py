"""Single-instance YOLO worker for durable camera-upload jobs."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import uuid

from server import load_config
from storage import Store


@contextmanager
def exclusive_worker_lock(path: Path):
    """OS-held lock is released even if the process crashes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Another ML worker already owns this database") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def atomic_write(path: Path, data: bytes):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".part", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists(): temporary.unlink()


def process_job(store: Store, job: dict, detector, cv2, model: Path, confidence: float):
    identifier = job["id"]
    source = Path(job["file_path"])
    image_payload = None
    if not store.job_is_processing(identifier): return "cancelled", {"classification": "ANALYSIS CANCELLED"}
    record = {"source": str(source), "processed_at": datetime.now(timezone.utc).isoformat(),
              "model": str(model), "threshold": confidence, "authorization": "not_evaluated"}
    try:
        if source.resolve().parent != store.captures or source.stem != identifier:
            raise ValueError("Job source is outside the capture directory")
        image = detector.load_image(source)
        result = detector.verify_person(image, conf=confidence)
        if not store.job_is_processing(identifier): return "cancelled", {"classification": "ANALYSIS CANCELLED"}
        record.update(result)
        record["classification"] = "PERSON DETECTED" if result["person"] else "NO PERSON DETECTED"
        annotated = detector.annotate(image, result)
        annotated[:45] = image[:45]
        cv2.putText(annotated, record["classification"], (8, 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 0, 255) if result["person"] else (0, 200, 200), 2)
        ok, encoded = cv2.imencode(".jpg", annotated)
        if not ok: raise ValueError("Could not encode annotation")
        image_name = f"{identifier}-ml.jpg"
        image_payload = (store.predictions / image_name, encoded.tobytes())
        record["annotated_image"] = image_name
        state = "person_detected" if result["person"] else "no_person_detected"
        error = None
    except Exception as exc:
        record.update(classification="PROCESSING ERROR", error=str(exc), person=False,
                      confidence=0.0, count=0, annotated_image=None)
        state, error = "error", str(exc)
    record["processed_at"] = datetime.now(timezone.utc).isoformat()
    def write_artifacts():
        if image_payload is not None: atomic_write(*image_payload)
        atomic_write(store.predictions / f"{identifier}-ml.json", json.dumps(record, indent=2).encode("utf-8"))
    # Commit cancellation/result atomically with the DB lock; late results cannot win.
    if not store.finish_job(identifier, state, record, error, write_artifacts=write_artifacts):
        return "cancelled", {"classification": "ANALYSIS CANCELLED"}
    return state, record


def run(config_path: Path, once: bool = False, poll_seconds: float = 0.5):
    config = load_config(config_path)
    if not 0 < poll_seconds <= 30: raise ValueError("Poll interval must be in (0,30]")
    store = Store(config["database"], config["capture_dir"], config["prediction_dir"])
    worker_id = uuid.uuid4().hex
    lock_path = Path(config["database"]).with_suffix(".worker.lock")
    with exclusive_worker_lock(lock_path):
        os.environ["MODEL_NAME"] = str(config["model_path"])
        os.environ["CONF_THRESHOLD"] = "0.35"
        os.environ["IMG_SIZE"] = "960"
        ml_dir = Path(__file__).resolve().parents[1] / "ml"
        sys.path.insert(0, str(ml_dir))
        try:
            import cv2
            import detector
            print("Loading local YOLO11m and warming up...", flush=True)
            detector.get_model()
        except Exception as exc:
            raise RuntimeError(f"Could not load configured ML model {config['model_path']}: {exc}") from exc
        print(f"Model ready: {config['model_path']}", flush=True)
        recovered = store.recover_processing()
        print(f"Recovered {recovered} abandoned processing job(s).", flush=True)
        stopped = threading.Event()

        def heartbeat_loop():
            while not stopped.is_set():
                try: store.heartbeat(worker_id, config["model_path"])
                except Exception as exc: print(f"Heartbeat error: {exc}", flush=True)
                stopped.wait(5)

        heartbeat = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat.start()
        try:
            while True:
                job = store.claim_job(worker_id)
                if job:
                    state, record = process_job(store, job, detector, cv2, config["model_path"], 0.35)
                    print(f"{job['id']}: {state} confidence={record.get('confidence')} {record.get('error','')}", flush=True)
                elif once:
                    return
                else:
                    time.sleep(poll_seconds)
        finally:
            stopped.set()
            heartbeat.join(timeout=10)
            store.clear_heartbeat(worker_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.local.json"))
    parser.add_argument("--once", action="store_true", help="Process all queued jobs, then exit")
    args = parser.parse_args()
    try: run(args.config, once=args.once)
    except (RuntimeError, OSError, ValueError) as exc:
        parser.exit(1, f"WORKER STARTUP ERROR: {exc}\n")


if __name__ == "__main__": main()
