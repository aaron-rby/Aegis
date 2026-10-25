# Sentinel hardware monitor

Run `START_HARDWARE.bat` in the parent project folder. It starts or reuses the
existing local Python service and opens http://127.0.0.1:8765/#hardware. Existing
`START_SERVER.bat` and `website/START_SENTINEL.bat` are preserved.

The launcher does not open COM ports. Close Arduino Serial Monitor/Plotter,
refresh ports, select the main ESP32 COM port, keep 115200 baud and click
**Connect USB**. Disconnect here before reopening Serial Monitor. No serial
commands or firmware changes are performed. Some USB adapters reset on opening
even when DTR/RTS are not deliberately asserted.

## Readings and charts

The controller's existing `PIR:MOTION | ECHO:3200 us | DISTANCE:55.2 cm | OBJECT |
AGREEMENT:3/3 | ARMED` format is supported. Newline-delimited sensor JSON is also
accepted. NO ECHO produces a null/invalid distance, never zero centimetres.
Motion readings can still arrive while the echo is invalid.

Online means a recognized sensor snapshot arrived less than 15 seconds ago;
for USB it must belong to the currently open serial session. Opening a port,
boot messages, buzzer text and trigger pulses do not establish live readings.
Unplugging marks the connection offline. Recovery is explicit: refresh ports,
select the board and connect again. Concurrent browser tabs reuse one reader.

The Hardware page polls once per second. Its distance and motion charts show
received samples from the current source/session within the last 60 seconds.
Invalid echo samples and time gaps break the distance trace. Camera readiness
and buzzer state stay **Not reported** unless explicitly supplied in a valid
sensor snapshot. No capture success is inferred from GPIO19 activity.

## Matching direct-trigger wiring

| Connection | Pin |
| --- | --- |
| PIR output | Main ESP32 GPIO13 |
| Ultrasonic TRIG | Main GPIO5 |
| Ultrasonic ECHO | Divider tap to main GPIO18 |
| Camera trigger | Main GPIO19 directly to ESP32-CAM GPIO13 |
| Ground | Common main/camera/sensor GND |
| Trigger pull-down | Trigger node to resistor to GND, a parallel branch |

Never place the trigger pull-down in series between the GPIOs. Physical HC-SR04
ECHO requires the voltage divider. Alternative firmware branches use different
pins; follow the matching firmware/guide.

## Startup troubleshooting

- Missing Python environment: follow `README.md` to create `website/.venv`.
- Startup errors: read the terminal and `data/hardware-service.log`.
- Occupied/unresponsive port: launcher does not terminate it or start a duplicate.
- Older service already running: the launcher reuses it and reports that its own
  terminal must be restarted manually to load the updated Python bridge.
- Busy COM port: close Serial Monitor/Plotter yourself; no programs are closed
  automatically.
- USB open but Offline: verify baud rate, board power and recognized sensor logs.
- Missing echoes: inspect sensor wiring and divider; missing echo is not clearance.

The background service continues after the launcher exits. Use the existing
service terminal for manual lifecycle management when applicable. The launcher
does not stop any process.

## Isolated verification

Run `.venv\Scripts\python.exe -m unittest test_hardware_monitor -v` from `website`.
Fixtures use temporary storage, mocked serial handles and mocked launcher
processes. No simulated readings are posted into the real dashboard.
