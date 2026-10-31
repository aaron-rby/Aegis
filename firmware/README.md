# Aegis firmware source

| Folder | Role |
|---|---|
| main_ml_alarm/mlids | Main ESP32: dual sensing, GPIO19 camera pulse, independent clearance rearming, Wi-Fi result polling and 1 s / 5 s buzzer control. |
| camera_resolution_test | Report-aligned camera source reference: classic AI-Thinker-compatible pin map, SVGA 800×600, quality 12, five-photo upload. Confirm actual board/sensor and flashed sketch. |
| esp32cam_ov3660_hq | Separate HQ candidate, quality 10 and additional upload diagnostics. Its README records compile verification, not replacement of the demonstrated uploader. |

Copy the adjacent config.example.h to config.h and fill local Wi-Fi details, laptop LAN IP and matching tokens. The camera uses camera_token; the main board uses the separate alarm_token from backend/config.local.json. Both configuration files are ignored by Git.

The main and report-aligned camera sources were sanitized by moving credential declarations into config.h; control logic was preserved. The main sketch needs ArduinoJson and the Espressif Arduino core. Follow each camera folder's pin map and programming instructions. Source files are not a readback of the firmware currently on the boards; do not flash an unverified alternative merely to match a filename.

See [wiring](../docs/wiring.md) and [ML buzzer setup](../docs/ml-buzzer.md). A clean checkout requires local configuration before firmware compilation. Neither ESP32 runs the laptop YOLO model.
