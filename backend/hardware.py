"""Read-only USB telemetry for the port-5000 capture dashboard."""
from collections import deque
from datetime import datetime, timezone
import threading
import time

from serial_bridge import SerialBridge


class HardwareMonitor:
    def __init__(self):
        self.lock = threading.RLock()
        self.latest = {}
        self.history = deque(maxlen=1200)
        self.last_monotonic = None
        self.disconnected = True
        self.bridge = SerialBridge(self.receive, self.lost)

    def receive(self, sample):
        with self.lock:
            self.latest = {**sample, "received_at": datetime.now(timezone.utc).isoformat(),
                           "received_epoch": time.time()}
            self.last_monotonic = time.monotonic()
            self.disconnected = False
            self.history.append(dict(self.latest))

    def lost(self):
        with self.lock:
            self.disconnected = True

    def snapshot(self):
        serial = self.bridge.status()
        with self.lock:
            age = None if self.last_monotonic is None else max(0, time.monotonic() - self.last_monotonic)
            online = bool(self.latest) and not self.disconnected and age is not None and age < 15 and (
                serial["connected"] and self.latest.get("session_id") == serial.get("session_id"))
            history = [dict(p) for p in self.history if p["received_epoch"] >= time.time() - 60
                       and p.get("session_id") == self.latest.get("session_id")]
            return {**self.latest, "online": bool(online), "serial": serial,
                    "sample_age_seconds": age, "stale_after_seconds": 15,
                    "history": history, "hardware_monitor_version": 1}
