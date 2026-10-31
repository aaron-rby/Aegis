"""Read ESP32 sensor logs and send an explicit manual camera request. Never flashes firmware."""
from __future__ import annotations

import json
import math
import re
import threading
import time
import uuid

import serial
from serial.tools import list_ports


def parse_sensor_line(line: str):
    """Accept sensor JSON or the existing PIR:MOTION | DISTANCE:55.2 cm log format.

    Invalid echo stays None. Unknown camera/buzzer state stays unknown.
    Unrelated boot, upload, and alarm messages are not sensor heartbeats.
    """
    line = line.strip()
    if line.startswith("{"):
        try:
            value = json.loads(line)
            if not isinstance(value, dict) or type(value.get("pir")) is not bool:
                return None
            if "distance_cm" not in value:
                return None
            distance = value["distance_cm"]
            if distance is not None and (type(distance) not in (int, float) or not math.isfinite(distance) or not 0 <= distance <= 1000):
                return None
            result = {"pir": value["pir"], "distance_cm": distance}
            agreement = value.get("agreement")
            required = value.get("agreement_required")
            if type(agreement) is int and type(required) is int and 0 <= agreement <= required <= 100:
                result.update(agreement=agreement, agreement_required=required)
            if value.get("controller_state") in {"ARMED", "WAIT CLEAR", "BUSY", "FAULT", "WAIT CAMERA"}:
                result["controller_state"] = value["controller_state"]
            for key in ("camera_ready", "buzzer_active"):
                if type(value.get(key)) is bool:
                    result[key] = value[key]
            if type(value.get("rssi")) is int and -150 <= value["rssi"] <= 0:
                result["rssi"] = value["rssi"]
            return result
        except (ValueError, TypeError):
            return None
    pir = re.search(r"\bPIR\s*:\s*(MOTION|CLEAR|HIGH|LOW|1|0)\b", line, re.I)
    distance = re.search(r"\bDISTANCE\s*:\s*(\d+(?:\.\d+)?)\s*cm\b", line, re.I)
    no_echo = bool(re.search(r"\bNO\s+ECHO\b", line, re.I))
    if not pir or (not distance and not no_echo):
        return None
    cm = None if no_echo else float(distance.group(1))
    if cm is not None and not 0 <= cm <= 1000:
        return None
    result = {"pir": pir.group(1).upper() in {"MOTION", "HIGH", "1"}, "distance_cm": cm}
    agreement = re.search(r"\bAGREEMENT\s*:\s*(\d+)\s*/\s*(\d+)", line, re.I)
    if agreement and 0 <= int(agreement.group(1)) <= int(agreement.group(2)) <= 100:
        result["agreement"] = int(agreement.group(1))
        result["agreement_required"] = int(agreement.group(2))
    if re.search(r"\bWAIT CLEAR\b", line, re.I):
        result["controller_state"] = "WAIT CLEAR"
    elif re.search(r"\bARMED\b", line, re.I):
        result["controller_state"] = "ARMED"
    camera = re.search(r"\bCAMERA\s*:\s*(READY|BUSY|OFFLINE|WAIT|NOT READY)\b", line, re.I)
    if camera:
        result["camera_state"] = camera.group(1).upper()
        result["camera_ready"] = result["camera_state"] == "READY"
    return result


class SerialBridge:
    def __init__(self, on_sample, on_disconnect=None):
        self.on_sample = on_sample
        self.on_disconnect = on_disconnect
        self.lock = threading.RLock()
        self.lifecycle = threading.Lock()
        self.handle = None
        self.last_trigger = None
        self.thread = None
        self.stop = threading.Event()
        self.state = {"connected": False, "port": None, "baudrate": 115200,
                      "lines_received": 0, "samples_received": 0, "last_sample": None, "error": None}

    @staticmethod
    def ports():
        return [{"port": p.device, "description": p.description, "manufacturer": p.manufacturer}
                for p in list_ports.comports()]

    def status(self):
        with self.lock:
            return dict(self.state)

    def connect(self, port, baudrate=115200):
        # Serialize the entire check/open/start operation, not just state writes.
        # A second browser tab reuses this reader or must explicitly disconnect it.
        with self.lifecycle:
            with self.lock:
                if self.state["connected"]:
                    if self.state["port"] == port and self.state["baudrate"] == baudrate:
                        return dict(self.state)
                    raise ValueError("Another USB connection is active. Disconnect it before selecting a different port or baud rate.")
            self._disconnect()
            return self._connect(port, baudrate)

    def _connect(self, port, baudrate):
        if baudrate not in (9600, 57600, 115200, 230400, 460800, 921600):
            raise ValueError("Unsupported baud rate")
        if port not in {p["port"] for p in self.ports()}:
            raise ValueError("This serial port is not detected. Connect the ESP32 with a USB data cable, then refresh ports.")
        handle = serial.Serial(port=None, baudrate=baudrate, timeout=0.5, write_timeout=1)
        # Avoid deliberately asserting reset/boot lines. Some USB adapters may still reset on open.
        handle.dtr = False
        handle.rts = False
        handle.port = port
        try:
            handle.open()
        except (serial.SerialException, OSError) as exc:
            handle.close()
            message = "Could not open the port. Close Arduino Serial Monitor, Serial Plotter, and any other program using it, then retry."
            with self.lock:
                self.state.update(connected=False, port=port, baudrate=baudrate, error=message)
            raise ValueError(message) from exc
        with self.lock:
            self.handle = handle
            self.stop = threading.Event()
            self.state = {"connected": True, "port": port, "baudrate": baudrate,
                          "session_id": uuid.uuid4().hex, "lines_received": 0,
                          "samples_received": 0, "last_sample": None, "error": None}
            self.thread = threading.Thread(target=self._read, args=(handle, self.stop, self.state["session_id"]), daemon=True)
            self.thread.start()
        return self.status()

    def trigger_camera(self):
        # Reuse the one existing port; never create another serial reader.
        with self.lifecycle, self.lock:
            now = time.monotonic()
            if not self.handle or not self.state["connected"]:
                raise ValueError("Connect the main ESP32 USB port in Hardware first.")
            last = self.state.get("last_sample")
            if last is None or time.time() - last >= 15:
                raise ValueError("Fresh controller readings are required before a manual trigger.")
            if self.state.get("controller_state") != "ARMED":
                raise ValueError("Controller is not armed. Clear the sensor zone and wait for rearming.")
            if self.last_trigger is not None and now - self.last_trigger < 3:
                raise ValueError("A trigger was just sent. Wait for the controller to update.")
            try:
                if self.handle.write(b"T\n") != 2:
                    raise ValueError("Incomplete USB command; capture is not confirmed.")
            except (serial.SerialException, OSError) as exc:
                raise ValueError("Could not send the camera request. Check USB and reconnect.") from exc
            self.last_trigger = now
            return {"sent": True, "detail": "Request sent to the controller. Waiting for camera uploads; capture is not yet confirmed."}

    def disconnect(self):
        with self.lifecycle:
            return self._disconnect()

    def _disconnect(self):
        with self.lock:
            self.stop.set()
            handle, thread = self.handle, self.thread
            self.handle = None
            self.thread = None
            self.state["connected"] = False
        if handle:
            try:
                handle.close()
            except (serial.SerialException, OSError):
                pass
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2)
            if thread.is_alive():
                with self.lock:
                    self.thread = thread
                    self.state["error"] = "The previous serial reader has not stopped. Unplug the board and retry; a second reader was not started."
                raise ValueError(self.state["error"])
        if self.on_disconnect:
            self.on_disconnect()
        return self.status()

    def _read(self, handle, stop, session_id):
        buffer = bytearray()
        try:
            while not stop.is_set():
                data = handle.read(min(handle.in_waiting or 1, 4096))
                if not data:
                    continue
                buffer.extend(data)
                while b"\n" in buffer and not stop.is_set():
                    raw, _, remaining = buffer.partition(b"\n")
                    buffer = bytearray(remaining)
                    line = raw.decode("utf-8", errors="replace").strip()
                    sample = parse_sensor_line(line) if len(raw) <= 8192 else None
                    with self.lock:
                        self.state["lines_received"] += 1
                    if sample:
                        with self.lock:
                            self.state["samples_received"] += 1
                            self.state["last_sample"] = time.time()
                            self.state["controller_state"] = sample.get("controller_state")
                        self.on_sample({**sample, "device_id": f"ESP32 · {handle.port}",
                                        "transport": "usb", "session_id": session_id})
                if len(buffer) > 8192:
                    buffer.clear()  # Bound unterminated or corrupted serial input.
        except (serial.SerialException, OSError, TypeError, ValueError):
            if not stop.is_set():
                with self.lock:
                    self.state["error"] = "USB connection lost. Reconnect the board and select its port again."
        finally:
            try:
                handle.close()
            except (serial.SerialException, OSError):
                pass
            with self.lock:
                current = self.handle is handle
                if current:
                    self.state["connected"] = False
                    self.handle = None
            if current and self.on_disconnect:
                self.on_disconnect()
