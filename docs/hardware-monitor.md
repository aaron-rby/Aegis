# Hardware monitoring in the START_ALL dashboard

This integration belongs to `C:\Users\aaron\Pictures\AI-Intrusion-Detection`.
Run `START_ALL.bat`; its existing backend/ML startup now opens
http://localhost:5000/#hardware. It does not use the separate green website,
the port-8765 service, or `START_SENTINEL.bat`.
`START_HARDWARE.bat` in this same project is an optional shortcut to START_ALL,
not a second service or a separate UI.

The existing startup lock and backend/worker reuse logic remain in place. A
backend from before this update must be stopped in its own console and started
again to load the new hardware endpoints; no process is terminated automatically.

## Connect

1. Close Arduino Serial Monitor/Plotter yourself.
2. Open Hardware, click Refresh ports, choose the main ESP32 port.
3. Keep 115200 baud and click Connect USB.
4. Disconnect here before reopening Serial Monitor.

The reader only consumes existing logs; it does not send commands. No COM port
opens at page load or launcher startup. Some adapters reset the ESP32 when a
port opens despite DTR/RTS being kept inactive.

Online requires a recognized sensor sample within 15 seconds from the current
serial session. Opening a port alone is not Online. Boot, trigger and buzzer
messages do not refresh sensor freshness. NO ECHO produces an invalid distance,
not zero. Motion can still be reported when an ultrasonic echo is unavailable.
Camera and buzzer states stay Not reported unless explicitly included in a
recognized sensor snapshot. No camera capture is inferred from a GPIO pulse.

Hardware polls once per second. Distance and motion charts show the previous
60 seconds of actual samples, breaking the trace for invalid measurements or
long gaps. No fixture data is posted to the real dashboard.

## Matching pins

PIR → main GPIO13; TRIG → GPIO5; ECHO divider tap → GPIO18;
main GPIO19 → camera GPIO13; all boards/sensors share GND. The trigger pull-down
is a resistor branch from the trigger node to GND, never a series resistor
between the GPIOs. Alternative firmware branches have different pin maps.

## Endpoints

GET `/api/hardware` and `/api/serial/ports`; POST `/api/serial/connect` and
`/api/serial/disconnect`. USB control is restricted to loopback clients and
approved local origins. The existing camera upload and ML routes are preserved.

## Checks

From the project root:

    ml\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p test_hardware.py -v

From frontend: `node --test src/lib/events.test.js` and `npm run build`.

The validated read-only serial bridge was reused from the earlier isolated
hardware implementation. Physical readings still require a user-selected Connect USB.

## Verification on 25 October 2026

- Production React build passed.
- All 13 backend regression tests passed, including six hardware/API/startup checks.
- All six event-domain tests passed.
- Corrected START_ALL startup was exercised: the updated port-5000 backend became
  ready and the already-running ML worker was reused.
- The older port-5000 backend was restarted once with explicit user approval.
- Browser Hardware page detected COM6 and displayed actual received serial data
  at 115200 baud, including PIR, changing distance, agreement and WAIT CLEAR.
- More than 170 actual samples were observed; distance and motion charts updated.
- Camera readiness and buzzer state remained Not reported, as the controller did
  not explicitly supply them. No serial commands or fixture telemetry were sent.
- No horizontal overflow was observed at the checked 503 px browser width.
- Physical unplug/reconnect and camera/buzzer completion were not exercised.
