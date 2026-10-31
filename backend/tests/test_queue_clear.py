from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import Store
from worker import process_job
import cv2
import numpy as np

class QueueClearTests(TestCase):
 def setup_store(self,folder):
  r=Path(folder);c=r/'captures';p=r/'predictions';c.mkdir();p.mkdir()
  return Store(r/'db.sqlite3',c,p)
 def add(self,s,name):
  f=s.captures/(name+'.jpg');cv2.imwrite(str(f),np.zeros((60,60,3),dtype=np.uint8));s.add_photo(f)
 def test_clear_queued_processing_completed_and_future(self):
  with TemporaryDirectory() as folder:
   s=self.setup_store(folder)
   for name in ['a','b','c']:self.add(s,name)
   done=s.claim_job('w');s.finish_job(done['id'],'person_detected',{'person':True,'confidence':.8})
   running=s.claim_job('w');result=s.clear_processing_queue()
   self.assertEqual(result['cancelled'],2);self.assertEqual(result['processing_cancelled'],1)
   self.assertEqual(s.status(Path('m'))['jobs']['queued'],0)
   self.assertEqual(s.status(Path('m'))['jobs']['processing'],0)
   self.assertEqual(s.photo(done['id'])['ml_state'],'person_detected')
   self.assertEqual(s.photo(running['id'])['ml_state'],'cancelled')
   writer=Mock();self.assertFalse(s.finish_job(running['id'],'person_detected',{'person':True},write_artifacts=writer));writer.assert_not_called()
   self.assertEqual(s.recover_processing(),0);self.assertIsNone(s.claim_job('w'))
   s=Store(s.db_path,s.captures,s.predictions);s.import_captures()
   self.assertEqual(s.status(Path('m'))['jobs']['queued'],0)
   self.assertEqual(len(list(s.captures.glob('*.jpg'))),3)
   self.add(s,'new');self.assertEqual(s.claim_job('w')['id'],'new')
   self.assertEqual(s.clear_processing_queue()['cancelled'],1)
   self.assertEqual(s.clear_processing_queue()['cancelled'],0)
 def test_cancel_during_inference_discards_result_without_worker_failure(self):
  with TemporaryDirectory() as folder:
   s=self.setup_store(folder);self.add(s,'a');job=s.claim_job('w');detector=Mock()
   detector.load_image.return_value=np.zeros((60,60,3),dtype=np.uint8)
   def infer(*args,**kwargs):
    s.clear_processing_queue();return {'person':True,'confidence':.99,'count':1,'boxes':[]}
   detector.verify_person.side_effect=infer
   state,_=process_job(s,job,detector,cv2,Path('model.pt'),.35)
   self.assertEqual(state,'cancelled');detector.annotate.assert_not_called()
   self.assertEqual(list(s.predictions.iterdir()),[])
   self.assertEqual(s.photo('a')['ml_state'],'cancelled')
