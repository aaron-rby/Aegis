import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import Store

class EventDeleteTests(unittest.TestCase):
    def test_whole_burst_stays_deleted_after_restart_and_late_upload(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); caps=root/'captures'; preds=root/'predictions';caps.mkdir();preds.mkdir()
            db=root/'test.db'; store=Store(db,caps,preds)
            burst='582ABD7BB88C-abc-1'
            for number in (1,2):
                f=caps/f'{burst}-{number}.jpg'; f.write_bytes(b'fixture');store.add_photo(f)
            other=caps/'other.jpg';other.write_bytes(b'fixture');store.add_photo(other)
            self.assertEqual(store.delete_event(burst)['frames'],2)
            self.assertIsNone(store.photo(burst+'-1'))
            self.assertEqual(store.photos_page(1,100)['total'],1)
            self.assertTrue((caps/(burst+'-1.jpg')).exists())
            store=Store(db,caps,preds);store.import_captures()
            late=caps/f'{burst}-3.jpg';late.write_bytes(b'fixture');store.add_photo(late)
            self.assertEqual(store.photos_page(1,100)['total'],1)
            self.assertIsNone(store.delete_event(burst))
            self.assertEqual(store.delete_event('capture:other')['frames'],1)
            self.assertEqual(store.photos_page(1,100)['total'],0)
