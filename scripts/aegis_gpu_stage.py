"""Single CUDA training stage. Run as a subprocess so failed CUDA contexts are released."""
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'ml/gpu_dataset_20261026'
GENERAL=DATA/'runs/aegis_person_local_gpu_v1'
CAMERA=DATA/'runs/aegis_camera_local_gpu_v1'

def prepare_camera_data():
 import yaml
 rows=[r for r in json.loads((DATA/'manifest.json').read_text()) if r['source']=='camera']
 location=DATA/'camera_stage';location.mkdir(exist_ok=True)
 for split in ('train','val','test'):
  subset=[r for r in rows if r['split']==split]
  if not subset or not any(r['boxes'] for r in subset) or not any(not r['boxes'] for r in subset):raise ValueError('Camera split needs person and empty examples: '+split)
  paths=[str((DATA/r['file']).resolve()) for r in subset]
  if not all(Path(p).is_file() for p in paths):raise ValueError('Missing camera image')
  (location/(split+'.txt')).write_text('\n'.join(paths)+'\n',encoding='utf-8')
 config={'path':str(DATA),'train':str(location/'train.txt'),'val':str(location/'val.txt'),'test':str(location/'test.txt'),'names':{0:'person'}}
 path=location/'data.yaml';path.write_text(yaml.safe_dump(config),encoding='utf-8')
 print('Reviewed camera splits:',{s:sum(r['split']==s for r in rows) for s in ('train','val','test')},flush=True)
 return path

def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['general','camera']);p.add_argument('--batch',type=int,default=1);a=p.parse_args()
 if a.batch<1:raise ValueError('Batch must be positive')
 import torch
 from ultralytics import YOLO
 if not torch.cuda.is_available():raise RuntimeError('CUDA required; refusing CPU fallback')
 print('CUDA:',torch.version.cuda,'GPU:',torch.cuda.get_device_name(0),flush=True)
 if a.stage=='general':
  last=GENERAL/'weights/last.pt'
  if not last.is_file():raise FileNotFoundError('Saved general checkpoint missing')
  YOLO(str(last)).train(resume=True,batch=a.batch,workers=0,device=0,plots=False)
 else:
  data=prepare_camera_data();last=CAMERA/'weights/last.pt'
  if last.is_file():
   YOLO(str(last)).train(resume=True,batch=a.batch,workers=0,device=0,plots=False)
  else:
   if CAMERA.exists():raise RuntimeError('Camera run exists without a resumable checkpoint; preserve it for inspection')
   source=GENERAL/'weights/best.pt'
   YOLO(str(source)).train(data=str(data),epochs=15,patience=5,imgsz=640,batch=a.batch,device=0,workers=0,seed=42,project=str(CAMERA.parent),name=CAMERA.name,exist_ok=False,optimizer='AdamW',lr0=.0001,lrf=.1,warmup_epochs=1,hsv_v=.2,hsv_s=.3,translate=.03,scale=.15,mosaic=.1,mixup=0,close_mosaic=3,plots=False)
if __name__=='__main__':main()
