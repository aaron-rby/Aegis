"""Start/reuse the local Sentinel service, then open its hardware menu.

This launcher never opens COM ports, sends serial commands, or stops processes.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8765"
OPENER = build_opener(ProxyHandler({}))


def probe():
    try:
        with OPENER.open(URL + "/api/health", timeout=1) as response:
            data = json.loads(response.read(65536))
    except HTTPError as exc:
        raise RuntimeError(f"Port 8765 is occupied, but its health endpoint returned HTTP {exc.code}. No second server was started.") from exc
    except (URLError, TimeoutError, OSError):
        return None
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Port 8765 returned an unrecognized response. No second server was started.") from exc
    known = isinstance(data, dict) and data.get("status") == "ok" and (
        data.get("service") == "sentinel-local" or
        (data.get("authorization") == "not_implemented" and "model_available" in data and "video_sampling" in data))
    if not known:
        raise RuntimeError("A different service is using port 8765. Leave it running and resolve the port conflict before retrying.")
    return data


@contextmanager
def startup_lock(path, timeout=40):
    """Cross-process lock: two simultaneous launcher clicks cannot start two services."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Another Sentinel launcher is still starting the service. Wait a moment and retry.")
                time.sleep(0.2)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def ensure_service(root=ROOT, timeout=30):
    data = probe()
    if data:
        return data, False
    with startup_lock(root / "data" / ".hardware-start.lock"):
        data = probe()
        if data:
            return data, False
        # An occupied but unresponsive port is not permission to start another
        # server. Windows exclusive bind also detects an existing listener.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
                if os.name == "nt":
                    check.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                check.bind(("127.0.0.1", 8765))
        except OSError as exc:
            raise RuntimeError("Port 8765 is occupied but the service is not responding. No duplicate was started. Check the existing service terminal.") from exc
        log_path = root / "data" / "hardware-service.log"
        env = dict(os.environ, PORT="8765", PYTHONUNBUFFERED="1")
        # Preserve a configured LAN bind, otherwise retain the service's local default.
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        with log_path.open("ab", buffering=0) as log:
            log.write(f"\n--- Hardware launcher {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n".encode())
            child = subprocess.Popen([sys.executable, str(root / "app.py")], cwd=root,
                                     env=env, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, creationflags=flags,
                                     start_new_session=os.name != "nt")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = probe()
            if data:
                return data, True
            if child.poll() is not None:
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                raise RuntimeError(f"Python service exited with code {child.returncode}.\n{detail}\nLog: {log_path}")
            time.sleep(0.3)
        raise RuntimeError(f"The service did not respond within {timeout} seconds. It has not been killed. Check {log_path} before retrying.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help="Check startup without opening a browser")
    args = parser.parse_args()
    try:
        data, started = ensure_service()
        print("Started Sentinel Python service." if started else "Reusing the running Sentinel Python service.")
        if data.get("hardware_monitor_version", 0) < 2:
            print("NOTE: The running service predates this hardware update. To load the updated bridge, stop it in its own terminal and run this launcher again. No process was stopped automatically.")
        print(f"Hardware monitor: {URL}/#hardware")
        print("Close Arduino Serial Monitor/Plotter, select a port and click Connect USB. No port has been opened by this launcher.")
        if not args.no_browser and not webbrowser.open(URL + "/#hardware"):
            print("The browser could not be opened automatically. Copy the address above into your browser.")
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"STARTUP ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
