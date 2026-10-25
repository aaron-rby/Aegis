# Two-stage buzzer: sensor fusion and ML

The controller sketch is [`mlids.ino`](../firmware/main_ml_alarm/mlids/mlids.ino).
It preserves the sensor and camera-trigger wiring and implements two alarms:

| Trigger | Audible response |
| --- | --- |
| PIR HIGH + valid distance ≤80 cm for three consecutive samples | 1-second 2 kHz beep and the normal camera pulse |
| A new laptop `person_detected` result | 5-second 2 kHz beep |
| Manual T command | Camera test only; no short sensor beep |
| No-person, pending or failed ML result | No additional ML beep |

ML overrides an active short beep with a five-second alarm window. A later
sensor event cannot shorten or restart an active ML alarm. The short sensor
beep still works without Wi-Fi; the five-second beep requires the laptop and
network. Sensors indicate a presence candidate; ML detects the visual person class.

`AlarmTiming.h` defines the durations. A dedicated FreeRTOS task checks expiry
every 10 ms independently of HTTP polling, avoiding long buzzer timing delays
when the main loop is waiting on Wi-Fi. There is no one- or five-second blocking
delay in the sensor loop. Physical timing has not been measured on hardware.

The backend exposes `GET /api/alarm/latest` to the main ESP32. It requires `X-Alarm-Token`, returns a recent person-detected burst ID as plain text, or an empty body when there is no recent event. Both the upload and completed prediction must be less than 90 seconds old. It never returns imported legacy predictions. The board polls once per second, ignores the first successful reply at boot, and remembers the last burst ID to avoid repeatedly sounding for the same reply. Wait for the baseline connection message before testing a new event.

## Set up and flash

1. **Keep the current camera firmware.** Flash only the **main ESP32**. Save a copy of the main sketch currently in Arduino IDE first; the exact flashed binary is not verified.
2. Connect the laptop, main ESP32, and ESP32-CAM to the same reachable Wi-Fi/hotspot. Run `CHECK_SYSTEM.bat` and check the laptop's Wi-Fi IPv4. The camera's last known upload address was `172.20.10.7`, but check it again.
3. Open `backend/config.local.json` on the laptop. It now has an `alarm_token` value. Keep this file private. The camera's existing `camera_token` is a **different** value.
4. Open `firmware/main_ml_alarm/mlids/mlids.ino` in Arduino IDE. Keep `AlarmTiming.h` in the same sketch folder. Preserve/verify your configured hotspot credentials and `ALARM_TOKEN` against step 3. Set `ALARM_URL` to `http://<laptop Wi-Fi IPv4>:5000/api/alarm/latest`. Use the laptop's LAN IP, **not** `localhost`.
5. First **Disconnect USB in the website** so Arduino IDE can access the port. Select the main ESP32 board and its COM port (previously COM6, but check). Upload this sketch **only to the main board**. Open Serial Monitor at 115200 baud. Wait for `MAIN ESP32 READY` and `ML alarm connected; watching for NEW person detections.` If it prints `HTTP 401`, correct the alarm token. For negative HTTP codes, check Wi-Fi, laptop IP, firewall and backend. Close Serial Monitor before reconnecting USB in the website.
6. Run project-root `START_ALL.bat`. It starts/reuses the port-5000 backend and ML worker. Keep their windows open; the existing alarm route does not need a backend change for this firmware update.
7. Test automatic sensing with a well-lit person clearly in the camera view. Sensor agreement requests the **1-second** beep and five-photo capture. When a new person result arrives, the firmware requests the **5-second** beep. Look for `BUZZER REQUEST: SENSOR FUSION, 1000 ms` and `BUZZER REQUEST: ML PERSON, 5000 ms`, followed by `BUZZER OFF`. A no-person burst should have only the sensor beep. For another event, PIR must clear and valid distance must remain >100 cm for two seconds to rearm.

Keep the passive piezo wired with `+` on main GPIO23 and `-` on GND. Main GPIO19 still drives camera GPIO13; all grounds remain common. Power down before changing wiring. If you want to return to the old immediate sensor buzzer, reflash your saved old main sketch. This change does not turn the ML model into a reliable human-authorization or security decision; it reports a detected person shape and can miss people or trigger falsely, especially with dark or obstructed camera frames.

The Arduino ESP32 core provides the sketch's Wi-Fi and HTTP client functions. See the [official Wi-Fi API documentation](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/wifi.html).
