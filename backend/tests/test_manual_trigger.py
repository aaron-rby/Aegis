import sys,time,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from serial_bridge import SerialBridge

class ManualTriggerTests(unittest.TestCase):
    def ready(self):
        b=SerialBridge(Mock()); b.handle=Mock(); b.handle.write.return_value=2
        b.state.update(connected=True,last_sample=time.time(),controller_state="ARMED")
        return b
    def test_one_command_and_duplicate_guard(self):
        b=self.ready(); self.assertTrue(b.trigger_camera()["sent"])
        b.handle.write.assert_called_once_with(b"T\n")
        with self.assertRaises(ValueError): b.trigger_camera()
        self.assertEqual(b.handle.write.call_count,1)
    def test_disconnected_stale_and_unarmed_never_write(self):
        for change in ({"connected":False},{"last_sample":time.time()-16},{"controller_state":"WAIT CLEAR"}):
            b=self.ready(); b.state.update(change)
            with self.assertRaises(ValueError): b.trigger_camera()
            b.handle.write.assert_not_called()
    def test_partial_write_does_not_confirm(self):
        b=self.ready(); b.handle.write.return_value=1
        with self.assertRaises(ValueError): b.trigger_camera()
