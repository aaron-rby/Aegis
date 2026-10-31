"""Recover CUDA training, adapt to reviewed camera frames, and compare candidates. Never deploys automatically."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'ml/gpu_dataset_20261026'
STATE=ROOT/'ml/camera_labels/gpu_training_status.json';LOGS=ROOT/'ml/camera_labels/gpu_training_logs'
GENERAL=DATA/'runs/aegis_person_local_gpu_v1';CAMERA=DATA/'runs/aegis_camera_local_gpu_v1'

def status(phase,**extra):
 record={'phase':phase,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),**extra}
 STATE.parent.mkdir(parents=True,exist_ok=True);temp=STATE.with_suffix('.tmp');temp.write_text(json.dumps(record,indent=2),encoding='utf-8');os.replace(temp,STATE)
 print(json.dumps(record),flush=True)

def run(phase,args):
 path=LOGS/(phase+'.log');status(phase,log=str(path))
 environment=os.environ.copy();environment['PYTHONUNBUFFERED']='1'
 with path.open('ab',buffering=0) as log:
  result=subprocess.run([sys.executable,*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=environment)
 return result.returncode,path

def require(phase,args):
 code,path=run(phase,args)
 if code:raise RuntimeError(f'{phase} failed with exit {code}; see {path}')

def complete(run_dir):
 """Final validation writes results.png only after optimizer stripping; inspect the checkpoint metadata instead."""
 # Completion marker is written only after a successful subprocess exit.
 return (run_dir/'aegis_stage_complete.json').is_file()

def train_stage(stage,directory):
 if complete(directory):return
 for attempt in range(1,4):
  code,path=run('fine_tuning_'+stage+f'_attempt{attempt}',['-u',str(ROOT/'scripts/aegis_gpu_stage.py'),stage,'--batch','1'])
  if code==0:
   (directory/'aegis_stage_complete.json').write_text(json.dumps({'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}));return
  with path.open('rb') as f:
   f.seek(max(0,path.stat().st_size-20000));tail=f.read().decode(errors='replace').lower()
  if not any(x in tail for x in ('out of memory','cudaerrormemoryallocation','cublas_status_alloc_failed')):raise RuntimeError(f'{stage} failed; see {path}')
  if attempt<3:status('waiting_after_gpu_memory_error',stage=stage,attempt=attempt);time.sleep(30)
 raise RuntimeError(f'{stage} exceeded CUDA memory even at batch 1; progress retained in {directory}')

def main():
 if Path(sys.executable).resolve().parent.parent.name!='.venv-gpu':raise RuntimeError('Use isolated ml/.venv-gpu Python')
 LOGS.mkdir(parents=True,exist_ok=True)
 import msvcrt
 with (LOGS/'coordinator.lock').open('a+b') as lock:
  if lock.tell()==0:lock.write(b'0');lock.flush()
  lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  require('verify_cuda_recovery',['-c',"import torch,torchvision; assert torch.cuda.is_available(); x=torch.ones(32,32,device='cuda'); print(torch.cuda.get_device_name(0),torch.version.cuda,(x@x).mean().item()); print(torchvision.ops.nms(torch.tensor([[0.,0.,10.,10.]],device='cuda'),torch.tensor([.9],device='cuda'),.5))"])
  train_stage('general',GENERAL);train_stage('camera',CAMERA)
  models=[('baseline',DATA/'weights/yolo11m.pt'),('general',GENERAL/'weights/best.pt'),('camera',CAMERA/'weights/best.pt')]
  for name,model in models:
   report=LOGS/(name+'_metrics_recovery.json')
   if not report.exists():
    code="from ultralytics import YOLO; import json; from pathlib import Path; r=YOLO("+repr(str(model))+").val(data="+repr(str(DATA/'data.runtime.yaml'))+",split='val',imgsz=960,batch=1,device=0,workers=0,project="+repr(str(DATA/'evaluation'))+",name="+repr('local_gpu_recovery_'+name)+",exist_ok=True,plots=False); Path("+repr(str(report))+").write_text(json.dumps(r.results_dict,indent=2,default=float))"
    require('validate_'+name+'_recovery',['-c',code])
   if name!='baseline':
    report=LOGS/('camera_comparison_'+name+'.json')
    if not report.exists():require('validate_camera_pipeline_'+name,['-u',str(ROOT/'ml/evaluate_gpu_candidate.py'),'--candidate',str(model),'--data',str(DATA),'--output',str(report)])
  status('completed_candidates_awaiting_review',candidates=[str(m) for n,m in models if n!='baseline'],metrics_folder=str(LOGS),deployed=False)

if __name__=='__main__':
 try:main()
 except Exception as exc:
  traceback.print_exc();status('failed',error=str(exc));sys.exit(1)
