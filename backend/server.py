"""Camera-compatible LAN receiver and indexed gallery backend."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hmac
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import mimetypes
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import parse_qs, urlsplit

try:
    from PIL import Image, UnidentifiedImageError
except ImportError as exc:
    raise SystemExit("BACKEND STARTUP ERROR: Pillow is required. Run: python -m pip install -r backend/requirements.txt") from exc

from storage import Store
from hardware import HardwareMonitor

MAX_BYTES = 5 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9-]{1,96}\Z")
PAGE = b'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Intruder camera gallery</title><style>body{font:16px system-ui;background:#101923;color:#ecf1f5;margin:32px}h1{margin-bottom:8px}p{color:#b5c8d8}#grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:20px}figure{margin:0;background:#203041;border-radius:12px;overflow:hidden}img{width:100%;display:block}figcaption{padding:14px;overflow-wrap:anywhere;font-size:14px}.prediction{font-weight:700;margin-top:7px}.person{color:#ff9f9f}.clear{color:#ffe08a}.pending{color:#b5c8d8}#status{margin:22px 0;color:#a7e3bd}</style></head><body><h1>Intruder camera gallery</h1><p>Camera JPEGs are saved on this PC and processed by the ML worker. No person detected is a model result, not proof the scene is empty.</p><p><a href="/ml/" style="color:#8ecbff">Open the full ML results page</a></p><div id="status">Connecting...</div><div id="grid"></div><script>let previous='';async function refresh(){try{const [pr,sr]=await Promise.all([fetch('/api/photos?per_page=100',{cache:'no-store'}),fetch('/api/status',{cache:'no-store'})]);if(!pr.ok||!sr.ok)throw Error();const photos=await pr.json(),status=await sr.json();document.querySelector('#status').textContent=photos.total+' photos saved | '+(status.worker.running?'ML worker online':'ML heartbeat unavailable')+' | Checking every 2 seconds';const signature=JSON.stringify(photos);if(signature!==previous){previous=signature;const grid=document.querySelector('#grid');grid.replaceChildren();for(const p of photos.items){const fig=document.createElement('figure'),img=document.createElement('img');img.src=p.annotated_url||p.image_url;img.alt=p.name;img.loading='lazy';const cap=document.createElement('figcaption');cap.append(document.createTextNode(p.name+' | '+p.received_at));const label=document.createElement('div');label.className='prediction '+(p.prediction?(p.prediction.person?'person':'clear'):'pending');label.textContent=p.prediction?(p.prediction.classification+' | confidence '+Math.round((p.prediction.confidence||0)*100)+'%'):'Waiting for ML prediction';cap.append(label);fig.append(img,cap);grid.append(fig)}}}catch(e){document.querySelector('#status').textContent='Server unavailable; retrying...'}}refresh();setInterval(refresh,2000);</script></body></html>'''


def results_page(store: Store):
    with store.connect() as db:
        rows = db.execute("SELECT * FROM photos WHERE prediction IS NOT NULL ORDER BY received_at DESC,id DESC LIMIT 200").fetchall()
    cards = []
    for row in rows:
        photo = store.as_photo(row)
        prediction = photo["prediction"]
        image = html.escape(photo["annotated_url"] or photo["image_url"], quote=True)
        label = html.escape(prediction.get("classification", "PROCESSING ERROR"))
        name = html.escape(photo["name"])
        cards.append(f'<article><img src="{image}" alt="{name}"><p>{label}</p><small>{name}</small></article>')
    return ('<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Camera ML results</title>'
            '<style>body{font:16px system-ui;background:#101923;color:#ecf1f5;padding:24px}main{display:grid;'
            'grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}article{background:#203041;'
            'padding:12px;border-radius:10px;overflow-wrap:anywhere}img{width:100%}a{color:#8ecbff}</style></head>'
            '<body><h1>Camera ML results</h1><p>No person detected is a model result, not proof of absence. '
            'Authorization is not evaluated.</p><p><a href="/">Back to gallery</a></p><main>'
            + ''.join(cards) + '</main></body></html>')


def load_config(path: Path):
    path = Path(path).resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read backend configuration {path}: {exc}") from exc
    required = ("capture_dir", "prediction_dir", "database", "model_path", "host", "port", "camera_token")
    for key in required:
        if not raw.get(key):
            raise ValueError(f"Missing {key} in {path}")
    for key in ("capture_dir", "prediction_dir", "database", "model_path"):
        value = Path(os.path.expandvars(raw[key]))
        raw[key] = (value if value.is_absolute() else path.parent / value).resolve()
    if not raw["capture_dir"].is_dir():
        raise ValueError(f"Capture directory does not exist: {raw['capture_dir']}")
    if not raw["prediction_dir"].is_dir():
        raise ValueError(f"Prediction directory does not exist: {raw['prediction_dir']}")
    if not raw["model_path"].is_file():
        raise ValueError(f"Model file does not exist: {raw['model_path']}")
    try: raw["port"] = int(raw["port"])
    except (ValueError, TypeError): raise ValueError("Port must be an integer")
    if not 1 <= raw["port"] <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    if not isinstance(raw["camera_token"], str):
        raise ValueError("camera_token must be text")
    if "alarm_token" in raw and (not isinstance(raw["alarm_token"], str) or len(raw["alarm_token"]) < 16):
        raise ValueError("alarm_token must be at least 16 characters")
    return raw


def make_handler(store: Store, token: str, model: Path, alarm_token: str | None = None, hardware_monitor=None):
    lock = threading.Lock()
    frontend = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    monitor = hardware_monitor or HardwareMonitor()

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, data, kind="text/plain; charset=utf-8"):
            if isinstance(data, (dict, list)):
                data, kind = json.dumps(data).encode(), "application/json; charset=utf-8"
            elif isinstance(data, str):
                data = data.encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parts = urlsplit(self.path)
            path = parts.path
            if path == "/api/hardware":
                return self.respond(200, monitor.snapshot())
            if path == "/api/serial/ports":
                try:
                    return self.respond(200, {"ports": monitor.bridge.ports(), "status": monitor.bridge.status()})
                except OSError as exc:
                    return self.respond(503, {"detail": f"Cannot list serial ports: {exc}"})
            if path == "/":
                index = frontend / "index.html"
                if index.is_file():
                    return self.respond(200, index.read_bytes(), "text/html; charset=utf-8")
                return self.respond(200, PAGE, "text/html; charset=utf-8")
            if path.startswith("/assets/") or path == "/favicon.svg":
                asset = (frontend / path.lstrip("/")).resolve()
                if asset.is_file() and asset.is_relative_to(frontend.resolve()):
                    kind = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                    return self.respond(200, asset.read_bytes(), kind)
                return self.respond(404, "Not found")
            if path in ("/api/photos", "/api/bursts"):
                query = parse_qs(parts.query)
                try:
                    page = int(query.get("page", ["1"])[0])
                    per_page = int(query.get("per_page", ["30"])[0])
                except ValueError:
                    return self.respond(400, "Invalid pagination")
                if page < 1 or not 1 <= per_page <= 100:
                    return self.respond(400, "Pagination out of range")
                if path == "/api/photos":
                    person_filter = query.get("person", ["all"])[0]
                    burst_id = query.get("burst_id", [None])[0]
                    if person_filter not in ("all", "person", "no_person", "pending", "error"):
                        return self.respond(400, "Invalid person filter")
                    if burst_id is not None and not ID.fullmatch(burst_id):
                        return self.respond(400, "Invalid burst ID")
                    store.sync_predictions()
                    return self.respond(200, store.photos_page(page, per_page, person_filter, burst_id))
                store.sync_predictions()
                return self.respond(200, store.bursts_page(page, per_page))
            if path.startswith("/api/photos/"):
                identifier = path[len("/api/photos/"):]
                if not ID.fullmatch(identifier):
                    return self.respond(404, "Not found")
                store.sync_predictions()
                item = store.photo(identifier)
                return self.respond(200, item) if item else self.respond(404, "Not found")
            if path == "/api/status":
                store.sync_predictions()
                return self.respond(200, store.status(model))
            if path == "/api/alarm/latest":
                if not alarm_token:
                    return self.respond(503, "ML alarm is not configured")
                if not hmac.compare_digest(self.headers.get("X-Alarm-Token", ""), alarm_token):
                    return self.respond(401, "Wrong alarm token")
                event_id = store.latest_alarm_event()
                return self.respond(200, event_id or "")
            if path == "/api/ml-results":
                store.sync_predictions()
                with store.connect() as db:
                    rows = db.execute("SELECT * FROM photos WHERE prediction IS NOT NULL ORDER BY received_at DESC,id DESC").fetchall()
                results = []
                for row in rows:
                    prediction = json.loads(row["prediction"])
                    results.append({"source": row["id"] + ".jpg", **prediction})
                return self.respond(200, {"configured": store.predictions.is_dir(), "results": results})
            if path in ("/ml", "/ml/"):
                store.sync_predictions()
                return self.respond(200, results_page(store), "text/html; charset=utf-8")
            for prefix, folder in (("/photos/", store.captures), ("/ml-images/", store.predictions), ("/ml/", store.predictions)):
                if path.startswith(prefix):
                    name = path[len(prefix):]
                    if name.endswith(".jpg") and Path(name).name == name:
                        if prefix == "/photos/" and not ID.fullmatch(name[:-4]):
                            break
                        target = folder / name
                        if target.is_file() and target.resolve().parent == folder:
                            return self.respond(200, target.read_bytes(), "image/jpeg")
                    break
            return self.respond(404, "Not found")

        def do_POST(self):
            self.connection.settimeout(15)
            parts = urlsplit(self.path)
            if parts.path in ("/api/serial/connect", "/api/serial/disconnect"):
                origin = self.headers.get("Origin")
                allowed = {f"http://{host}:{port}" for host in ("localhost", "127.0.0.1", "[::1]") for port in (5000, 5173)}
                if self.client_address[0] not in ("127.0.0.1", "::1") or (origin and origin not in allowed):
                    return self.respond(403, {"detail": "Control USB from this laptop's local dashboard only."})
                try:
                    if parts.path.endswith("disconnect"):
                        return self.respond(200, monitor.bridge.disconnect())
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 1024 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                        return self.respond(400, {"detail": "Send a small JSON port and baudrate request."})
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict) or not isinstance(payload.get("port"), str) or not 0 < len(payload["port"]) <= 100 or type(payload.get("baudrate", 115200)) is not int:
                        return self.respond(400, {"detail": "A serial port and numeric baudrate are required."})
                    return self.respond(200, monitor.bridge.connect(payload["port"], payload.get("baudrate", 115200)))
                except (ValueError, OSError) as exc:
                    return self.respond(409, {"detail": str(exc)})
            if parts.path != "/upload": return self.respond(404, "Not found")
            if not hmac.compare_digest(self.headers.get("X-Camera-Token", ""), token):
                return self.respond(401, "Wrong camera upload token")
            identifier = parse_qs(parts.query).get("id", [""])[0]
            if not ID.fullmatch(identifier): return self.respond(400, "Invalid photo ID")
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "image/jpeg":
                return self.respond(415, "Send image/jpeg")
            try: length = int(self.headers.get("Content-Length", "0"))
            except ValueError: return self.respond(400, "Invalid length")
            if not 4 <= length <= MAX_BYTES: return self.respond(413, "Invalid image size")
            try: data = self.rfile.read(length)
            except (TimeoutError, OSError): return self.respond(408, "Upload timed out")
            if len(data) != length or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
                return self.respond(400, "Incomplete JPEG or missing JPEG markers")
            try:
                with Image.open(BytesIO(data)) as image:
                    if image.format != "JPEG": return self.respond(400, "Invalid JPEG")
                    image.verify()
            except (OSError, ValueError, UnidentifiedImageError):
                return self.respond(400, "Invalid JPEG")
            target = store.captures / (identifier + ".jpg")
            with lock:
                if target.exists():
                    if target.read_bytes() != data: return self.respond(409, "Photo ID already used")
                    status = 200
                else:
                    temp_name = None
                    try:
                        with tempfile.NamedTemporaryFile(mode="wb", suffix=".part", dir=store.captures, delete=False) as stream:
                            temp_name = stream.name
                            stream.write(data)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temp_name, target)
                        status = 201
                    finally:
                        if temp_name and os.path.exists(temp_name): os.unlink(temp_name)
                try: store.add_photo(target, datetime.now(timezone.utc).isoformat(), record_upload=(status == 201))
                except Exception as exc:
                    print(f"INDEX ERROR for {target.name}: {exc}", flush=True)
                    return self.respond(500, "Photo saved but index update failed; retry upload")
            print(f"SAVED: {target.name} ({status})", flush=True)
            return self.respond(status, {"saved": target.name})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.local.json"))
    parser.add_argument("--port", type=int, help="Temporary port override for migration testing")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.port is not None: config["port"] = args.port
        store = Store(config["database"], config["capture_dir"], config["prediction_dir"])
        imported = store.import_captures()
        store.sync_predictions()
        server = ThreadingHTTPServer((config["host"], config["port"]),
                                     make_handler(store, config["camera_token"], config["model_path"],
                                                  config.get("alarm_token")))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"BACKEND STARTUP ERROR: {exc}\n")
    print(f"Backend ready on http://localhost:{config['port']} | indexed {imported} captures", flush=True)
    print(f"Captures: {store.captures}\nPredictions: {store.predictions}\nModel: {config['model_path']}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__": main()
