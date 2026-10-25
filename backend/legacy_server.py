"""LAN-only JPEG receiver and live gallery. Python standard library only."""
import argparse
import hmac
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import threading
from urllib.parse import parse_qs, urlsplit

TOKEN = "intruder-local-upload-v1"  # Match the camera sketch.
MAX_BYTES = 5 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9-]{1,96}\Z")
DEFAULT_ML_RESULTS = Path(
    r"C:\Users\aaron\Downloads\AI-Intrusion-Detection-main\AI-Intrusion-Detection-main\ml\gallery_predictions"
)
PAGE = b'''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Intruder camera gallery</title><style>
body{font:16px system-ui;background:#101923;color:#ecf1f5;margin:32px}
h1{margin-bottom:8px}p{color:#b5c8d8}#grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:20px}
figure{margin:0;background:#203041;border-radius:12px;overflow:hidden}img{width:100%;display:block}
figcaption{padding:14px;overflow-wrap:anywhere;font-size:14px}.prediction{font-weight:700;margin-top:7px}
.person{color:#ff9f9f}.clear{color:#ffe08a}.pending{color:#b5c8d8}#status{margin:22px 0;color:#a7e3bd}
</style></head><body><h1>Intruder camera gallery</h1>
<p>Each sensor trigger requests five photos. Received JPEGs are saved on this PC and processed by the ML watcher.</p>
<p><a href="/ml/" style="color:#8ecbff">Open the full ML results page</a></p>
<div id="status">Connecting...</div><div id="grid"></div><script>
let previous='';async function refresh(){try{const [pr,mr]=await Promise.all([
fetch('/api/photos',{cache:'no-store'}),fetch('/api/ml-results',{cache:'no-store'})]);
if(!pr.ok||!mr.ok)throw Error();const photos=await pr.json(),ml=await mr.json();
const predictions=new Map(ml.results.map(x=>[x.source,x]));
document.querySelector('#status').textContent=photos.length+' photos saved | '+ml.results.length+
' ML predictions | '+(ml.configured?'ML results connected':'ML results folder unavailable')+' | Checking every 2 seconds';
const signature=JSON.stringify([photos,ml]);if(signature!==previous){previous=signature;
const grid=document.querySelector('#grid');grid.replaceChildren();
for(const p of photos.slice(0,100)){const fig=document.createElement('figure');const img=document.createElement('img');
const result=predictions.get(p.name);img.src=result&&result.annotated_image?'/ml-images/'+encodeURIComponent(result.annotated_image):'/photos/'+encodeURIComponent(p.name);img.alt=p.name;img.loading='lazy';
const cap=document.createElement('figcaption');cap.append(document.createTextNode(p.name+' | '+p.received));
const label=document.createElement('div');label.className='prediction '+(result?(result.person?'person':'clear'):'pending');
label.textContent=result?(result.classification+' | confidence '+Math.round((result.confidence||0)*100)+'%'):'Waiting for ML prediction';cap.append(label);
fig.append(img,cap);grid.append(fig);}}}catch(e){document.querySelector('#status').textContent='Server unavailable; retrying...';}}
refresh();setInterval(refresh,2000);</script></body></html>'''

def make_handler(folder, token=TOKEN, ml_folder=DEFAULT_ML_RESULTS):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    ml_folder = Path(ml_folder).resolve()
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, data, kind='text/plain; charset=utf-8'):
            if isinstance(data, str): data = data.encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/':
                return self.respond(200, PAGE, 'text/html; charset=utf-8')
            if path == '/api/photos':
                with lock:
                    files = sorted(folder.glob('*.jpg'), key=lambda p: p.stat().st_mtime_ns, reverse=True)
                    photos = [{'name': p.name, 'received': datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(timespec='seconds')} for p in files]
                return self.respond(200, json.dumps(photos), 'application/json')
            if path == '/api/ml-results':
                results = []
                if ml_folder.is_dir():
                    for record_path in ml_folder.glob('*.json'):
                        try:
                            record = json.loads(record_path.read_text(encoding='utf-8'))
                            results.append({
                                'source': Path(record.get('source', '')).name,
                                'processed_at': record.get('processed_at', ''),
                                'classification': record.get('classification', 'PROCESSING ERROR'),
                                'person': bool(record.get('person', False)),
                                'confidence': float(record.get('confidence', 0) or 0),
                                'annotated_image': Path(record.get('annotated_image', '')).name,
                            })
                        except (OSError, ValueError, TypeError):
                            continue
                results.sort(key=lambda item: item['processed_at'], reverse=True)
                return self.respond(200, json.dumps({'configured': ml_folder.is_dir(), 'results': results}), 'application/json')
            if path in ('/ml', '/ml/'):
                try: return self.respond(200, (ml_folder / 'index.html').read_bytes(), 'text/html; charset=utf-8')
                except FileNotFoundError: return self.respond(503, 'ML results are not ready. Start START_CAMERA_ML.bat first.')
            if path.startswith('/ml-images/'):
                name = path[len('/ml-images/'):]
                if name.endswith('.jpg') and Path(name).name == name:
                    try: return self.respond(200, (ml_folder / name).read_bytes(), 'image/jpeg')
                    except FileNotFoundError: pass
            if path.startswith('/ml/'):
                name = path[len('/ml/'):]
                if name.endswith('.jpg') and Path(name).name == name:
                    try: return self.respond(200, (ml_folder / name).read_bytes(), 'image/jpeg')
                    except FileNotFoundError: pass
            if path.startswith('/photos/'):
                name = path[len('/photos/'):]
                if name.endswith('.jpg') and ID.fullmatch(name[:-4]):
                    try: return self.respond(200, (folder / name).read_bytes(), 'image/jpeg')
                    except FileNotFoundError: pass
            self.respond(404, 'Not found')

        def do_POST(self):
            self.connection.settimeout(15)
            parts = urlsplit(self.path)
            if parts.path != '/upload': return self.respond(404, 'Not found')
            if not hmac.compare_digest(self.headers.get('X-Camera-Token', ''), token):
                return self.respond(401, 'Wrong camera upload token')
            identifier = parse_qs(parts.query).get('id', [''])[0]
            if not ID.fullmatch(identifier): return self.respond(400, 'Invalid photo ID')
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'image/jpeg':
                return self.respond(415, 'Send image/jpeg')
            try: length = int(self.headers.get('Content-Length', '0'))
            except ValueError: return self.respond(400, 'Invalid length')
            if not 4 <= length <= MAX_BYTES: return self.respond(413, 'Invalid image size')
            try: data = self.rfile.read(length)
            except (TimeoutError, OSError): return self.respond(408, 'Upload timed out')
            if len(data) != length or not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
                return self.respond(400, 'Incomplete JPEG or missing JPEG markers')
            target = folder / (identifier + '.jpg')
            with lock:
                if target.exists():
                    if target.read_bytes() != data: return self.respond(409, 'Photo ID already used')
                    status = 200
                else:
                    temporary = target.with_suffix('.part')
                    temporary.write_bytes(data)
                    temporary.replace(target)
                    status = 201
            print('SAVED:', target, flush=True)
            self.respond(status, json.dumps({'saved': target.name}), 'application/json')

    return Handler

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--storage', type=Path, default=Path(__file__).parent / 'captures')
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.storage))
    print(f'Gallery on this PC: http://localhost:{args.port}', flush=True)
    print(f'Photos: {args.storage.resolve()}\nPress Ctrl+C to stop.', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == '__main__': main()
