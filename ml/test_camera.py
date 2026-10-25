"""Capture and validate one ESP32-CAM JPEG without running the ML model."""
import argparse
import os
import sys
from pathlib import Path
import cv2
import numpy as np
import requests

ROOT = Path(__file__).resolve().parent


def validate_jpeg(data):
    if not data.startswith(b'\xff\xd8') or not data.rstrip(b'\x00').endswith(b'\xff\xd9'):
        raise ValueError('Incomplete JPEG: missing start/end markers')
    try:
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except cv2.error as exc:
        raise ValueError('Cannot decode camera JPEG') from exc
    if image is None or image.size == 0:
        raise ValueError('Cannot decode camera JPEG')
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'test_cam.jpg')
    args = parser.parse_args()
    url = os.getenv('CAMERA_URL', '')
    if not url:
        parser.error('Set CAMERA_URL to the camera capture endpoint first')
    raw = os.getenv('CAMERA_TOKEN')
    if raw is None:
        raw = input('Camera token (Enter if none): ')
    token = ''.join(c for c in raw if 32 < ord(c) < 127 and c not in "\"'")
    headers = {'X-Camera-Token': token} if token else {}
    auth = (os.environ['CAMERA_USER'], os.getenv('CAMERA_PASS', '')) if os.getenv('CAMERA_USER') else None
    try:
        response = requests.request(os.getenv('CAMERA_METHOD', 'POST'), url,
                                    headers=headers, auth=auth, timeout=20)
        response.raise_for_status()
        if not response.headers.get('content-type', '').lower().startswith('image/jpeg'):
            raise ValueError('Camera response is not image/jpeg')
        validate_jpeg(response.content)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(response.content)
    except (requests.RequestException, ValueError, OSError) as exc:
        print(f'Camera test failed: {exc}', file=sys.stderr)
        return 1
    print(f'SUCCESS: verified JPEG saved to {args.output} ({len(response.content)} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
