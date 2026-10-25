"""Read-only hardware monitoring and HTTP integration using isolated serial fixtures."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from hardware import HardwareMonitor
from serial_bridge import parse_sensor_line
from server import make_handler


class HardwareTests(unittest.TestCase):
    def test_no_echo_and_unrelated_logs(self):
        result = parse_sensor_line('PIR:CLEAR | ECHO:0 us | NO ECHO | INVALID | AGREEMENT:0/3 | WAIT CLEAR')
        self.assertIsNone(result['distance_cm'])
        self.assertFalse(result['pir'])
        for text in ('GPIO19 returned LOW', 'CAMERA READY', 'BUZZER: two-second alarm', 'BOOT'):
            self.assertIsNone(parse_sensor_line(text))

    def test_fresh_current_session_only(self):
        monitor = HardwareMonitor()
        self.assertFalse(monitor.snapshot()['online'])
        with patch.object(monitor.bridge, 'status', return_value={'connected': True, 'session_id': 'a'}):
            self.assertFalse(monitor.snapshot()['online'])
            monitor.receive({'pir': True, 'distance_cm': 55.2, 'session_id': 'a'})
            self.assertTrue(monitor.snapshot()['online'])
            monitor.last_monotonic -= 16
            self.assertFalse(monitor.snapshot()['online'])
            monitor.receive({'pir': False, 'distance_cm': None, 'session_id': 'old'})
            self.assertFalse(monitor.snapshot()['online'])

    def test_unknown_fields_not_carried_and_disconnect(self):
        monitor = HardwareMonitor()
        with patch.object(monitor.bridge, 'status', return_value={'connected': True, 'session_id': 'a'}):
            monitor.receive({'pir': True, 'distance_cm': 55.2, 'session_id': 'a', 'camera_ready': True})
            monitor.receive({'pir': False, 'distance_cm': None, 'session_id': 'a'})
            self.assertNotIn('camera_ready', monitor.snapshot())
            self.assertTrue(monitor.snapshot()['online'])
            monitor.lost()
            self.assertFalse(monitor.snapshot()['online'])

    def test_http_control_is_local_and_never_auto_connects(self):
        monitor = HardwareMonitor()
        handler_type = make_handler(Mock(), 'token', Path('model.pt'), hardware_monitor=monitor)
        def perform(path, method='GET', body=None, origin='http://localhost:5000', host='127.0.0.1'):
            handler = handler_type.__new__(handler_type)
            handler.path = path
            handler.client_address = (host, 10000)
            data = json.dumps(body).encode() if body else b''
            handler.headers = {'Origin': origin, 'Content-Type': 'application/json', 'Content-Length': str(len(data))}
            handler.rfile, handler.wfile = BytesIO(data), BytesIO()
            handler.connection = Mock()
            handler.send_response, handler.send_header, handler.end_headers = Mock(), Mock(), Mock()
            getattr(handler, 'do_' + method)()
            return handler.send_response.call_args.args[0], json.loads(handler.wfile.getvalue())
        with patch.object(monitor.bridge, 'connect', return_value={'connected': True}) as connect:
            self.assertFalse(perform('/api/hardware')[1]['online'])
            connect.assert_not_called()
            self.assertEqual(perform('/api/serial/connect', 'POST', {'port': 'COM_TEST'}, origin='https://evil.example')[0], 403)
            self.assertEqual(perform('/api/serial/connect', 'POST', {'port': 'COM_TEST'}, host='192.168.1.10')[0], 403)
            connect.assert_not_called()
            self.assertEqual(perform('/api/serial/connect', 'POST', {'port': 'COM_TEST', 'baudrate': 115200})[0], 200)
            connect.assert_called_once_with('COM_TEST', 115200)

    def test_history_excludes_old_and_previous_session(self):
        monitor = HardwareMonitor()
        monitor.receive({'pir': True, 'distance_cm': 55, 'session_id': 'old'})
        monitor.receive({'pir': False, 'distance_cm': None, 'session_id': 'new'})
        self.assertEqual(len(monitor.snapshot()['history']), 1)
        monitor.history[-1]['received_epoch'] -= 61
        self.assertEqual(monitor.snapshot()['history'], [])

    def test_startup_recognizes_current_and_previous_frontend(self):
        spec = importlib.util.spec_from_file_location('launcher_system', BACKEND.parent / 'scripts' / 'system.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for title in ('Sentinel AI — Intrusion Monitoring', 'Vigil — Intrusion Command Center'):
            response = Mock()
            response.status = 200
            response.read.return_value = f'<title>{title}</title>'.encode()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            with patch.object(module, 'urlopen', return_value=response):
                self.assertEqual(module.gallery_http(), (200, True))


if __name__ == '__main__':
    unittest.main()
