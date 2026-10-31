"""Compare candidate and baseline on held-out camera frames through Aegis's real detector."""
from pathlib import Path
import argparse,collections,gc,json,os,statistics
ROOT=Path(__file__).resolve().parents[1]

def iou(a,b):
 inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
 return inter/union if union>0 else 0

def evaluate(candidate, data, output, split='val'):
 import detector,torch
 rows=[r for r in json.loads((data/'manifest.json').read_text()) if r['source']=='camera' and r['split']==split]
 if not rows or not any(r['boxes'] for r in rows) or not any(not r['boxes'] for r in rows):raise ValueError('Camera split needs person and empty images')
 reports=[]
 for name,model in [('baseline',data/'weights/yolo11m.pt'),('candidate',candidate)]:
  detector._model=None;detector._device=None;gc.collect();torch.cuda.empty_cache()
  detector.MODEL_NAME=str(model);detector.IMG_SIZE=960;detector.CONF_THRESHOLD=.35
  detector.MIN_BOX_AREA=.005;detector.MIN_BOX_HEIGHT=.10;detector.MAX_ASPECT=3.;detector.USE_TTA=False;detector.ENHANCE_DARK=True;detector.ZOOM_OUT_PASS=True;detector.ZOOM_PAD=.5
  detector.get_model();counts=collections.Counter();details=[];events={};durations=[]
  for row in rows:
   result=detector.verify_person(data/row['file'],conf=.35)
   truth=bool(row['boxes']);pred=bool(result['person']);counts['tp' if truth and pred else 'fn' if truth else 'fp' if pred else 'tn']+=1
   width,height=row['width'],row['height']
   # Manifest boxes use normalized YOLO center x/y/width/height.
   truth_boxes=[[(x-w/2)*width,(y-h/2)*height,(x+w/2)*width,(y+h/2)*height] for x,y,w,h in row['boxes']]
   used=set();matched=0
   for box in sorted(result['boxes'],key=lambda b:b['confidence'],reverse=True):
    matches=[(iou(box['box'],gt),j) for j,gt in enumerate(truth_boxes) if j not in used]
    score,j=max(matches,default=(0,-1))
    if score>=.5:used.add(j);matched+=1
   counts['box_tp']+=matched;counts['box_fp']+=len(result['boxes'])-matched;counts['box_fn']+=len(truth_boxes)-matched
   event=row['original_name'].rsplit('-',1)[0];e=events.setdefault(event,{'truth':False,'prediction':False});e['truth']|=truth;e['prediction']|=pred
   durations.append(result['ms']);details.append({'original_name':row['original_name'],'truth':truth,'prediction':pred,'boxes':result['boxes'],'ms':result['ms']})
  tp,fp,fn=counts['tp'],counts['fp'],counts['fn'];btp,bfp,bfn=counts['box_tp'],counts['box_fp'],counts['box_fn']
  report={'model':name,'checkpoint':str(model),'split':split,'camera_images':len(rows),'threshold':.35,'counts':dict(counts),'image_precision':tp/(tp+fp) if tp+fp else None,'image_recall':tp/(tp+fn) if tp+fn else None,'box_precision_iou50':btp/(btp+bfp) if btp+bfp else None,'box_recall_iou50':btp/(btp+bfn) if btp+bfn else None,'median_inference_ms':statistics.median(durations),'events':events,'frames':details}
  reports.append(report);print(json.dumps({k:v for k,v in report.items() if k not in ('events','frames')}),flush=True)
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps({'reports':reports,'limitations':['Small camera validation set; keep the independent test set untouched.','GPU timing does not establish CPU deployment latency.','No automatic model deployment.']},indent=2),encoding='utf-8')
 return reports

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--data',type=Path,default=ROOT/'ml/gpu_dataset_20261026');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if not a.candidate.is_file():p.error('Candidate checkpoint missing')
 os.environ['CONF_THRESHOLD']='0.35';os.environ['IMG_SIZE']='960'
 evaluate(a.candidate.resolve(),a.data.resolve(),a.output.resolve())
