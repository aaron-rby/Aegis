"""Collect training/test photos straight from the ESP32-CAM.

    python collect_camera.py person 30        # 30 photos with a person   -> data/person/
    python collect_camera.py no_person 30     # 30 photos without anyone  -> data/no_person/
    python collect_camera.py screen 30        # 30 photos of people on screens/prints -> data/screen_negatives/

A photo is taken every 3 seconds, so move, pose and change the lighting between shots.
Close every camera preview page first (the camera serves one request at a time).
"""
import os
from pathlib import Path
import sys
import time
import uuid

import requests
from test_camera import validate_jpeg

FOLDERS = {"person": "data/person", "no_person": "data/no_person", "screen": "data/screen_negatives"}
if len(sys.argv) < 2 or sys.argv[1] not in FOLDERS:
    raise SystemExit(__doc__)
kind, count = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30

url = os.getenv("CAMERA_URL", "")
if not url:
    raise SystemExit("Set CAMERA_URL to the camera capture endpoint first")
raw = os.getenv("CAMERA_TOKEN") or input("Camera token (Enter if none): ")
token = "".join(c for c in raw if 32 < ord(c) < 127 and c not in "\"'")

out = Path(__file__).resolve().parent / FOLDERS[kind]
out.mkdir(parents=True, exist_ok=True)
saved = 0
failures = 0
if count < 1:
    raise SystemExit("Photo count must be positive")
print(f"Saving {count} '{kind}' photos to {out}. Get ready...")
time.sleep(3)
while saved < count:
    try:
        r = requests.request(os.getenv("CAMERA_METHOD", "POST"), url, headers={"X-Camera-Token": token}, timeout=20)
        ok = r.status_code == 200 and r.content.rstrip(b"\x00").endswith(b"\xff\xd9")
        if ok:
            validate_jpeg(r.content)
    except (requests.RequestException, ValueError):
        ok = False
    if ok:
        failures = 0
        saved += 1
        (out / f"esp32_{kind}_{time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]}_{saved:03d}.jpg").write_bytes(r.content)
        print(f"  {saved}/{count} saved")
    else:
        failures += 1
        if failures >= 5:
            raise SystemExit("Five consecutive capture failures; check camera address and credentials")
        print("  photo failed, retrying...")
    time.sleep(3)
print("Done. Next: python evaluate.py")
