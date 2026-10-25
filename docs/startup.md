# Startup and recovery

## Before pressing Start

- Power/connect the laptop and ensure it is on the camera's hotspot/Wi-Fi. `CHECK_SYSTEM.bat` reports the current Wi-Fi IPv4. The camera firmware last targeted `172.20.10.7:5000`; if the laptop has a different address, the camera cannot reach it until its upload target is changed.
- Keep `backend/config.local.json` on this PC. It contains the camera upload token and local paths; never publish it. Its configured capture and prediction folders currently point to the established external folders. The launcher checks that they exist and does not move them.
- `ml/.venv/Scripts/python.exe`, `ml/yolo11m.pt`, and `frontend/dist/index.html` must exist. To recreate the Python environment, follow `ml/README.md`; to rebuild React, run `npm install` and `npm run build` inside `frontend/`.

## Normal start

1. Double-click the project-root `START_ALL.bat` (or run `& "C:\Users\aaron\Pictures\AI-Intrusion-Detection\START_ALL.bat"` in PowerShell). Do not paste the batch file's individual lines into PowerShell.
2. Watch for `Backend ready on port 5000` and `ML worker ready`. The launcher starts separate backend and ML console windows. Keep those two windows open. Re-running `START_ALL.bat` should say the existing services are in use; it should not launch duplicates.
3. Run `CHECK_SYSTEM.bat`. Gallery HTTP should be 200 and the heartbeat should be online. Then open <http://localhost:5000/>. The backend receives uploads and serves React; the worker handles inference.
4. Power the ESP32-CAM and main ESP32, open the main board's Serial Monitor at 115200, and wait for `MAIN ESP32 READY`/`ARMED`. The main board was previously seen as COM6, but the COM number can change. Only send `T` once after the camera finishes booting and the main board is armed.
5. Check the gallery count and the Bursts view. A complete burst requires five accepted JPEGs and five final ML states. If fewer arrive, inspect camera power, Wi-Fi, and upload diagnostics. A main-board `EVENT` line proves only that GPIO19 pulsed, not that the camera captured or uploaded.

To stop intentionally, close the ML and backend console windows (or press Ctrl+C in each). Do not close the laptop or let it sleep while the camera needs to upload. `START_ALL.bat` is a manual launcher; Windows will **not** run it automatically after reboot unless you set up a separate startup task.

## Development and recovery

Run `START_ALL.bat` for the backend and worker, then `START_DEV.bat` for the Vite dev server. Vite proxies `/api`, `/photos`, and `/ml-images` to port 5000. The dev URL is printed in its own window. After changes, run `npm run build` in `frontend/` for the production page.

If the launcher says port 5000 belongs to another service, do not start the old `START_GALLERY.bat` or a second backend. Find the existing server first. If worker heartbeat is stale while its lock is held, inspect the worker window; a busy or hung worker must be resolved before restarting. The worker automatically requeues abandoned `processing` jobs after a crash and resumes `queued` jobs on restart.

Run `BACKUP_DATA.bat` after important tests and before moving paths. It makes separate `captures/` and `predictions/` folders plus a SQLite snapshot under `backups/phase5-...`. It does not delete originals. A backup made during an active burst may capture different points in time across the folders; repeat after the burst and worker finish. `storage/` and `backups/` are ignored by Git. Back up `backend/config.local.json` and the model weights separately in secure local storage if rebuilding another PC; the config contains a secret.

Retain the old launchers and absolute data paths until the after-reboot, live five-frame acceptance gate is recorded in `PHASE5_STARTUP.md`.
