"""Read-only status and guarded Windows startup for the camera gallery."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import webbrowser
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "backend" / "config.local.json"
PYTHON = ROOT / "ml" / ".venv" / "Scripts" / "python.exe"
FRONTEND = ROOT / "frontend" / "dist" / "index.html"


def settings():
    try:
        raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Cannot read {CONFIG}: {exc}") from exc
    for key in ("capture_dir", "prediction_dir", "database", "model_path", "host", "port", "camera_token"):
        if not raw.get(key):
            raise RuntimeError(f"Missing {key} in {CONFIG}")
    for key in ("capture_dir", "prediction_dir", "database", "model_path"):
        path = Path(os.path.expandvars(str(raw[key])))
        raw[key] = (path if path.is_absolute() else CONFIG.parent / path).resolve()
    if raw["port"] != 5000:
        raise RuntimeError("This launcher expects port 5000; check backend/config.local.json")
    if not isinstance(raw["camera_token"], str) or not raw["camera_token"].strip():
        raise RuntimeError("camera_token must be nonempty text")
    return raw


def preflight(config):
    errors = []
    for label, path in (("Capture folder", config["capture_dir"]), ("Prediction folder", config["prediction_dir"])):
        if not path.is_dir():
            errors.append(f"{label} missing: {path}")
    if not config["database"].parent.is_dir():
        errors.append(f"Database folder missing: {config['database'].parent}")
    if not config["model_path"].is_file():
        errors.append(f"YOLO model missing: {config['model_path']}")
    if not PYTHON.is_file():
        errors.append(f"Python environment missing: {PYTHON}")
    if not FRONTEND.is_file():
        errors.append("React build missing: run npm install and npm run build in frontend")
    if errors:
        raise RuntimeError("Preflight failed:\n  " + "\n  ".join(errors))


def gallery_http():
    try:
        with urlopen("http://127.0.0.1:5000/", timeout=3) as response:
            body = response.read(4096).decode("utf-8", "replace")
            return response.status, any(title in body for title in (
                "<title>Vigil — Intrusion Command Center</title>",
                "<title>Sentinel AI — Intrusion Monitoring</title>"))
    except HTTPError as exc:
        return exc.code, False
    except (URLError, OSError, TimeoutError):
        return None, False


def port_occupied():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        stream.settimeout(1)
        return stream.connect_ex(("127.0.0.1", 5000)) == 0


def readonly_db(path):
    if not path.is_file():
        return None
    # SQLite URI mode=ro prevents this report from creating or updating a DB.
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)


def worker_heartbeat(path):
    try:
        db = readonly_db(path)
        if db is None:
            return None
        with db:
            row = db.execute("SELECT value FROM service_state WHERE name='worker_heartbeat'").fetchone()
        db.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def heartbeat_fresh(value):
    if not value:
        return False
    try:
        return 0 <= (datetime.now(timezone.utc) - datetime.fromisoformat(value)).total_seconds() < 30
    except ValueError:
        return False


def worker_lock_held(path):
    """Use the worker's OS lock, not a possibly stale heartbeat, for startup."""
    if not path.is_file():
        return False
    with open(path, "r+b") as stream:
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            return False
        except OSError:
            return True


def wifi_ipv4():
    if os.name != "nt":
        return []
    command = ["powershell", "-NoProfile", "-Command",
               "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
               "Where-Object { $_.InterfaceAlias -match 'Wi-Fi|Wireless|WLAN' -and "
               "$_.IPAddress -notlike '169.254.*' } | Select-Object InterfaceAlias,IPAddress | ConvertTo-Json -Compress"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
        data = json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else []
        if data:
            return data if isinstance(data, list) else [data]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    # Get-NetIPAddress may be blocked by a local policy; ipconfig is read-only.
    try:
        result = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=8, check=False)
        section = None
        addresses = []
        for line in result.stdout.splitlines():
            if line and not line[0].isspace() and line.rstrip().endswith(":"):
                section = line.rstrip(" :")
            match = re.search(r"IPv4 Address[^:]*:\s*(\d{1,3}(?:\.\d{1,3}){3})", line)
            if section and re.search(r"Wi-Fi|Wireless|WLAN", section, re.I) and match:
                addresses.append({"InterfaceAlias": section, "IPAddress": match.group(1)})
        return addresses
    except (OSError, subprocess.TimeoutExpired):
        return []


@contextmanager
def start_lock():
    path = ROOT / "storage" / "start.lock"
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
            raise RuntimeError("Another START_ALL is already checking or starting services") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def check(config):
    status, ours = gallery_http()
    print(f"Gallery HTTP: {status if status is not None else 'unreachable'}" + (" (Sentinel backend)" if ours else ""))
    addresses = wifi_ipv4()
    print("Laptop Wi-Fi IPv4: " + (", ".join(f"{item['InterfaceAlias']} {item['IPAddress']}" for item in addresses) if addresses else "unavailable; check Windows Wi-Fi"))
    heartbeat = worker_heartbeat(config["database"])
    print(f"ML heartbeat: {'online' if heartbeat_fresh(heartbeat) else 'offline/stale'}" + (f" (last {heartbeat})" if heartbeat else ""))
    try:
        db = readonly_db(config["database"])
        if db is None:
            print("Database: missing; no photos indexed yet")
            return 1
        with db:
            photo = db.execute("SELECT id,received_at,ml_state FROM photos ORDER BY received_at DESC,id DESC LIMIT 1").fetchone()
            prediction = db.execute("SELECT id,received_at,ml_state FROM photos WHERE ml_state IN ('person_detected','no_person_detected') ORDER BY received_at DESC,id DESC LIMIT 1").fetchone()
            total = db.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
            incomplete = db.execute("SELECT COUNT(*) FROM (SELECT burst_id FROM photos WHERE burst_id IS NOT NULL GROUP BY burst_id HAVING COUNT(*) < 5)").fetchone()[0]
            errors = db.execute("SELECT COUNT(*) FROM photos WHERE ml_state='error'").fetchone()[0]
            queued = db.execute("SELECT COUNT(*) FROM ml_jobs WHERE state IN ('queued','processing')").fetchone()[0]
        db.close()
        print("Latest photo: " + (f"{photo[0]} | {photo[1]} | {photo[2]}" if photo else "none"))
        print("Latest prediction: " + (f"{prediction[0]} | {prediction[1]} | {prediction[2]}" if prediction else "none"))
        print(f"Counts: {total} photos | {incomplete} incomplete bursts | {errors} ML errors | {queued} queued/processing")
    except (sqlite3.Error, OSError) as exc:
        print(f"Database read error: {exc}")
        return 1
    return 0 if status == 200 and ours and heartbeat_fresh(heartbeat) else 1


def start(config):
    with start_lock():
        _start_locked(config)


def _start_locked(config):
    preflight(config)
    status, ours = gallery_http()
    if status is not None and not ours:
        raise RuntimeError(f"Port 5000 answers HTTP {status} from another service; close it before starting")
    if status is None and port_occupied():
        raise RuntimeError("Port 5000 is occupied but the gallery does not answer; inspect the existing process")
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    if ours:
        print("Backend already running on port 5000; using it.", flush=True)
    else:
        backend = subprocess.Popen([str(PYTHON), "-u", str(ROOT / "backend" / "server.py")], cwd=ROOT, creationflags=flags)
        for _ in range(40):
            if backend.poll() is not None:
                raise RuntimeError(f"Backend exited with code {backend.returncode}; read its console window")
            if gallery_http() == (200, True):
                break
            time.sleep(.25)
        else:
            raise RuntimeError("Backend did not answer on port 5000 within 10 seconds; read its console window")
        print("Backend ready on port 5000.", flush=True)
    lock = config["database"].with_suffix(".worker.lock")
    if worker_lock_held(lock):
        if heartbeat_fresh(worker_heartbeat(config["database"])):
            print("ML worker already running; using it.", flush=True)
            return
        raise RuntimeError("ML worker lock is held but heartbeat is stale; inspect its console before retrying")
    worker = subprocess.Popen([str(PYTHON), "-u", str(ROOT / "backend" / "worker.py")], cwd=ROOT, creationflags=flags)
    print("Starting ML worker and loading the local model...", flush=True)
    for _ in range(360):
        if worker.poll() is not None:
            raise RuntimeError(f"ML worker exited with code {worker.returncode}; read its console window")
        if worker_lock_held(lock) and heartbeat_fresh(worker_heartbeat(config["database"])):
            print("ML worker ready. Open http://localhost:5000/", flush=True)
            return
        time.sleep(.25)
    raise RuntimeError("ML worker did not become ready within 90 seconds; read its console window")


def backup(config):
    for path in (config["capture_dir"], config["prediction_dir"], config["database"]):
        if not path.exists():
            raise RuntimeError(f"Backup source missing: {path}")
    destination = ROOT / "backups" / ("phase5-" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    destination.mkdir(parents=True, exist_ok=False)
    counts = {}
    for label, source, suffixes in (("captures", config["capture_dir"], {".jpg"}),
                                    ("predictions", config["prediction_dir"], {".jpg", ".json"})):
        target = destination / label
        target.mkdir()
        files = [item for item in source.iterdir() if item.is_file() and item.suffix.lower() in suffixes]
        for item in files:
            shutil.copy2(item, target / item.name)
        counts[label] = len(files)
    source = sqlite3.connect(config["database"].as_uri() + "?mode=ro", uri=True, timeout=10)
    target = sqlite3.connect(destination / "app.sqlite3")
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()
    (destination / "manifest.json").write_text(json.dumps({"completed_at": datetime.now(timezone.utc).isoformat(),
        "source_capture_dir": str(config["capture_dir"]), "source_prediction_dir": str(config["prediction_dir"]),
        "counts": counts}, indent=2), encoding="utf-8")
    print(f"Backup complete: {destination}")
    print(f"Captures: {counts['captures']} | prediction JSON/JPEG: {counts['predictions']} | SQLite: 1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "check", "backup"))
    args = parser.parse_args()
    try:
        config = settings()
        if args.action == "start":
            start(config)
            try:
                with urlopen("http://127.0.0.1:5000/api/hardware", timeout=3) as response:
                    data = json.load(response)
                if data.get("hardware_monitor_version") != 1:
                    raise ValueError("Unexpected hardware endpoint")
            except (OSError, ValueError, URLError) as exc:
                raise RuntimeError("The running backend predates hardware monitoring. Stop that backend in its own console and rerun START_ALL; no process was terminated automatically.") from exc
            webbrowser.open("http://localhost:5000/#hardware")
            return 0
        if args.action == "backup":
            backup(config)
            return 0
        return check(config)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
