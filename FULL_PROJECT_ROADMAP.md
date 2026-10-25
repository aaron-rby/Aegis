# Full ESP32-CAM, backend, ML, and React roadmap

## Goal and current baseline

Flow: main ESP32 sensors -> ESP32-CAM trigger -> camera JPEG upload -> laptop Python backend -> durable photo storage -> laptop YOLO worker -> prediction record -> React gallery.

React displays photos; the ESP32-CAM captures them. The camera must continue posting to `http://<laptop Wi-Fi IPv4>:5000/upload`; `localhost` is only for software on the laptop.

The working setup on 20 October 2026 had a gallery on port 5000, 340 stored photos, 45 prediction records, and a matching prediction for the newest photo. The gallery and ML watcher were separate processes. The current server is in `C:\Users\aaron\Documents\Intruder Detection System Project\local-photo-gallery\server.py`; the active ML watcher is in `C:\Users\aaron\Downloads\AI-Intrusion-Detection-main\AI-Intrusion-Detection-main\ml\watch_gallery.py`. Keep the current launchers and data as the rollback path until the new setup passes the final test.

## Target folder layout

```text
AI-Intrusion-Detection/
  frontend/                  React + Vite source
    public/
    src/
      components/
      pages/
      services/api.js
      styles/
      App.jsx
      main.jsx
    package.json
    vite.config.js
    dist/                    generated build; do not edit by hand
  backend/
    server.py                HTTP upload, API, image serving, built React
    storage.py               atomic writes and indexed metadata
    worker.py                queued ML processing
    tests/
  ml/
    detector.py
    models/yolo11m.pt
    evaluation/
  firmware/
    main_controller/
    esp32_cam/
    camera_diagnostic/
  storage/                   runtime files; not in Git
    captures/
    predictions/
    app.sqlite3              photo, burst, and job states
  scripts/
    START_ALL.bat
    START_DEV.bat
    CHECK_SYSTEM.bat
  docs/
    wiring.md
    startup.md
    troubleshooting.md
  .gitignore
  README.md
```

## Phase 1 — Freeze and measure the working system

1. Record the currently flashed main and camera sketch names; do not assume a local `.ino` file matches flash contents.
2. Copy the current captures, prediction JSON/JPEG files, model weights, scripts, and configuration into a dated backup. Count files and compare checksums before changing paths. Do not move or delete originals yet.
3. Run one controlled five-photo person burst and one empty-scene burst. Record: serial log, upload HTTP codes, five filenames, five predictions, and elapsed time. Record the laptop Wi-Fi IPv4.
4. Gate: the existing gallery still receives photos and shows predictions. If any burst is incomplete, fix camera power, Wi-Fi, or trigger behavior before relying on frontend work as an integration test.

## Phase 2 — Consolidate the backend without breaking the camera

1. Copy the existing Python gallery server into `backend/`. Keep `POST /upload` and the existing camera token/header and ID format unchanged, so the flashed camera still works.
2. Replace absolute paths with one configuration file or environment variables for capture directory, prediction directory, model path, host, and port. Validate paths and model presence at startup; print clear startup errors.
3. Keep atomic JPEG writes and duplicate-safe retries. Store metadata in SQLite: photo ID, burst ID, photo number, receive time, file path, size, ML state, prediction, error. Derive burst/photo numbers from the current camera IDs only after validating that format; retain the full ID as the canonical key.
4. Expose paginated `GET /api/photos` with stable image URLs, `GET /api/photos/<id>`, `GET /api/bursts`, `GET /api/status`, `GET /photos/<name>`, and `GET /ml-images/<name>`. Preserve `GET /api/ml-results` during migration so the existing page keeps working.
5. `GET /api/status` must distinguish backend alive, last camera upload, worker heartbeat, queued jobs, processing errors, and configured model. A results folder existing is not proof that ML is running.
6. Gate: current firmware uploads a five-photo burst to the new backend, all files open in the browser, duplicate upload does not create another photo, and invalid token/JPEG requests are rejected. Keep the old backend available for rollback until this passes.

## Phase 3 — Make ML processing reliable

1. On every accepted JPEG, create a persistent `queued` ML job in SQLite. The worker changes it to `processing`, then `person_detected`, `no_person_detected`, or `error` and saves JSON plus an annotated JPEG atomically.
2. On worker restart, resume queued jobs and retry abandoned `processing` jobs. This fixes the current watcher behavior that ignores photos already present when it starts.
3. Run one worker instance only. Add a heartbeat and a startup check that the local model file loads. Keep inference off the HTTP upload thread so slow ML cannot block the camera upload.
4. Use the current YOLO11m model and 0.35 threshold as the initial baseline, then evaluate with labelled ESP32-CAM person and empty-scene images. Record missed people, false alarms, image orientation, lighting, and latency. Adjust the threshold based on that set; a lower threshold can increase false positives.
5. Gate: for a five-photo burst, five job records reach a final state, annotated images match original IDs, and a worker restart during a burst still completes all jobs. Display `No person detected` as a model result, not proof the scene is empty.

## Phase 4 — Build the React gallery

1. Create a React + Vite frontend in `frontend/`. During development, use the Vite dev server and proxy `/api`, `/photos`, and `/ml-images` to Python on port 5000. Keep API calls in `src/services/api.js`.
2. Build a responsive gallery with image cards, capture time, person/no-person/error/pending badges, confidence, annotated/original toggle, full-image view, person filter, burst grouping, and pagination. Show empty/loading/error states.
3. Show a burst as `received n/5`, `processing n/5`, or `complete 5/5`. Missing photos must remain visible as missing; the frontend must not imply that five were captured merely because one arrived.
4. Show a visible stale/offline status when the backend or ML heartbeat is missing. Refresh the lists on a short interval initially; add server-sent events later only if polling is insufficient.
5. Build the frontend into `frontend/dist/`. Extend Python to serve those built assets at `/` while keeping all camera and API routes. Daily operation then needs backend plus ML worker, without a Vite development terminal.
6. Gate: the React page loads at `http://localhost:5000/`, old and new photos display, each prediction links to the correct photo, it works on a phone-sized viewport, and a new live burst updates without manual refresh.

## Phase 5 — Startup, recovery, and documentation

1. Add `START_ALL.bat` that checks port 5000, configuration, model, and folders, then starts exactly one backend and one worker. It must show clear errors and avoid duplicate instances. Keep a separate `START_DEV.bat` for the Vite developer server.
2. Add `CHECK_SYSTEM.bat` to report gallery HTTP status, laptop Wi-Fi IPv4, worker heartbeat, latest photo, latest prediction, and counts of incomplete bursts/errors. The check must not trigger the camera or alter data.
3. Write the exact wiring, power, COM port, firmware identity, boot, and reset instructions. Camera 5V and GND must be tested under load; software cannot measure the camera's 5V pin without extra hardware.
4. Keep `storage/`, `frontend/node_modules/`, Python environments, logs, and downloaded/build outputs out of Git; back up captures and prediction metadata separately.
5. Gate: after a laptop restart, the documented launcher starts backend and worker, a new burst arrives, and the React page shows five final results. Then retire the old launchers and paths.

## Final acceptance test

1. Confirm the laptop and camera are on a reachable Wi-Fi network and the camera's configured PC IP is current.
2. From powered-off boards, start backend and worker. Confirm actual worker heartbeat, not just an existing results folder.
3. Trigger one person burst. Verify five distinct uploads, five stored JPEGs, five final ML jobs, and five correct React cards; inspect boxes on clear person images.
4. Trigger one empty-scene burst after rearm. Verify five uploads and review false positives.
5. Stop and restart the ML worker during a burst. Verify queued jobs finish after restart.
6. Restart the backend, refresh the React page, and verify all old images and predictions remain available.
7. Disconnect camera Wi-Fi or power briefly. Verify the website reports incomplete/offline status instead of showing success; restore the connection and retest.

No software roadmap can guarantee zero hardware failures or perfect detection. These gates make failures visible, keep the working system recoverable, and define exactly what 'working end to end' means.
