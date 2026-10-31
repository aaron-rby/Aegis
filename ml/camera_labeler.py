"""Local manual annotation tool for original ESP32-CAM images; no automatic truth labels."""
from __future__ import annotations
import argparse, hashlib, json, math, random, shutil, threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / 'captures'
LABELS = ROOT / 'ml' / 'camera_labels' / 'annotations.json'
HTML = Path(__file__).with_name('camera_labeler.html')
LOCK = threading.RLock()

def validate_entry(value):
    if not isinstance(value, dict) or value.get('status') not in {'person','empty','uncertain'}:
        raise ValueError('Choose person, empty or uncertain.')
    boxes = value.get('boxes', [])
    if not isinstance(boxes, list) or len(boxes)>100: raise ValueError('Invalid box list.')
    clean=[]
    for b in boxes:
        if not isinstance(b,list) or len(b)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in b):
            raise ValueError('Box must contain four finite normalized coordinates.')
        x,y,w,h=b
        if not(0<=x<=1 and 0<=y<=1 and w>0 and h>0 and x+w<=1.000001 and y+h<=1.000001):
            raise ValueError('Box is outside image boundaries.')
        clean.append([round(v,7) for v in b])
    if value['status']=='person' and not clean: raise ValueError('Draw at least one person box.')
    if value['status']!='person' and clean: raise ValueError('Clear boxes before marking empty or uncertain.')
    return {'status':value['status'],'boxes':clean}

def read_labels():
    return json.loads(LABELS.read_text(encoding='utf-8')) if LABELS.exists() else {}

def image_path(name):
    if Path(name).name!=name or not name.lower().endswith('.jpg'): raise ValueError('Invalid filename.')
    p=CAPTURES/name
    if not p.is_file(): raise ValueError('Original capture is missing.')
    return p

def save_label(name, value):
    p=image_path(name);entry=validate_entry(value)
    entry.update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),reviewed_at=datetime.now(timezone.utc).isoformat())
    with LOCK:
        labels=read_labels();labels[name]=entry;LABELS.parent.mkdir(parents=True,exist_ok=True)
        temporary=LABELS.with_suffix('.tmp');temporary.write_text(json.dumps(labels,indent=2),encoding='utf-8');temporary.replace(LABELS)
    return entry

def session_key(name):
    parts=Path(name).stem.split('-')
    return '-'.join(parts[:2]) if len(parts)==4 else 'legacy:'+Path(name).stem

def split_groups(rows):
    # Union identical images and entire camera sessions before allocating splits.
    parent={r['session']:r['session'] for r in rows}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    hashes={}
    for r in rows:
        if r['sha256'] in hashes: parent[find(r['session'])]=find(hashes[r['sha256']])
        hashes[r['sha256']]=r['session']
    groups={}
    for r in rows: groups.setdefault(find(r['session']),[]).append(r)
    if len(groups)<3: raise ValueError('Review images from at least three separate camera sessions before export.')
    counts={'train':0,'val':0,'test':0};targets={'train':.7*len(rows),'val':.15*len(rows),'test':.15*len(rows)}
    items=list(groups.values());random.Random(42).shuffle(items);items.sort(key=len,reverse=True)
    result={k:[] for k in counts}
    for i,g in enumerate(items):
        remaining=len(items)-i;empty=[k for k in result if not result[k]]
        key=empty[0] if remaining==len(empty) else max(counts,key=lambda k:targets[k]-counts[k])
        result[key].extend(g);counts[key]+=len(g)
    return result

def export_dataset(output):
    if output.exists(): raise ValueError('Output already exists. Choose a new version; existing datasets are never overwritten.')
    rows=[]
    for name,e in read_labels().items():
        e= dict(e);clean=validate_entry(e)
        if clean['status']=='uncertain':continue
        p=image_path(name);digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest!=e.get('sha256'): raise ValueError('Original changed since annotation: '+name)
        rows.append(dict(name=name,session=session_key(name),sha256=digest,**clean))
    splits=split_groups(rows)
    for key,group in splits.items():
        if not group or not any(r['status']=='person' for r in group) or not any(r['status']=='empty' for r in group):
            raise ValueError('Each split needs reviewed person and empty examples. Review more varied sessions first; no output created.')
    output.mkdir(parents=True)
    try:
        for split,group in splits.items():
            images=output/'images'/split;labels=output/'labels'/split;images.mkdir(parents=True);labels.mkdir(parents=True)
            for r in group:
                shutil.copy2(image_path(r['name']),images/r['name'])
                lines=[]
                for x,y,w,h in r['boxes']:lines.append(f'0 {x+w/2:.7f} {y+h/2:.7f} {w:.7f} {h:.7f}')
                (labels/(Path(r['name']).stem+'.txt')).write_text('\n'.join(lines),encoding='utf-8')
        (output/'data.yaml').write_text('path: '+output.resolve().as_posix()+'\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: person\n',encoding='utf-8')
        (output/'split_manifest.json').write_text(json.dumps(splits,indent=2),encoding='utf-8')
    except Exception:
        raise # Preserve partial output for inspection rather than deleting data.
    return {k:len(v) for k,v in splits.items()}

class Handler(BaseHTTPRequestHandler):
    def reply(self,code,data,kind='application/json'):
        if kind=='application/json':data=json.dumps(data).encode()
        elif isinstance(data,str):data=data.encode()
        self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
    def allowed_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def do_GET(self):
        if not self.allowed_host():return self.reply(403,{'detail':'Local access only.'})
        path=urlsplit(self.path).path
        if path=='/':return self.reply(200,HTML.read_bytes(),'text/html; charset=utf-8')
        if path=='/api/images':
            labels=read_labels();rows=[]
            for p in sorted(CAPTURES.glob('*.jpg'),key=lambda p:p.stat().st_mtime,reverse=True):
                rows.append({'name':p.name,'session':session_key(p.name),'label':labels.get(p.name)})
            return self.reply(200,rows)
        if path.startswith('/image/'):
            try:return self.reply(200,image_path(unquote(path[7:])).read_bytes(),'image/jpeg')
            except ValueError:return self.reply(404,{'detail':'Not found'})
        return self.reply(404,{'detail':'Not found'})
    def do_POST(self):
        expected={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
        if not self.allowed_host() or self.headers.get('Origin') not in expected:return self.reply(403,{'detail':'Same-origin local requests only.'})
        if self.path!='/api/label':return self.reply(404,{'detail':'Not found'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=50000:raise ValueError('Invalid request length.')
            value=json.loads(self.rfile.read(length));entry=save_label(value['name'],value)
            return self.reply(200,entry)
        except (ValueError,KeyError,TypeError) as exc:return self.reply(400,{'detail':str(exc)})
        except OSError:return self.reply(500,{'detail':'Could not save labels. Check disk space and permissions.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=5010);p.add_argument('--export',type=Path);a=p.parse_args()
    if a.export:
        try:print(json.dumps(export_dataset(a.export.resolve()),indent=2))
        except ValueError as exc:p.exit(1,str(exc)+'\n')
    else:
        print(f'Camera labeling: http://127.0.0.1:{a.port} | originals unchanged',flush=True)
        ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__': main()
