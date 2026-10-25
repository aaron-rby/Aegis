"""Persistent job, crash recovery, artifacts, heartbeat, and lock checks."""
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import Store
from worker import exclusive_worker_lock, process_job


class FakeDetector:
    @staticmethod
    def load_image(path):
        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None: raise ValueError("bad image")
        return image

    @staticmethod
    def verify_person(image, conf=0.35):
        return {"person": True, "confidence": 0.8, "count": 1,
                "boxes": [{"box": [2, 2, 20, 20], "confidence": 0.8}], "ms": 1.0}

    @staticmethod
    def annotate(image, result): return image.copy()


class WorkerTest(unittest.TestCase):
    def test_five_jobs_recover_and_finish(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captures, predictions = root / "captures", root / "predictions"
            captures.mkdir()
            predictions.mkdir()
            store = Store(root / "app.sqlite3", captures, predictions)
            stream = BytesIO()
            Image.new("RGB", (40, 40), "green").save(stream, format="JPEG")
            for n in range(1, 6):
                photo = captures / f"582ABD7BB88C-3cae8d1e-1-{n}.jpg"
                photo.write_bytes(stream.getvalue())
                store.add_photo(photo)
            self.assertEqual(store.status(root / "model.pt")["jobs"]["queued"], 5)
            first = store.claim_job("crashed-worker")
            self.assertEqual(first["id"], "582ABD7BB88C-3cae8d1e-1-1")
            self.assertEqual(store.recover_processing(), 1)
            self.assertEqual(store.status(root / "model.pt")["jobs"]["queued"], 5)
            store.heartbeat("new-worker", root / "model.pt")
            self.assertTrue(store.status(root / "model.pt")["worker"]["running"])
            for _ in range(5):
                job = store.claim_job("new-worker")
                state, record = process_job(store, job, FakeDetector, cv2, root / "model.pt", 0.35)
                self.assertEqual(state, "person_detected")
                self.assertTrue((predictions / record["annotated_image"]).is_file())
                self.assertTrue((predictions / f"{job['id']}-ml.json").is_file())
            self.assertIsNone(store.claim_job("new-worker"))
            with store.connect() as db:
                rows = db.execute("SELECT state,attempts FROM ml_jobs ORDER BY photo_id").fetchall()
            self.assertEqual([row["state"] for row in rows], ["person_detected"] * 5)
            self.assertEqual([row["attempts"] for row in rows], [2, 1, 1, 1, 1])
            self.assertFalse(list(predictions.glob("*.part")))
            store.clear_heartbeat("new-worker")
            self.assertFalse(store.status(root / "model.pt")["worker"]["running"])

    def test_second_worker_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "worker.lock"
            with exclusive_worker_lock(lock):
                with self.assertRaises(RuntimeError):
                    with exclusive_worker_lock(lock): pass

    def test_ml_alarm_requires_fresh_person_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captures, predictions = root / "captures", root / "predictions"
            captures.mkdir()
            predictions.mkdir()
            store = Store(root / "app.sqlite3", captures, predictions)
            self.assertIsNone(store.latest_alarm_event())
            first = captures / "582ABD7BB88C-3cae8d1e-1-1.jpg"
            first.write_bytes(b"test")
            store.add_photo(first)
            job = store.claim_job("worker")
            store.finish_job(job["id"], "no_person_detected", {"person": False})
            self.assertIsNone(store.latest_alarm_event())
            second = captures / "582ABD7BB88C-3cae8d1e-1-2.jpg"
            second.write_bytes(b"test")
            store.add_photo(second)
            job = store.claim_job("worker")
            store.finish_job(job["id"], "person_detected", {"person": True})
            self.assertEqual(store.latest_alarm_event(), "582ABD7BB88C-3cae8d1e-1")
            with store.connect() as db:
                db.execute("UPDATE ml_jobs SET finished_at='2020-01-01T00:00:00+00:00' WHERE photo_id=?",
                           (job["id"],))
            self.assertIsNone(store.latest_alarm_event())

    def test_missing_source_becomes_error_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captures, predictions = root / "captures", root / "predictions"
            captures.mkdir()
            predictions.mkdir()
            store = Store(root / "app.sqlite3", captures, predictions)
            source = captures / "582ABD7BB88C-3cae8d1e-2-1.jpg"
            stream = BytesIO()
            Image.new("RGB", (40, 40), "green").save(stream, format="JPEG")
            source.write_bytes(stream.getvalue())
            store.add_photo(source)
            job = store.claim_job("worker")
            source.unlink()
            state, record = process_job(store, job, FakeDetector, cv2, root / "model.pt", 0.35)
            self.assertEqual(state, "error")
            self.assertEqual(record["classification"], "PROCESSING ERROR")
            self.assertTrue((predictions / f"{job['id']}-ml.json").is_file())
            self.assertEqual(store.status(root / "model.pt")["jobs"]["errors"], 1)


if __name__ == "__main__": unittest.main()
