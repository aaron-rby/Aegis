# Phase 2 backend cutover — 20 October 2026

The replacement receiver is `backend/server.py`. It uses `backend/config.local.json` for the existing capture directory, existing ML result directory, local YOLO11m model, SQLite path, LAN binding, port, and unchanged camera upload token. `backend/config.example.json` is the portable template. The local config and SQLite database are ignored by Git.

The current camera request remains `POST /upload?id=<camera-id>` with `X-Camera-Token` and `Content-Type: image/jpeg`. The camera firmware and laptop IP were not changed. The server validates the token, ID, size, JPEG markers, and JPEG structure; writes a new image via a temporary file and atomic rename; and returns 200 for an identical retry or 409 for conflicting bytes. Full IDs remain canonical. Burst/photo numbers are derived only for IDs matching the observed camera format.

The new server imports existing captures and existing watcher prediction JSON into `storage/app.sqlite3`, without moving or deleting source files. Existing photos without predictions are `legacy_unprocessed`; new accepted uploads are `queued` until a watcher result is imported. The current ML watcher still runs separately and processes new files. This migration does not add the Phase 3 persistent worker yet.

Routes: `GET /api/photos?page=1&per_page=30` is paginated (maximum 100); `GET /api/photos/<id>` returns one indexed photo; `GET /api/bursts` groups the recognized camera IDs; `GET /api/status` reports backend, last upload to this backend, worker heartbeat, job counts, and model; `/photos/<name>` and `/ml-images/<name>` serve images; `/api/ml-results` and `/ml/` preserve the prior result views. The embedded gallery on `/` uses the paginated API.

The old watcher has no heartbeat. `/api/status` therefore reports `worker.running: false` even when its process is visible and its predictions are arriving. A heartbeat and restart recovery belong to Phase 3; the server does not infer worker health from the result folder.

For a fresh start, run `scripts/START_BACKEND_PHASE2.bat` in one terminal and the project-root `START_CAMERA_ML.bat` in another. The latter was updated in Phase 3 to start the persistent worker; do not start the downloaded legacy watcher alongside it. Only one server may own port 5000. The old gallery's `START_GALLERY.bat` remains the rollback launcher; stop the Phase 2 backend before starting it. Do not run both gallery launchers at once. The source data folders are shared, so rollback does not move photos or results.

Phase 2 verification: isolated backend tests cover five uploads, duplicate retry, conflicting duplicate, invalid token/ID/JPEG, pagination, bursts, media, result import, and status. The new server was compared on port 5001, then cut over to port 5000. Live camera burst `582ABD7BB88C-3cae8d1e-4` delivered five JPEGs and five ML results; totals rose from 365/70 to 370/75. Exact camera-side HTTP codes are not available because the camera firmware/serial log was not captured, but the backend observed and indexed all five uploads. A live duplicate retry returned 200, bad token returned 401, malformed JPEG returned 400, and the photo count stayed 370.

Phase 3 subsequently added the persistent worker, startup model load check, heartbeat, and restart recovery. See `PHASE3_WORKER.md` for the live verification and current launchers.
