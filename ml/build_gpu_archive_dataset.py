"""Build a portable, person-only GPU dataset from local archives and reviewed camera labels."""
from __future__ import annotations
import argparse,hashlib,io,json,math,random,re,shutil,zipfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image
import yaml
ROOT=Path(__file__).resolve().parents[1]
PRIORITY={'train':0,'val':1,'test':2}
EXT={'.jpg','.jpeg','.png','.bmp'}

def digest(data):return hashlib.sha256(data).hexdigest()
def clean_boxes(boxes):
 out=[]
 for x,y,w,h in boxes:
  if not all(math.isfinite(v) for v in (x,y,w,h)) or w<=0 or h<=0:raise ValueError('Nonfinite or empty box')
  if min(x-w/2,y-h/2)<-.00002 or max(x+w/2,y+h/2)>1.00002:raise ValueError('Normalized box outside image')
  out.append([round(float(v),6) for v in (x,y,w,h)])
 return sorted(out)
def fractional_box(x,y,w,h,W,H):
 if not all(math.isfinite(v) for v in (x,y,w,h)) or w<=0 or h<=0:raise ValueError('Invalid pixel box')
 a=max(0,min(W,x));b=max(0,min(H,y));c=max(0,min(W,x+w));d=max(0,min(H,y+h))
 if c<=a or d<=b:raise ValueError('Pixel box outside image')
 return [(a+c)/2/W,(b+d)/2/H,(c-a)/W,(d-b)/H]
def source_split(name):
 part=name.replace('\\','/').split('/')[0]
 return {'train':'train','valid':'val','val':'val','test':'test'}.get(part)
def compatible_yolo(text,person_ids):
 result=[]
 for line in text.splitlines():
  if not line.strip():continue
  values=line.split()
  if len(values)!=5:raise ValueError('Not a YOLO detection box')
  cls=float(values[0])
  if not cls.is_integer() or int(cls) not in person_ids:raise ValueError('Unknown source class; requires review')
  result.append([float(v) for v in values[1:]])
 return clean_boxes(result)
def build(out):
 out=out.resolve()
 if out.exists():raise ValueError('Output already exists; choose a new version.')
 out.mkdir(parents=True);objects=out/'.objects';objects.mkdir();licenses=out/'source_metadata';licenses.mkdir()
 rows=[];rejected=[];source_stats=defaultdict(Counter);annotations_by_hash={}
 def reject(source,name,reason):rejected.append({'source':source,'image':name,'reason':reason});source_stats[source]['excluded']+=1
 def add(source,name,data,boxes,split,group,origin):
  try:
   boxes=clean_boxes(boxes)
   with Image.open(io.BytesIO(data)) as im:
    W,H=im.size;fmt=im.format;im.verify()
   if W<=0 or H<=0:raise ValueError('Invalid image dimensions')
   ext={ 'JPEG':'.jpg','PNG':'.png','BMP':'.bmp' }.get(fmt)
   if not ext:raise ValueError('Unsupported decoded image format')
  except Exception as exc:reject(source,name,str(exc));return
  sha=digest(data);target=objects/(sha+ext)
  if not target.exists():target.write_bytes(data)
  rows.append({'source':source,'original_name':name,'origin':origin,'sha256':sha,'extension':ext,'width':W,'height':H,'boxes':boxes,'split':split,'group':group})
  source_stats[source]['candidates']+=1
 def load_yolo(z,source,origin):
  configs=[n for n in z.namelist() if n.endswith('data.yaml') and '__MACOSX' not in n]
  if not configs:raise ValueError('Missing source class map: '+source)
  config=yaml.safe_load(z.read(configs[0]));names=config.get('names',[])
  if isinstance(names,dict):names=[names[k] for k in sorted(names)]
  ids={i for i,n in enumerate(names) if str(n).strip().lower() in {'human','person','soldier'}}
  if not ids or len(ids)!=len(names):raise ValueError('Ambiguous classes in '+source)
  (licenses/(source+'-data.yaml')).write_bytes(z.read(configs[0]))
  for n in z.namelist():
   if Path(n).name.startswith('README') and not n.endswith('/'):
    (licenses/(source+'-'+Path(n).name)).write_bytes(z.read(n))
  members=set(z.namelist())
  for n in sorted(members):
   if '/images/' not in n or Path(n).suffix.lower() not in EXT or '__MACOSX' in n:continue
   split=source_split(n)
   if split is None:reject(source,n,'Unknown source split');continue
   label=n.replace('/images/','/labels/');label=str(Path(label).with_suffix('.txt')).replace('\\','/')
   if label not in members:reject(source,n,'Missing source label, not assumed empty');continue
   try:boxes=compatible_yolo(z.read(label).decode('utf-8-sig'),ids)
   except Exception as exc:reject(source,n,str(exc));continue
   base=Path(n).stem.split('.rf.')[0]
   add(source,n,z.read(n),boxes,split,source+':'+base,origin)
 # One image archive plus the matching COCO annotation archive.
 with zipfile.ZipFile(ROOT/'annotations_trainval2017.zip') as za:
  coco=json.loads(za.read('annotations/instances_val2017.json'))
 person_ids={c['id'] for c in coco['categories'] if c['name']=='person'};instances=defaultdict(list);crowd=set()
 for a in coco['annotations']:
  if a['category_id'] in person_ids:
   instances[a['image_id']].append(a)
   if a.get('iscrowd'):crowd.add(a['image_id'])
 with zipfile.ZipFile(ROOT/'val2017.zip') as z:
  members=set(z.namelist())
  for info in sorted(coco['images'],key=lambda i:i['id']):
   name='val2017/'+info['file_name']
   if name not in members:reject('coco',name,'Missing matching image');continue
   if info['id'] in crowd:reject('coco',name,'Person crowd/ignore annotation requires review; not relabeled as empty');continue
   try:boxes=[fractional_box(*a['bbox'],info['width'],info['height']) for a in instances[info['id']]]
   except Exception as exc:reject('coco',name,str(exc));continue
   bucket=int(hashlib.sha256(('coco:'+str(info['id'])).encode()).hexdigest()[:8],16)%100
   split='train' if bucket<70 else 'val' if bucket<85 else 'test'
   add('coco',name,z.read(name),boxes,split,'coco:'+str(info['id']),'val2017.zip + annotations_trainval2017.zip')
 with zipfile.ZipFile(ROOT/'Camouflage.v1i.yolov11.zip') as z:load_yolo(z,'camouflage','Camouflage.v1i.yolov11.zip')
 camo1=digest((ROOT/'Camouflage.v1i.yolov11.zip').read_bytes());camo2=digest((ROOT/'Camouflage.v1i.yolov11 (1).zip').read_bytes())
 if camo1!=camo2:
  with zipfile.ZipFile(ROOT/'Camouflage.v1i.yolov11 (1).zip') as z:load_yolo(z,'camouflage_copy','Camouflage.v1i.yolov11 (1).zip')
 with zipfile.ZipFile(ROOT/'dataset-20261020T080309Z-1-002.zip') as outer:
  for n,source in [('dataset/soldier.v1i.yolov11.zip','soldier_a'),('dataset/soldier.v1i.yolov11 (1).zip','soldier_b')]:
   with zipfile.ZipFile(io.BytesIO(outer.read(n))) as z:load_yolo(z,source,'dataset-20261020T080309Z-1-002.zip!'+n)
 # Use official ExDark ground truth. Folder names alone are never negative labels.
 stage=ROOT/'ml/archive_sources';splits={}
 for line in (stage/'ExDark_imageclasslist.txt').read_text(encoding='utf-8-sig').splitlines()[1:]:
  parts=line.split()
  if len(parts)>=5 and parts[-1] in {'1','2','3'}:splits[parts[0]]={'1':'train','2':'val','3':'test'}[parts[-1]]
 with zipfile.ZipFile(stage/'ExDark_Annno.zip') as az,zipfile.ZipFile(stage/'ExDark.zip') as iz:
  amap={Path(n).name:n for n in az.namelist() if n.endswith('.txt') and '__MACOSX' not in n}
  for n in sorted(set(iz.namelist())):
   if '__MACOSX' in n or Path(n).name.startswith('._') or Path(n).suffix.lower() not in EXT:continue
   name=Path(n).name;aname=name+'.txt'
   if aname not in amap or name not in splits:reject('exdark',n,'Missing official annotation or split');continue
   data=iz.read(n)
   try:
    with Image.open(io.BytesIO(data)) as im:W,H=im.size
    boxes=[]
    for line in az.read(amap[aname]).decode('utf-8-sig').splitlines():
     if not line.strip() or line.startswith('%'):continue
     values=line.split()
     if len(values)<5:raise ValueError('Malformed ExDark object record')
     if values[0].lower() in {'people','person','human'}:boxes.append(fractional_box(*map(float,values[1:5]),W,H))
   except Exception as exc:reject('exdark',n,str(exc));continue
   add('exdark',n,data,boxes,splits[name],'exdark:'+Path(name).stem,'dataset!ExDark.zip + official ExDark_Annno.zip')
 for p in stage.glob('ExDark_*.md'):shutil.copy2(p,licenses/p.name)
 for p in stage.glob('ExDark_*.txt'):shutil.copy2(p,licenses/p.name)
 # Snapshot only human-reviewed camera labels; keep full camera sessions together.
 lp=ROOT/'ml/camera_labels/annotations.json'
 if lp.exists():
  labels=json.loads(lp.read_text(encoding='utf-8-sig'));sessions=sorted({ '-'.join(Path(n).stem.split('-')[:2]) for n,v in labels.items() if v['status'] in {'person','empty'} })
  random.Random(42).shuffle(sessions);assignment={k:('train' if i<.7*len(sessions) else 'val' if i<.85*len(sessions) else 'test') for i,k in enumerate(sessions)}
  for name,e in labels.items():
   if e['status'] not in {'person','empty'}:continue
   p=ROOT/'captures'/name
   if Path(name).name!=name or not p.is_file():reject('camera',name,'Missing or invalid original name');continue
   data=p.read_bytes()
   if digest(data)!=e.get('sha256'):reject('camera',name,'Original changed since manual review');continue
   boxes=[[x+w/2,y+h/2,w,h] for x,y,w,h in e['boxes']];session='-'.join(p.stem.split('-')[:2])
   add('camera',name,data,boxes,assignment[session],'camera:'+session,'manual camera_labels/annotations.json snapshot')
 # Preserve existing evaluation holdouts by forcing exact matches to test.
 heldout=set()
 for folder in [ROOT/'ml/data_prepared/person',ROOT/'ml/data_prepared/no_person',ROOT/'ml/data/person',ROOT/'ml/data/no_person']:
  if folder.exists():
   for p in folder.iterdir():
    if p.is_file() and p.suffix.lower() in EXT:heldout.add(digest(p.read_bytes()))
 # Join source-image variants and duplicate records before resolving a split.
 parent={r['group']:r['group'] for r in rows}
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 byhash=defaultdict(list)
 for r in rows:
  if r['sha256'] in heldout:r['split']='test'
  old=byhash[r['sha256']]
  if old:parent[find(r['group'])]=find(old[0]['group'])
  old.append(r)
 group_split={}
 for r in rows:
  g=find(r['group']);previous=group_split.get(g,'train')
  group_split[g]=max([previous,r['split']],key=lambda v:PRIORITY[v])
 counts={k:Counter() for k in ['train','val','test']};manifest=[];duplicates=0;conflicts=0
 rank={'camera':5,'coco':4,'exdark':3}
 for sha,entries in sorted(byhash.items()):
  # A positive/negative contradiction needs human review, not a fabricated label.
  if len({bool(r['boxes']) for r in entries})>1:
   conflicts+=1
   for r in entries:reject(r['source'],r['original_name'],'Exact duplicate has contradictory person/empty annotations')
   continue
  r=max(entries,key=lambda v:rank.get(v['source'],2));split=group_split[find(r['group'])]
  duplicates+=len(entries)-1
  filename=r['source']+'_'+sha[:24]+r['extension']
  images=out/'images'/split;labs=out/'labels'/split;images.mkdir(parents=True,exist_ok=True);labs.mkdir(parents=True,exist_ok=True)
  src=objects/(sha+r['extension']);dest=images/filename
  if not src.resolve().is_relative_to(out) or not dest.resolve().is_relative_to(out):raise ValueError('Unsafe output path')
  shutil.copy2(src,dest)
  (labs/(Path(filename).stem+'.txt')).write_text('\n'.join('0 '+' '.join(f'{v:.6f}' for v in b) for b in r['boxes']),encoding='utf-8')
  counts[split]['images']+=1;counts[split]['person' if r['boxes'] else 'empty']+=1;source_stats[r['source']]['included_unique']+=1
  manifest.append({**r,'split':split,'file':f'images/{split}/{filename}','label':f'labels/{split}/{Path(filename).stem}.txt','duplicate_records':len(entries)-1})
 # Objects remain as an internal build cache outside the portable ZIP only.
 (out/'data.yaml').write_text('train: images/train\nval: images/val\ntest: images/test\nnames:\n  0: person\n',encoding='utf-8')
 weights=out/'weights';weights.mkdir();shutil.copy2(ROOT/'ml/yolo11m.pt',weights/'yolo11m.pt')
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 (out/'excluded_images.json').write_text(json.dumps(rejected,indent=2),encoding='utf-8')
 report={'created_at':datetime.now(timezone.utc).isoformat(),'counts':{k:dict(v) for k,v in counts.items()},'sources':{k:dict(v) for k,v in source_stats.items()},'unique_images':len(manifest),'duplicate_records_removed':duplicates,'contradictory_duplicate_groups_excluded':conflicts,'camouflage_zip_copy_identical':camo1==camo2,'hidden_dataset':{'status':'excluded pending verified class mapping','images':8754,'reason':'Three unreadable class names cannot be assumed to mean person.'},'exdark_annotations':'https://github.com/cs-chan/Exclusively-Dark-Image-Dataset/blob/master/Groundtruth/README.md','limitations':['Exact hashes and source filename groups cannot rule out every visually similar scene.','Camera session groups do not prove different scenes.','All original source test splits remain held out; no image is used for both training and testing.','Existing generic source provenance must accompany redistribution; consult source_metadata.','No training or live model change performed.']}
 (out/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,indent=2),flush=True)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.output)
