"""Sentinel local inference and hardware bridge. Run with python app.py."""
from __future__ import annotations

import hmac
import json
import math
import os
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StrictBool
from serial_bridge import SerialBridge

ROOT = Path(__file__).resolve().parent
DATA = Path(os.getenv("SENTINEL_DATA_DIR", str(ROOT / "data")))
DATA.mkdir(parents=True, exist_ok=True)
RECORDS = DATA / "events.json"
TOKEN_FILE = DATA / ".device_token"
if not TOKEN_FILE.exists():
    TOKEN_FILE.write_text(secrets.token_urlsafe(32), encoding="utf-8")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN") or TOKEN_FILE.read_text(encoding="utf-8").strip()
MODEL_PATH = os.getenv("SENTINEL_MODEL", str(ROOT.parent / "ml" / "yolo11n.pt"))
ANIMALS = {"bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"}
TARGETS = ANIMALS | {"person"}
LOCK = threading.RLock()
MODEL_LOCK = threading.Lock()
POOL = ThreadPoolExecutor(max_workers=1)
MODEL = None
MODEL_ERROR = None
HARDWARE: dict = {}
SENSOR_HISTORY = deque(maxlen=1200)
STALE_AFTER_SECONDS = 15
try:
    EVENTS = json.loads(RECORDS.read_text(encoding="utf-8")) if RECORDS.exists() else []
except (ValueError, OSError):
    EVENTS = []
for event in EVENTS:
    if event["status"] in {"queued", "processing"}:
        event.update(status="failed", error="Service restarted. Please submit the media again.")

app = FastAPI(title="Sentinel · Intrusion Detection", version="1.0")
origins = ["http://localhost:8765", "http://127.0.0.1:8765"]
origins += [s.strip() for s in os.getenv("SENTINEL_ORIGINS", "").split(",") if s.strip()]
try:
    site = json.loads((ROOT / ".openai" / "preview-origin.json").read_text())
    origins.append(site["origin"])
except (OSError, ValueError, KeyError):
    pass
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "OPTIONS"],
                   allow_headers=["Content-Type", "X-Device-Token"])


def now():
    return datetime.now(timezone.utc).isoformat()


def record_sample(sample):
    with LOCK:
        # Each sample is a complete snapshot: do not retain another source's old optional fields.
        HARDWARE.clear()
        HARDWARE.update(sample, received_at=now(), received_epoch=time.time())
        SENSOR_HISTORY.append(dict(HARDWARE))


def usb_disconnected():
    with LOCK:
        if HARDWARE.get("transport") == "usb":
            HARDWARE["disconnected"] = True


USB = SerialBridge(record_sample, usb_disconnected)


def persist():
    with LOCK:
        tmp = RECORDS.with_suffix(".tmp")
        tmp.write_text(json.dumps(EVENTS, indent=2), encoding="utf-8")
        tmp.replace(RECORDS)


def model():
    global MODEL, MODEL_ERROR
    if MODEL is None:
        from ultralytics import YOLO
        if not Path(MODEL_PATH).is_file():
            raise RuntimeError("YOLO weights missing. Set SENTINEL_MODEL to a local COCO detection checkpoint.")
        MODEL = YOLO(MODEL_PATH)
        names = set(MODEL.names.values())
        if "person" not in names or not (ANIMALS & names):
            MODEL = None
            raise RuntimeError("Use a COCO detector with person and animal classes, not person-only weights.")
        MODEL_ERROR = None
    return MODEL


def public_event(event):
    return {k: v for k, v in event.items() if k != "input_path"}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "sentinel-local", "hardware_monitor_version": 2,
            "model": Path(MODEL_PATH).name, "model_loaded": MODEL is not None,
            "model_available": Path(MODEL_PATH).is_file(), "model_error": MODEL_ERROR,
            "authorization": "not_implemented", "video_sampling": "At most 120 frames, approximately 1 fps for short clips"}


@app.get("/api/events")
def events():
    with LOCK:
        return [public_event(e) for e in reversed(EVENTS)]


@app.get("/api/events/{event_id}")
def event_detail(event_id: str):
    with LOCK:
        e = next((e for e in EVENTS if e["id"] == event_id), None)
        if not e:
            raise HTTPException(404, "Event not found")
        return public_event(e)


def check_capacity():
    if sum(e["status"] in {"queued", "processing"} for e in EVENTS) >= 4:
        raise HTTPException(429, "Four items are already waiting. Let them finish before uploading more.")
    if len(EVENTS) >= 1000:
        raise HTTPException(507, "Event storage limit reached. Archive the data directory before continuing.")


def enqueue(path, filename, kind, threshold, source="upload", telemetry=None):
    item = {"id": path.parent.name, "filename": filename, "kind": kind, "threshold": threshold,
            "source": source, "created_at": now(), "status": "queued", "progress": 0,
            "input_path": str(path), "frames": [], "authorization": "not_verified",
            "telemetry": telemetry}
    with LOCK:
        EVENTS.append(item)
        persist()
    POOL.submit(process, item)
    return public_event(item)


async def save_upload(upload, path, limit):
    total = 0
    try:
        with path.open("wb") as f:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise HTTPException(413, f"File exceeds {limit // 1024 // 1024} MB limit")
                f.write(chunk)
        if total == 0:
            raise HTTPException(400, "The file is empty")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


@app.post("/api/analyze", status_code=202)
async def analyze(file: UploadFile = File(...), threshold: float = Form(0.70)):
    if not math.isfinite(threshold) or not 0.1 <= threshold <= 0.95:
        raise HTTPException(422, "Confidence threshold must be between 0.10 and 0.95")
    check_capacity()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        kind, limit = "image", 20 * 1024 * 1024
    elif suffix in {".mp4", ".mov", ".avi", ".webm", ".mkv"}:
        kind, limit = "video", 200 * 1024 * 1024
    else:
        raise HTTPException(415, "Choose a JPEG, PNG, WebP, MP4, MOV, AVI, WebM or MKV file")
    folder = DATA / uuid.uuid4().hex
    folder.mkdir()
    path = folder / ("input" + suffix)
    await save_upload(file, path, limit)
    return enqueue(path, Path(file.filename or "upload").name, kind, threshold)


def infer_frame(img, threshold, index, second, folder):
    # Bound output resolution while retaining original aspect ratio.
    h, w = img.shape[:2]
    if h * w > 40_000_000:
        raise ValueError("Image exceeds the 40 megapixel processing limit")
    if max(h, w) > 1600:
        img = cv2.resize(img, (round(w * 1600 / max(h, w)), round(h * 1600 / max(h, w))))
    t0 = time.perf_counter()
    m = model()
    classes = [i for i, name in m.names.items() if name in TARGETS]
    result = m.predict(img, classes=classes, conf=threshold, imgsz=640, verbose=False, device="cpu")[0]
    detections = [{"label": result.names[int(b.cls[0])], "confidence": round(float(b.conf[0]), 4),
                   "box": [round(float(v), 1) for v in b.xyxy[0]]} for b in result.boxes]
    people = sum(d["label"] == "person" for d in detections)
    animals = sum(d["label"] in ANIMALS for d in detections)
    annotated = result.plot()
    target = folder / f"frame-{index:04d}.jpg"
    if not cv2.imwrite(str(target), annotated):
        raise ValueError("Unable to save annotated frame")
    return {"index": index, "second": round(second, 2), "people": people, "animals": animals,
            "detections": detections, "ms": round((time.perf_counter() - t0) * 1000, 1),
            "preview": f"/api/media/{folder.name}/{target.name}"}


def process(item):
    global MODEL_ERROR
    cap = None
    try:
        item.update(status="processing", progress=2)
        path = Path(item["input_path"])
        with MODEL_LOCK:
            model()  # Serialize model initialization and inference.
            if item["kind"] == "image":
                img = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("This file could not be decoded as an image")
                frames = [infer_frame(img, item["threshold"], 0, 0, path.parent)]
                duration, interval = 0, None
                item["frames"] = frames
            else:
                cap = cv2.VideoCapture(str(path))
                if not cap.isOpened():
                    raise ValueError("Video codec could not be decoded. Try an H.264 MP4.")
                fps, count = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if not math.isfinite(fps) or not math.isfinite(count) or fps <= 0 or count <= 0:
                    raise ValueError("Video frame count or frame rate is unavailable")
                duration = count / fps
                if duration > 300:
                    raise ValueError("Video is longer than five minutes. Upload a shorter clip.")
                sample_count = min(120, max(1, math.ceil(duration)))
                interval = max(1, duration / sample_count)
                frames = []
                for index in range(sample_count):
                    second = index * interval
                    cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
                    ok, img = cap.read()
                    if not ok:
                        raise ValueError(f"Video decoding failed near {second:.1f}s. Partial results are not a completed analysis.")
                    frames.append(infer_frame(img, item["threshold"], index, second, path.parent))
                    with LOCK:
                        item.update(frames=list(frames), progress=round(100 * (index + 1) / sample_count))
            best = max(frames, key=lambda f: (f["people"] > 0, f["animals"] > 0,
                       max((d["confidence"] for d in f["detections"]), default=0)))
            person_frames = sum(f["people"] > 0 for f in frames)
            animal_frames = sum(f["animals"] > 0 for f in frames)
            decision = "person" if person_frames else "animal" if animal_frames else "unconfirmed"
            with LOCK:
                item.update(status="complete", progress=100, frames=frames, decision=decision,
                            preview=best["preview"], duration=round(duration, 2), sample_interval=interval,
                            sampled_frames=len(frames), person_frames=person_frames, animal_frames=animal_frames,
                            peak_people=max(f["people"] for f in frames), peak_animals=max(f["animals"] for f in frames),
                            inference_ms=round(sum(f["ms"] for f in frames), 1), completed_at=now())
    except Exception as exc:
        if MODEL is None:
            MODEL_ERROR = str(exc)
        item.update(status="failed", error=str(exc), completed_at=now())
    finally:
        if cap is not None:
            cap.release()
        # Keep annotated evidence and JSON only; do not retain original uploads.
        Path(item["input_path"]).unlink(missing_ok=True)
        persist()


def device_auth(token):
    if not token or not hmac.compare_digest(token, DEVICE_TOKEN):
        raise HTTPException(401, "Missing or invalid X-Device-Token")


class Telemetry(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    pir: StrictBool
    distance_cm: float | None = Field(ge=0, le=1000, allow_inf_nan=False, strict=True)
    camera_ready: StrictBool | None = None
    buzzer_active: StrictBool | None = None
    rssi: int | None = Field(default=None, ge=-150, le=0)


@app.post("/api/hardware/telemetry")
def telemetry(payload: Telemetry, x_device_token: str | None = Header(default=None)):
    device_auth(x_device_token)
    record_sample({**payload.model_dump(), "transport": "wifi"})
    return {"accepted": True, "received_at": HARDWARE["received_at"]}


@app.get("/api/hardware")
def hardware():
    with LOCK:
        snapshot = {**HARDWARE, "online": bool(HARDWARE) and not HARDWARE.get("disconnected", False)
                    and time.time() - HARDWARE["received_epoch"] < STALE_AFTER_SECONDS,
                    "stale_after_seconds": STALE_AFTER_SECONDS,
                    "sample_age_seconds": max(0, time.time() - HARDWARE["received_epoch"]) if HARDWARE else None,
                    "history": [dict(p) for p in SENSOR_HISTORY if p["received_epoch"] >= time.time() - 60]}
    # Avoid acquiring the USB lock while holding the sensor lock (reader uses the reverse order).
    snapshot["serial"] = USB.status()
    if snapshot.get("transport") == "usb":
        snapshot["online"] = snapshot["online"] and snapshot["serial"].get("connected", False) and (
            snapshot.get("session_id") == snapshot["serial"].get("session_id"))
    return snapshot


@app.get("/api/serial/ports")
def serial_ports():
    return {"ports": USB.ports(), "status": USB.status()}


class SerialConnection(BaseModel):
    port: str = Field(min_length=1, max_length=100)
    baudrate: int = 115200


def allow_serial_control(request):
    # Port control belongs to the laptop, even if the service is bound to the LAN.
    if not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(403, "Open Sentinel on the laptop to control its USB connection")
    origin = request.headers.get("origin")
    if origin and origin not in origins:
        raise HTTPException(403, "This website origin is not allowed to control USB")


@app.post("/api/serial/connect")
def serial_connect(payload: SerialConnection, request: Request):
    allow_serial_control(request)
    try:
        return USB.connect(payload.port, payload.baudrate)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/serial/disconnect")
def serial_disconnect(request: Request):
    allow_serial_control(request)
    try:
        return USB.disconnect()
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/hardware/frame", status_code=202)
async def hardware_frame(request: Request, x_device_token: str | None = Header(default=None)):
    device_auth(x_device_token)
    check_capacity()
    folder = DATA / uuid.uuid4().hex
    folder.mkdir()
    path = folder / "input.jpg"
    total = 0
    try:
        with path.open("wb") as f:
            async for chunk in request.stream():
                total += len(chunk)
                if total > 20 * 1024 * 1024:
                    raise HTTPException(413, "JPEG exceeds 20 MB")
                f.write(chunk)
        if not total:
            raise HTTPException(400, "Empty camera frame")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return enqueue(path, "ESP32-CAM capture.jpg", "image", 0.70, "hardware", dict(HARDWARE))


@app.get("/api/media/{event_id}/{filename}")
def media(event_id: str, filename: str):
    import re
    if not re.fullmatch(r"[a-f0-9]{32}", event_id) or not re.fullmatch(r"frame-\d{4}\.jpg", filename):
        raise HTTPException(404)
    path = DATA / event_id / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")


app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="website")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("SENTINEL_HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8765")))
