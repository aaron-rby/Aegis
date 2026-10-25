"""Exercise the actual server process on a temporary local port; no camera access."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent


def main():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory() as captures, \
         (ROOT / 'rs.log').open('w', encoding='utf-8') as out, \
         (ROOT / 'rs.err').open('w', encoding='utf-8') as err:
        env = dict(os.environ, SERVER_HOST='127.0.0.1', SERVER_PORT=str(port),
                   CAMERA_URL='', CAPTURE_DIR=captures, PYTHONUNBUFFERED='1')
        process = subprocess.Popen([sys.executable, str(ROOT / 'run_server.py')],
                                   cwd=ROOT, env=env, stdout=out, stderr=err)
        try:
            base = f'http://127.0.0.1:{port}'
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError('Server exited; see rs.err')
                try:
                    health = requests.get(base + '/health', timeout=1)
                    health.raise_for_status()
                    break
                except requests.RequestException:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Server startup exceeded 60 seconds')
                    time.sleep(0.25)
            response = requests.post(base + '/verify',
                                     data=(ROOT/'data/person/coco_000000011699.jpg').read_bytes(),
                                     headers={'Content-Type': 'image/jpeg'}, timeout=60)
            response.raise_for_status()
            assert response.json()['person'] is True
            assert requests.post(base + '/check', timeout=3).status_code == 503
            result = {'health': health.json(), 'verification': response.json(),
                      'camera_unconfigured_returns': 503, 'result': 'PASS'}
            (ROOT/'http-smoke.json').write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
