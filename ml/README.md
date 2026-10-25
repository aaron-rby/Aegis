# ML: person verification

Run commands from this folder. Use `venv`, freshly recreated on this PC. The incomplete copied environment is preserved as `venv_legacy`; the previous working `.venv` remains available but launchers now use `venv`.

## Start

```powershell
.\SETUP.bat
.\venv\Scripts\python.exe detector.py data\person\coco_000000011699.jpg --output results_current\example.jpg
.\venv\Scripts\python.exe evaluate.py
.\venv\Scripts\python.exe -m unittest test_service test_evaluation test_runtime -v
.\START_SERVER.bat
```

The default model is the supplied `models/person_ft.pt` checkpoint (historically fine-tuned from YOLO11m), confidence 0.50, image size 960. `MODEL_NAME`, `CONF_THRESHOLD`, `IMG_SIZE`, `MIN_BOX_AREA` (fraction of image area), `MIN_BOX_HEIGHT`, `MAX_ASPECT`, `ENHANCE_DARK`, `ZOOM_OUT_PASS` and `USE_TTA=1` configure inference. Original detector source was recovered from another local project copy in Downloads and preserved under `original_source`. Path, input and concurrency fixes are applied in the active detector; rerun evaluation before attributing historical metrics to this machine.

## Camera integration

```powershell
$env:CAMERA_URL='http://YOUR_CAMERA_IP/capture'
$env:CAMERA_TOKEN='YOUR_CAMERA_TOKEN'
$env:SERVER_HOST='0.0.0.0'
.\START_SERVER.bat
```

Default bind is localhost. Bind to all interfaces only on your trusted local network when connecting boards. The service has no client authentication. Do not expose it publicly.

- `GET /health`: model and threshold.
- `POST /verify`: raw image bytes or multipart field `file`; returns `person`, `confidence`, `count`, `boxes`, `ms`. Limit 10 MiB; annotations saved under `captures` with unique names.
- `POST /check` (GET retained for compatibility): fetches `CHECK_FRAMES` camera images (default 2), and confirms if any image contains a qualifying person. Concurrent checks return 409. Missing configuration returns 503; camera faults return 502. This policy differs from webcam confirmation.
- `GET /status`: last successful camera check, not a fresh measurement. A controller must use its own request result, handle errors/timeouts, and never treat an old status as a new verdict.
- Camera settings: `CAMERA_METHOD` (POST by default), `CAMERA_TIMEOUT` (20 seconds), `CAMERA_RETRIES` (3), optional `CAMERA_USER`/`CAMERA_PASS` for Basic authentication.
- `webcam.py`: local camera, 3 positive detections among last 5 frames; run only when you want to activate your webcam.
- `collect_camera.py person 30`, `collect_camera.py no_person 30`: collects real camera images. `screen` is a special policy dataset, excluded from ordinary evaluation. A photograph of a person on a screen can legitimately be detected by a normal object detector; this model does not establish liveness.

No matching ESP32 firmware is supplied in this folder. Actual sensor-to-camera-to-verdict-to-buzzer behavior must be verified with the boards and matching firmware. The saved seven captures alone do not prove complete hardware integration.

## Datasets and training

`restore_datasets.py` recovers missing public source files from local archives without overwriting existing files. `restore_regression.py` restores historical regression images where archives contain them. Nine original regression photos are absent from the available dataset archives; this is not repaired by inventing replacements.

`build_training_set.py` creates `train_data` using public camouflage/soldier data plus COCO, retaining original source test splits in `camo_test`. It excludes the `hidden` dataset. The historical builder did include that dataset, so this exclusion does not retroactively change the provenance of the supplied checkpoint. It refuses to replace a populated training output. `audit_dataset.py` checks pairing and exact byte duplicates; it cannot prove that visually similar frames are independent. Source licensing and attribution are retained under `raw`.

The complete, audited dataset is now in `train_data`, matching your requested structure. The original incomplete dataset is preserved as `train_data_legacy`. New training uses `train_data/data.yaml`:

```powershell
.\venv\Scripts\python.exe train.py --device cpu --epochs 30 --batch 4
```

Training is optional and is not run by setup or server startup. New runs use `runs_repaired`, preserving the historical checkpoint. Only person boxes are labeled while the dataset retains the 80-class mapping; evaluate this as a person detector, not as a general 80-class benchmark. COCO val images used here for training must not subsequently be reported as an independent COCO validation benchmark.

## Results

Historical outputs are preserved in `results`, `results_base_main`, `results_base_camo`, and `runs`. They came from another machine and the original detector implementation. `results/report.txt` records 227 images, precision 98.6%, recall 95.1% at threshold 0.50. These are image-level historical results, not current system accuracy. The camouflage baseline report contains only positive images, so it cannot establish a false-alarm rate on negative scenes.

Fresh evaluation writes `results_current` and measures this copy's actual available data. Select thresholds on validation data, then evaluate once on an independent test set. Existing historical checkpoint training provenance and near-duplicate leakage require separate review. Person detection does not determine authorization.

## Restored folder compatibility

- `test.py` runs a static image with the configured detector and saves an annotation; `--show` explicitly opens a window. `test.jpg` and `test_cam.jpg` were recovered from the other local project copy, not captured during this repair.
- `build_dataset.py` prepares a new COCO evaluation set in `data_prepared`, excludes existing training image content, and refuses to overwrite populated output. `--include-exdark` exports uncertain examples under `review` for manual labeling. Run dataset preparation before rebuilding training data so the held-out images can be excluded from training.
- `camo_eval/person` now contains all 237 source-test images. `camo_eval/no_person` and `data/screen_negatives` are intentionally empty until suitable labeled images are supplied. Positive-only evaluation reports recall; false-positive rate and precision are unavailable without negative examples.
- `weights/README.md` explains existing checkpoint locations; no fabricated model files are created.
- `python train.py --check` validates model/dataset inputs without training. `train.log`/`train.err` record that check, not a new training run.
- `python smoke_http.py` tests the actual server process on a temporary localhost port. `rs.log`/`rs.err` contain its process output, and `srv.log`/`srv.err` contain real server logging. It stops only its own process and never contacts the camera.
- Run `python audit_structure.py` for the presence check against your supplied tree. The result is saved as `structure_audit.json`.

Latest file review: CURRENT_REVIEW.md. Webcam errors now release the camera; Q, Escape and closing the video window stop the demo. The ESP32-CAM diagnostic validates JPEG markers/decoding and returns a failure exit code for HTTP errors or invalid images.
