# ESP32-CAM intrusion monitor

The main ESP32 reads the PIR and ultrasonic sensors and pulses the ESP32-CAM trigger. The camera uploads JPEGs to the laptop backend. A separate YOLO worker analyzes saved photos; the React gallery displays both original and annotated images.

## Daily start

1. Connect the laptop to the same Wi-Fi/hotspot used by the ESP32-CAM. The camera's last known target was `172.20.10.7:5000`; verify the laptop's current Wi-Fi IPv4 with `CHECK_SYSTEM.bat` before triggering a burst. If the address changed, the camera firmware configuration must be updated.
2. Double-click `START_ALL.bat`. It checks the configuration, capture/prediction folders, local YOLO11m file, React build, and port 5000. It opens one backend window and one ML worker window; if either is already healthy, it reuses it. Keep the backend and worker windows open.
3. Double-click `CHECK_SYSTEM.bat`. Confirm gallery HTTP 200 and a fresh ML heartbeat. Open <http://localhost:5000/> on the laptop.
4. Power the ESP32-CAM from a stable regulated 5 V source with common ground to the main ESP32. Start/confirm the main board on the correct COM port at 115200 baud. Wait for `MAIN ESP32 READY` and `REARMED`/`ARMED`; send `T` once for a manual five-photo burst, or let both sensors trigger it.
5. Wait for five distinct photo cards and five final ML states. In Bursts, check `Complete 5/5`; review original images and annotations. Missing frames remain marked missing.

`START_DEV.bat` runs Vite only for frontend development. For normal use, the built React page is served by the backend on port 5000; no Vite window is needed. After changing frontend source, run `npm run build` in `frontend/` to update the ignored `frontend/dist/` output.

`BACKUP_DATA.bat` copies camera JPEGs, prediction JSON/JPEG files, and a consistent SQLite snapshot into a dated, ignored folder under `backups/`. A folder is complete only when it contains `manifest.json`. Keep a second copy on another drive before moving to another PC.

See [startup](docs/startup.md), [wiring](docs/wiring.md), and [troubleshooting](docs/troubleshooting.md) for exact checks and recovery. The [Phase 5 record](PHASE5_STARTUP.md) tracks verification and the remaining physical restart gate.

To make the **main ESP32 buzzer sound after a new ML person prediction**, use the separate [ML buzzer setup](docs/ml-buzzer.md). This requires uploading the new main-board sketch; the ESP32-CAM firmware stays unchanged.
