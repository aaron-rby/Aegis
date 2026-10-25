"""Isolated live-reading tests. No device is opened and no production samples are written."""
import os
import tempfile
import threading
import time
from unittest.mock import patch

from fastapi.testclient import TestClient
from serial_bridge import SerialBridge, parse_sensor_line


def run():
    motion = "PIR:MOTION | ECHO:3200 us | DISTANCE:55.2 cm | OBJECT | AGREEMENT:3/3 | ARMED"
    no_echo = "PIR:CLEAR | ECHO:0 us | NO ECHO | INVALID | AGREEMENT:0/3 | WAIT CLEAR"
    assert parse_sensor_line(motion) == {"pir": True, "distance_cm": 55.2, "agreement": 3,
                                        "agreement_required": 3, "controller_state": "ARMED"}
    assert parse_sensor_line(no_echo)["distance_cm"] is None
    assert parse_sensor_line(no_echo)["pir"] is False
    assert parse_sensor_line(no_echo)["controller_state"] == "WAIT CLEAR"
    assert parse_sensor_line(motion + " | CAMERA:BUSY")["camera_ready"] is False
    assert parse_sensor_line(motion + " | CAMERA:READY")["camera_ready"] is True
    assert "camera_ready" not in parse_sensor_line(motion)
    for bad in ("Starting camera...", "BUZZER: two-second alarm", "GPIO19 returned LOW", "PIR:MOTION", "{}"): 
        assert parse_sensor_line(bad) is None
    assert parse_sensor_line('{"pir":true,"distance_cm":null}')["distance_cm"] is None
    assert parse_sensor_line('{"pir":false,"distance_cm":81.5,"camera_ready":true}')["camera_ready"] is True
    for bad in ('{"pir":true,"distance_cm":NaN}', '{"pir":true,"distance_cm":-1}',
                '{"pir":"HIGH","distance_cm":55}', '{"pir":true,"distance_cm":true}'):
        assert parse_sensor_line(bad) is None
    print("PASS: documented controller logs, missing echoes, JSON, unknown status and corrupt input")

    with tempfile.TemporaryDirectory(prefix="sentinel-live-test-") as storage:
        os.environ["SENTINEL_DATA_DIR"] = storage
        import app as service
        client = TestClient(service.app)
        assert client.get("/api/hardware").json()["history"] == []
        # Confirm no stale optional metadata carries over between sources/samples.
        service.record_sample({"device_id": "test", "pir": True, "distance_cm": 30,
                               "camera_ready": True, "transport": "wifi"})
        service.record_sample({"device_id": "test", "pir": False, "distance_cm": None, "transport": "usb"})
        h = client.get("/api/hardware").json()
        # A fabricated USB snapshot cannot claim online without the matching reader.
        assert not h["online"] and len(h["history"]) == 2 and "camera_ready" not in h
        service.usb_disconnected()
        assert client.get("/api/hardware").json()["online"] is False
        for _ in range(1205):
            service.record_sample({"device_id": "test", "pir": False, "distance_cm": 90, "transport": "usb"})
        assert len(client.get("/api/hardware").json()["history"]) == 1200
        service.HARDWARE["received_epoch"] = time.time() - 16
        assert client.get("/api/hardware").json()["online"] is False
        assert client.post("/api/serial/disconnect", headers={"Origin": "https://untrusted.example"}).status_code == 403
        assert client.post("/api/serial/connect", json={"port": "NONEXISTENT", "baudrate": 115200}).status_code == 409
        print("PASS: bounded history, no metadata carryover, freshness, disconnects and origin restriction")

        delivered = threading.Event()
        samples = []

        class FakeSerial:
            def __init__(self, **kwargs):
                self.port = None
                self.buffer = bytearray(("BOOT\n" + motion + "\n" + no_echo + "\n").encode())
                self.closed = False
            @property
            def in_waiting(self):
                return len(self.buffer)
            def open(self):
                pass
            def read(self, n):
                chunk = bytes(self.buffer[:n])
                del self.buffer[:n]
                if not chunk:
                    threading.Event().wait(.01)
                return chunk
            def close(self):
                self.closed = True

        def receive(value):
            samples.append(value)
            service.record_sample(value)
            if len(samples) == 2:
                delivered.set()

        bridge = SerialBridge(receive, service.usb_disconnected)
        with patch("serial_bridge.serial.Serial", FakeSerial), patch.object(SerialBridge, "ports", return_value=[{"port": "COM_TEST"}]):
            bridge.connect("COM_TEST", 115200)
            assert delivered.wait(timeout=3)
            # The callback signals before the last counter update; wait for the thread to record it.
            limit = time.monotonic() + 1
            while bridge.status()["samples_received"] != 2 and time.monotonic() < limit:
                threading.Event().wait(.01)
            assert bridge.status()["lines_received"] == 3
            assert bridge.status()["samples_received"] == 2
            assert samples[0]["distance_cm"] == 55.2 and samples[1]["distance_cm"] is None
            bridge.disconnect()
            assert not bridge.status()["connected"]
            assert not client.get("/api/hardware").json()["online"]
        print("PASS: threaded serial transport reads existing logs, ignores boot text, and disconnects cleanly")
        import serial
        class LockedSerial(FakeSerial):
            def open(self):
                raise serial.SerialException("Access denied")
        with patch("serial_bridge.serial.Serial", LockedSerial), patch.object(SerialBridge, "ports", return_value=[{"port": "COM_TEST"}]):
            try:
                bridge.connect("COM_TEST")
                raise AssertionError("Locked port should fail")
            except ValueError:
                assert not bridge.status()["connected"]
                assert "Could not open" in bridge.status()["error"]
        print("PASS: locked-port errors replace stale disconnect messages")
        service.POOL.shutdown(wait=True)
    print("Live-reading checks passed. Physical USB readings require a connected ESP32.")


if __name__ == "__main__":
    run()
