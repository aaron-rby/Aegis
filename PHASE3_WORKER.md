# Phase 3 ML worker — 20 October 2026

The live backend and camera upload contract are unchanged. A newly accepted JPEG now creates a `queued` row in SQLite's `ml_jobs` table in the same transaction as its photo index row. The worker in `backend/worker.py` claims one job at a time, marks it `processing`, runs the local YOLO11m model at 0.35 confidence, atomically writes an annotated JPEG and JSON record, then marks the job `person_detected`, `no_person_detected`, or `error`. Inference runs in a separate process from HTTP uploads. A duplicate JPEG retry does not create another photo or job.

The worker takes an OS-held lock on `storage/app.worker.lock`; a second worker exits with a clear error. It loads and warms up the configured local model before beginning work. Its heartbeat updates SQLite every five seconds, and `/api/status` reports it as live only while the heartbeat is fresh. On restart it returns abandoned `processing` jobs to `queued`, retaining attempt counts. An error record is saved as JSON; an annotated image is only available when image processing succeeds. The gallery and `/ml/` both state that “No person detected” is a model result, not proof of absence.

The project-root `START_CAMERA_ML.bat` now starts the Phase 3 worker from `ml/.venv`. The old downloaded `watch_gallery.py` was stopped and must not be started alongside it. For a fresh start, open `scripts/START_BACKEND_PHASE2.bat` first, then project-root `START_CAMERA_ML.bat`. Keep both running. The camera still uploads to `http://172.20.10.7:5000/upload` when the laptop is on the `Aaron’s iPhone` hotspot. `localhost` works only on the laptop. The old gallery server and watcher files remain in their original locations for rollback; a verified 370-capture/75-result backup plus a SQLite snapshot is at `backups/phase1-2026-10-20_19-55-02`.

## Verification

- Isolated tests cover five persistent jobs, a claimed job recovered after a simulated crash, final JSON/JPEG artifacts, heartbeat start/clear, duplicate worker rejection, and the Phase 2 receiver/API behavior.
- A real-model probe on four copied ESP32-CAM frames loaded YOLO11m successfully and produced four completed jobs with matching annotated JPEG/JSON names.
- A separate port-5002 backend accepted one test image and completed it; the worker was stopped; four more uploads returned HTTP 201 and remained queued; after restart the burst reached 5/5 final jobs and all five annotated image URLs returned HTTP 200. No test uploads were added to the live gallery.
- A deliberately abandoned `processing` job in the isolated store was recovered at startup and completed on attempt 2.
- On the live camera and port-5000 backend, burst `582ABD7BB88C-5f2cc18f-13` uploaded five photos while ML was paused. Status showed five queued jobs and zero finished. After worker restart, all five reached a final state, with zero queued/errors, and all five annotated image URLs returned HTTP 200. This is the live restart-during-burst acceptance check.
- The camera also produced other live bursts through the new worker. The backend visibly records incomplete camera bursts rather than claiming five uploads when fewer arrived (for example burst `...-11` had 4/5 received). A missing JPEG is a camera/upload issue, not a completed ML job.

## Small labelled camera evaluation

`ml/evaluation/esp32_camera_labels.json` records ten manually reviewed frames from one empty-scene burst and one person burst. Running `ml/evaluate_camera.py` with the configured YOLO11m at 0.35 produced five true positives, five true negatives, zero false positives, and zero missed people, with mean model inference time 523 ms. The per-frame results and timing are in `ml/evaluation/esp32_camera_report.json`. The camera points upward, people are partly cropped, and all frames are from one lit indoor scene. This is a smoke-test result, not an estimate of field accuracy. The threshold remains 0.35 pending a larger labelled set with different distances, orientations, and low light.

Current practical limit: backend/worker start is still two windows; Phase 5 will combine startup and checks. The camera firmware identity remains unverified. Keep the laptop on the camera's reachable Wi-Fi network; while it was on `T-VIT` at `172.17.103.228`, manual triggers did not upload to the camera's saved `172.20.10.7` address.
