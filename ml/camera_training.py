"""Validate, train and compare camera-person models without replacing the live model."""
from __future__ import annotations
import argparse,hashlib,json,math,os
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

def validate_dataset(path):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('Dataset is not exported yet. Review camera labels and export first.')
    config=yaml.safe_load(path.read_text(encoding='utf-8'))
    if config.get('names') not in ({0:'person'},['person']):raise ValueError('Expected exactly class 0: person.')
    base=Path(config.get('path',path.parent));base=base if base.is_absolute() else path.parent/base
    seen_hashes={};seen_sessions={};counts={}
    for split in ('train','val','test'):
        images=base/config[split];labels=images.parent.parent/'labels'/images.name
        if not labels.is_dir(): labels=images.parent/'labels' # historical split/images layout
        files=sorted(p for p in images.glob('*') if p.suffix.lower() in {'.jpg','.jpeg','.png'})
        if not files:raise ValueError('Empty image split: '+split)
        positive=negative=0
        for image in files:
            lab=labels/(image.stem+'.txt')
            if not lab.is_file():raise ValueError('Missing label: '+str(lab))
            lines=lab.read_text(encoding='utf-8').splitlines()
            for line in lines:
                vals=line.split()
                if len(vals)!=5:raise ValueError('Expected 5 YOLO values: '+str(lab))
                cls,x,y,w,h=map(float,vals)
                if not all(math.isfinite(v) for v in (cls,x,y,w,h)) or cls!=0 or not(w>0 and h>0 and 0<=x-w/2<=x+w/2<=1.00001 and 0<=y-h/2<=y+h/2<=1.00001):raise ValueError('Invalid person box: '+str(lab))
            positive+=bool(lines);negative+=not bool(lines)
            digest=hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in seen_hashes and seen_hashes[digest]!=split:raise ValueError('Identical image leaks across splits.')
            seen_hashes[digest]=split
            parts=image.stem.split('-')
            if len(parts)==4:
                session='-'.join(parts[:2])
                if session in seen_sessions and seen_sessions[session]!=split:raise ValueError('Camera session leaks across splits.')
                seen_sessions[session]=split
        if not positive or not negative:raise ValueError('Each split needs person and empty examples: '+split)
        counts[split]={'images':len(files),'person':positive,'empty':negative}
    return base,config,counts

def run():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['check','train','evaluate']);p.add_argument('--data',type=Path,default=ROOT/'ml/camera_dataset_v1/data.yaml');p.add_argument('--device',default='auto');p.add_argument('--epochs',type=int,default=50);p.add_argument('--batch',type=int,default=2);p.add_argument('--name',default='person_v1');p.add_argument('--candidate',type=Path);p.add_argument('--split',choices=['val','test'],default='val');p.add_argument('--threshold',type=float,default=.35);a=p.parse_args()
    try:
        base,config,counts=validate_dataset(a.data)
        print(json.dumps(counts,indent=2))
        if a.action=='check':return
        import torch
        device= ('0' if torch.cuda.is_available() else 'cpu') if a.device=='auto' else a.device
        if a.action=='train':
            if device=='cpu' and a.device=='auto':raise ValueError('No CUDA GPU available. Use --device cpu explicitly for slow local training, or transfer the dataset to a GPU machine.')
            if a.epochs<1 or a.batch<1 or Path(a.name).name!=a.name:raise ValueError('Invalid training arguments.')
            target=ROOT/'ml/runs_camera'/a.name
            if target.exists():raise ValueError('Training run exists. Choose a new --name.')
            from ultralytics import YOLO
            YOLO(str(ROOT/'ml/yolo11m.pt')).train(data=str(a.data.resolve()),epochs=a.epochs,patience=10,imgsz=640,batch=a.batch,device=device,workers=0,project=str(target.parent),name=a.name,exist_ok=False,seed=42,hsv_v=.2,translate=.05,scale=.2,mosaic=.25,mixup=0)
            return
        if not a.candidate or not a.candidate.is_file():raise ValueError('Provide an existing --candidate checkpoint.')
        if not 0<a.threshold<1:raise ValueError('Threshold must be between 0 and 1.')
        # Compare through the same detector/filters used by the production worker.
        import detector
        thresholds=[.25,.35,.45,.55] if a.split=='val' else [a.threshold]
        reports=[]
        images=sorted((base/config[a.split]).glob('*.jpg'));labels=(base/config[a.split]).parent.parent/'labels'/a.split
        if not labels.is_dir():labels=(base/config[a.split]).parent/'labels'
        for model in [ROOT/'ml/yolo11m.pt',a.candidate.resolve()]:
            detector._model=None;detector.MODEL_NAME=str(model);detector.IMG_SIZE=960
            detector.get_model()
            for threshold in thresholds:
                detector.CONF_THRESHOLD=threshold;tp=tn=fp=fn=0;events={}
                for image in images:
                    truth=bool((labels/(image.stem+'.txt')).read_text().strip());r=detector.verify_person(image,conf=threshold);pred=bool(r['person'])
                    tp+=truth and pred;tn+=not truth and not pred;fp+=not truth and pred;fn+=truth and not pred
                    event='-'.join(image.stem.split('-')[:-1]) if len(image.stem.split('-'))==4 else image.stem
                    e=events.setdefault(event,{'truth':False,'pred':False});e['truth']|=truth;e['pred']|=pred
                positives=sum(e['truth'] for e in events.values());negatives=len(events)-positives
                reports.append({'model':str(model),'split':a.split,'threshold':threshold,'tp':tp,'tn':tn,'fp':fp,'fn':fn,'person_recall':tp/(tp+fn) if tp+fn else None,'precision':tp/(tp+fp) if tp+fp else None,'person_event_recall':sum(e['truth'] and e['pred'] for e in events.values())/positives if positives else None,'empty_event_false_alarm_rate':sum(not e['truth'] and e['pred'] for e in events.values())/negatives if negatives else None,'events':len(events)})
        out=ROOT/'ml/camera_labels'/('comparison-'+a.split+'.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(reports,indent=2),encoding='utf-8');print(json.dumps(reports,indent=2));print('Saved',out)
    except (ValueError,KeyError,OSError) as exc:p.exit(1,str(exc)+'\n')
if __name__=='__main__':run()
