"""Isolated parser, reader, telemetry and launcher checks. Never opens a real COM port."""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import serial
from fastapi.testclient import TestClient
from serial_bridge import SerialBridge, parse_sensor_line
import hardware_launcher

MOTION = "PIR:MOTION | ECHO:3200 us | DISTANCE:55.2 cm | OBJECT | AGREEMENT:3/3 | ARMED"
NO_ECHO = "PIR:CLEAR | ECHO:0 us | NO ECHO | INVALID | AGREEMENT:0/3 | WAIT CLEAR"
PORTS = [{"port": "COM_FIXTURE", "description": "Isolated fixture"}, {"port": "COM_OTHER"}]


class FakeSerial:
    instances = []
    opened = 0

    def __init__(self, **kwargs):
        self.port = None
        self.buffer = bytearray()
        self.closed = False
        self.fail = False
        self.guard = threading.Lock()
        self.instances.append(self)

    @property
    def in_waiting(self):
        return len(self.buffer)

    def open(self):
        type(self).opened += 1

    def feed(self, data):
        with self.guard:
            self.buffer.extend(data)

    def read(self, n):
        if self.fail:
            raise serial.SerialException("Fixture unplug")
        with self.guard:
            data = bytes(self.buffer[:n])
            del self.buffer[:n]
        if not data:
            threading.Event().wait(.005)
        return data

    def write(self, data):
        raise AssertionError("The bridge must never write serial commands")

    def close(self):
        self.closed = True


def eventually(predicate):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if predicate():
            return
        threading.Event().wait(.01)
    raise AssertionError("Fixture condition was not reached")


class ParserTests(unittest.TestCase):
    def test_documented_line(self):
        self.assertEqual(parse_sensor_line(MOTION), {"pir": True, "distance_cm": 55.2,
            "agreement": 3, "agreement_required": 3, "controller_state": "ARMED"})

    def test_no_echo_not_zero(self):
        parsed = parse_sensor_line(NO_ECHO)
        self.assertIsNone(parsed["distance_cm"])
        self.assertFalse(parsed["pir"])
        self.assertEqual(parsed["controller_state"], "WAIT CLEAR")

    def test_bad_input_and_trigger_do_not_create_samples(self):
        for line in ("", "BOOT", "GPIO19 returned LOW", "CAMERA READY", "BUZZER: two-second alarm",
                     "PIR:MOTION", "PIR:CLEAR | DISTANCE:-1 cm", "PIR:MOTION | DISTANCE:1001 cm",
                     '{"pir":true,"distance_cm":NaN}', '{"pir":true,"distance_cm":true}',
                     '{"pir":"HIGH","distance_cm":55}', '{"pir":true}'):
            with self.subTest(line=line): self.assertIsNone(parse_sensor_line(line))

    def test_only_explicit_camera_state(self):
        self.assertNotIn("camera_ready", parse_sensor_line(MOTION))
        self.assertTrue(parse_sensor_line(MOTION + " | CAMERA:READY")["camera_ready"])
        self.assertFalse(parse_sensor_line(MOTION + " | CAMERA:NOT READY")["camera_ready"])

    def test_json_metadata(self):
        result = parse_sensor_line(json.dumps({"pir": False, "distance_cm": None, "agreement": 1,
            "agreement_required": 3, "controller_state": "ARMED", "buzzer_active": False}))
        self.assertEqual(result["agreement"], 1)
        self.assertFalse(result["buzzer_active"])


class ReaderTests(unittest.TestCase):
    def setUp(self):
        FakeSerial.instances = []
        FakeSerial.opened = 0
        self.samples = []
        self.bridge = SerialBridge(self.samples.append)
        self.patches = [patch("serial_bridge.serial.Serial", FakeSerial), patch.object(SerialBridge, "ports", return_value=PORTS)]
        for item in self.patches: item.start()

    def tearDown(self):
        self.bridge.disconnect()
        for item in reversed(self.patches): item.stop()

    def test_open_does_not_claim_samples_or_auto_write(self):
        self.bridge.connect("COM_FIXTURE")
        self.assertEqual(self.bridge.status()["samples_received"], 0)
        self.assertEqual(self.samples, [])
        self.assertFalse(FakeSerial.instances[-1].dtr)
        self.assertFalse(FakeSerial.instances[-1].rts)

    def test_partial_lines_and_rejected_boot(self):
        self.bridge.connect("COM_FIXTURE")
        handle = FakeSerial.instances[-1]
        handle.feed(("BOOT\n" + MOTION[:20]).encode())
        eventually(lambda: self.bridge.status()["lines_received"] == 1)
        self.assertEqual(self.samples, [])
        handle.feed((MOTION[20:] + "\r\n" + NO_ECHO + "\n").encode())
        eventually(lambda: len(self.samples) == 2)
        self.assertEqual(self.samples[0]["distance_cm"], 55.2)
        self.assertIsNone(self.samples[1]["distance_cm"])

    def test_concurrent_tabs_reuse_one_reader(self):
        barrier = threading.Barrier(3)
        errors = []
        def connect():
            barrier.wait()
            try: self.bridge.connect("COM_FIXTURE")
            except Exception as exc: errors.append(exc)
        threads = [threading.Thread(target=connect) for _ in range(2)]
        for thread in threads: thread.start()
        barrier.wait()
        for thread in threads: thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(FakeSerial.opened, 1)
        with self.assertRaisesRegex(ValueError, "Disconnect"):
            self.bridge.connect("COM_OTHER")

    def test_unplug_and_reconnect_have_distinct_sessions(self):
        self.bridge.connect("COM_FIXTURE")
        session = self.bridge.status()["session_id"]
        FakeSerial.instances[-1].fail = True
        eventually(lambda: not self.bridge.status()["connected"])
        self.assertIn("USB connection lost", self.bridge.status()["error"])
        self.bridge.connect("COM_FIXTURE")
        self.assertNotEqual(session, self.bridge.status()["session_id"])
        self.assertIsNone(self.bridge.status()["last_sample"])

    def test_busy_port_error(self):
        with patch.object(FakeSerial, "open", side_effect=serial.SerialException("Access denied")):
            with self.assertRaisesRegex(ValueError, "Serial Monitor"):
                self.bridge.connect("COM_FIXTURE")
        self.assertFalse(self.bridge.status()["connected"])


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="sentinel-hardware-fixture-", dir=Path(__file__).resolve().parent)
        os.environ["SENTINEL_DATA_DIR"] = cls.temp.name
        import app
        cls.service = app
        cls.client = TestClient(app.app)

    @classmethod
    def tearDownClass(cls):
        cls.service.USB.disconnect()
        cls.service.POOL.shutdown(wait=True)
        cls.temp.cleanup()

    def setUp(self):
        self.service.HARDWARE.clear()
        self.service.SENSOR_HISTORY.clear()

    def test_offline_initially_and_serial_open_not_online(self):
        with patch.object(self.service.USB, "status", return_value={"connected": True, "port": "COM_FIXTURE"}):
            result = self.client.get("/api/hardware").json()
            self.assertFalse(result["online"])
            self.assertEqual(result["history"], [])

    def test_fresh_stale_disconnected_and_session(self):
        self.service.record_sample({"pir": True, "distance_cm": 55.2, "transport": "usb", "session_id": "a"})
        with patch.object(self.service.USB, "status", return_value={"connected": True, "session_id": "a"}):
            self.assertTrue(self.client.get("/api/hardware").json()["online"])
            self.service.HARDWARE["received_epoch"] -= 16
            self.assertFalse(self.client.get("/api/hardware").json()["online"])
        self.service.record_sample({"pir": True, "distance_cm": 55.2, "transport": "usb", "session_id": "old"})
        with patch.object(self.service.USB, "status", return_value={"connected": True, "session_id": "new"}):
            self.assertFalse(self.client.get("/api/hardware").json()["online"])

    def test_history_window_and_no_optional_carryover(self):
        self.service.record_sample({"pir": True, "distance_cm": 20, "transport": "wifi", "camera_ready": True})
        self.service.SENSOR_HISTORY[-1]["received_epoch"] -= 61
        self.service.record_sample({"pir": False, "distance_cm": None, "transport": "wifi"})
        result = self.client.get("/api/hardware").json()
        self.assertTrue(result["online"])
        self.assertNotIn("camera_ready", result)
        self.assertEqual(len(result["history"]), 1)
        self.assertIsNone(result["distance_cm"])

    def test_strict_telemetry_and_origin_control(self):
        headers = {"X-Device-Token": self.service.DEVICE_TOKEN}
        valid = {"device_id": "fixture", "pir": True, "distance_cm": 55.2}
        self.assertEqual(self.client.post("/api/hardware/telemetry", json=valid).status_code, 401)
        for payload in ({**valid, "pir": "yes"}, {**valid, "distance_cm": True}, {"device_id": "fixture", "pir": True}):
            self.assertEqual(self.client.post("/api/hardware/telemetry", headers=headers, json=payload).status_code, 422)
        self.assertEqual(self.client.post("/api/hardware/telemetry", headers=headers, json=valid).status_code, 200)
        self.assertEqual(self.client.post("/api/serial/disconnect", headers={"Origin": "https://other.example"}).status_code, 403)

    def test_history_is_bounded(self):
        for _ in range(1205):
            self.service.record_sample({"pir": False, "distance_cm": 91, "transport": "wifi"})
        self.assertEqual(len(self.service.SENSOR_HISTORY), 1200)


class LauncherTests(unittest.TestCase):
    def test_reuses_service_without_process_creation(self):
        with patch.object(hardware_launcher, "probe", return_value={"status": "ok"}), patch.object(hardware_launcher.subprocess, "Popen") as popen:
            self.assertFalse(hardware_launcher.ensure_service()[1])
            popen.assert_not_called()

    def test_checks_again_after_lock_before_starting(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            with patch.object(hardware_launcher, "probe", side_effect=[None, {"status": "ok"}]), patch.object(hardware_launcher.subprocess, "Popen") as popen:
                self.assertFalse(hardware_launcher.ensure_service(Path(folder))[1])
                popen.assert_not_called()

    def test_starts_once_and_waits_for_health(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            with patch.object(hardware_launcher, "probe", side_effect=[None, None, None, {"status": "ok"}]), patch.object(hardware_launcher.subprocess, "Popen") as popen, patch.object(hardware_launcher.time, "sleep"), patch.object(hardware_launcher.socket, "socket"):
                popen.return_value.poll.return_value = None
                self.assertTrue(hardware_launcher.ensure_service(Path(folder))[1])
                self.assertEqual(popen.call_count, 1)

    def test_startup_failure_reports_log(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            with patch.object(hardware_launcher, "probe", return_value=None), patch.object(hardware_launcher.subprocess, "Popen") as popen, patch.object(hardware_launcher.socket, "socket"):
                popen.return_value.poll.return_value = 1
                popen.return_value.returncode = 1
                with self.assertRaisesRegex(RuntimeError, "exited with code 1"):
                    hardware_launcher.ensure_service(Path(folder))

    def test_wrong_service_rejected(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"status":"ok","service":"unrelated"}'
        with patch.object(hardware_launcher.OPENER, "open", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "different service"):
                hardware_launcher.probe()

    def test_occupied_unresponsive_port_does_not_spawn(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            with patch.object(hardware_launcher, "probe", return_value=None), patch.object(hardware_launcher.subprocess, "Popen") as popen, patch.object(hardware_launcher.socket, "socket", side_effect=OSError("in use")):
                with self.assertRaisesRegex(RuntimeError, "No duplicate"):
                    hardware_launcher.ensure_service(Path(folder))
                popen.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
