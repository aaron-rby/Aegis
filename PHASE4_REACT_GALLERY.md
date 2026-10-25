# Phase 4 React gallery — 20 October 2026

The React/Vite source is in `frontend/`. The production build is `frontend/dist/`, served by `backend/server.py` at `http://localhost:5000/`. The ESP32-CAM still sends `POST /upload` to the same backend on port 5000; the upload and image routes were preserved. Daily operation needs the backend and one ML worker, not a Vite terminal.

## Fresh start

1. Connect the laptop and ESP32-CAM to the same Wi-Fi. The currently configured camera target is the laptop's `172.20.10.7` address on Aaron's iPhone hotspot; confirm the laptop still has that address before triggering the camera.
2. Double-click `START_REACT_GALLERY.bat` and keep its window open. Do **not** also start the old `START_GALLERY.bat`, which launches the legacy server on the same port.
3. Double-click `START_CAMERA_ML.bat` and keep its window open. It starts the Phase 3 persistent ML worker. Only one instance can run.
4. Open `http://localhost:5000/`. It displays old and new photos, prediction badges, the latest backend/ML status, and burst groups. New results refresh every three seconds.
5. Wait for `REARMED` on the main ESP32, then send `T` once. A complete camera burst should show five received photos and five final ML states. If fewer than five arrive, the burst view shows their actual frame numbers and missing slots.

If a backend window is already serving port 5000, do not start another. Check `http://localhost:5000/api/status` and `http://localhost:5000/` first. `START_REACT_GALLERY.bat` is the new launcher; the old gallery launcher remains available for rollback. The ML window can keep running while the frontend is rebuilt or the backend is restarted.

## Development

From `frontend/`, run `npm install`, then `npm run dev`. Vite proxies `/api`, `/photos`, and `/ml-images` to the Python backend on port 5000. Open the Vite address shown in the terminal for development. Run `npm run build` to update `frontend/dist/` before using the production page at port 5000. Keep backend and ML running during development. The built files are generated and ignored by Git; rebuild after cloning or copying this project to another PC.

## Checks performed

- `npm run build` succeeds with React 19 and Vite 8.
- The project ML environment passes all four backend/worker integration tests, including API filter validation and an incomplete burst with missing frame 3.
- The production page, JavaScript/CSS assets, photo and annotated-image routes, person filter, original/annotated toggle, full-image view, and pagination work in the browser.
- The responsive page and mobile navigation were checked at a 390-pixel viewport.
- Live uploads updated the open React page without a manual refresh. Burst `582ABD7BB88C-5f2cc18f-24` reached five received photos, five final ML results, zero errors, and five matching annotated image IDs. Burst `...-22` had only frames 3–5; the interface marks frames 1 and 2 missing.

“No person detected” remains a model result, not proof that the scene is empty. The camera firmware identity is still unverified, and false detections or missed people require a larger labelled ESP32-CAM evaluation set.
