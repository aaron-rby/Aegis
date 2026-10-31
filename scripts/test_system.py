"""Regression tests for cancelled launcher startup and Windows batch exit codes."""
import contextlib,importlib.util,io,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
spec=importlib.util.spec_from_file_location('aegis_system',Path(__file__).with_name('system.py'))
system=importlib.util.module_from_spec(spec);spec.loader.exec_module(system)
class StartupTests(unittest.TestCase):
 def test_interrupt_returns_130_without_opening_browser(self):
  with patch.object(sys,'argv',['system.py','start']),patch.object(system,'settings',return_value={}),patch.object(system,'start',side_effect=KeyboardInterrupt),patch.object(system.webbrowser,'open') as browser,contextlib.redirect_stderr(io.StringIO()) as err:
   self.assertEqual(system.main(),130);browser.assert_not_called();self.assertIn('cancelled',err.getvalue())
 def test_success_requires_hardware_readback(self):
  response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'hardware_monitor_version':1}).encode()
  with patch.object(sys,'argv',['system.py','start']),patch.object(system,'settings',return_value={}),patch.object(system,'start'),patch.object(system,'urlopen',return_value=response),patch.object(system.webbrowser,'open') as browser:
   self.assertEqual(system.main(),0);browser.assert_called_once_with('http://localhost:5000/#hardware')
 def test_batch_rejects_positive_and_negative_exit_codes(self):
  source=(Path(__file__).resolve().parents[1]/'START_ALL.bat').read_text()
  command='"ml\\.venv\\Scripts\\python.exe" -u "scripts\\system.py" start'
  self.assertIn(command,source)
  with tempfile.TemporaryDirectory(prefix='aegis-startup-fixture-') as folder:
   root=Path(folder).resolve()
   self.assertTrue(root.is_relative_to(Path(tempfile.gettempdir()).resolve()))
   self.assertTrue(root.name.startswith('aegis-startup-fixture-'))
   dummy=root/'ml/.venv/Scripts/python.exe';dummy.parent.mkdir(parents=True);dummy.touch()
   for code in (0,1,130,-1073741510):
    with self.subTest(code=code):
     fixture=root/'launcher.bat';fixture.write_text(source.replace(command,f'cmd /d /c exit {code}').replace('  pause','  rem pause').replace('\npause','\nrem pause'),encoding='ascii')
     result=subprocess.run(['cmd.exe','/d','/c',str(fixture)],capture_output=True,text=True,timeout=10)
     if code==0:self.assertIn('Startup complete.',result.stdout);self.assertEqual(result.returncode,0)
     else:self.assertNotIn('Startup complete.',result.stdout);self.assertNotEqual(result.returncode,0)
if __name__=='__main__':unittest.main()
