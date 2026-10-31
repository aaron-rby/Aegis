# Aegis ML

## Current gallery worker

The normal application runs through START_ALL.bat at the repository root. Its worker uses the checkpoint in backend/config.local.json, explicitly sets confidence 0.35 and inference size 960, and processes saved camera images through the SQLite queue. The model runs on the laptop, not the ESP32-CAM.

The standalone detector/service below defaults to models/person_ft.pt at confidence 0.50. These configurations are different. Supply the appropriate checkpoint locally; weights and datasets are not bundled. See the [project setup](../README.md), [results and limitations](../docs/results.md), and [camera fine-tuning workflow](../docs/camera-finetuning.md).

## Standalone service and diagnostics

Run these commands from ml/. SETUP.bat creates a separate venv for the standalone service; the gallery launchers use .venv.

```powershell
.\SETUP.bat
.\venv\Scripts\python.exe detector.py PATH_TO_IMAGE --output results_current/example.jpg
.\venv\Scripts\python.exe -m unittest test_service test_evaluation test_runtime -v
.\START_SERVER.bat
```

Model/threshold settings include MODEL_NAME, CONF_THRESHOLD, IMG_SIZE, MIN_BOX_AREA, MIN_BOX_HEIGHT, MAX_ASPECT, ENHANCE_DARK, ZOOM_OUT_PASS and USE_TTA. TTA is off by default. More stringent filters can miss small or partly visible people.

The optional standalone FastAPI service provides:

- GET /health: current model and threshold.
- POST /verify: image bytes or multipart file; returns person, confidence, count, boxes and inference time.
- POST /check: requests configured camera frames; faults remain errors. CAMERA_URL and related camera settings must be supplied.
- GET /status: last successful camera check, not a fresh measurement.

It binds to localhost by default and has no client authentication. Use only a trusted local network when explicitly binding to other interfaces. It is separate from the gallery backend and its token-protected camera upload/alarm routes.

webcam.py runs an explicitly requested local webcam demonstration. test_camera.py diagnoses camera HTTP/JPEG delivery. collect_camera.py saves labeled collection sessions. A detected person, photograph or screen image does not establish identity, authorization or liveness.

## Dataset preparation and training

- camera_labeler.py and camera_labeler.html: manually review original frames, draw person boxes or confirm empty scenes. Uncertain images are excluded.
- camera_training.py: export/check reviewed data, train a separate candidate and compare thresholds through the production detector. See the detailed [workflow](../docs/camera-finetuning.md).
- build_dataset.py, build_training_set.py and audit_dataset.py: prepare and audit local source datasets; review data licensing, labeling and split independence.
- build_gpu_archive_dataset.py, evaluate_gpu_candidate.py and scripts/train_aegis_gpu.py: optional local GPU preparation, training and comparison helpers. They do not automatically deploy a candidate.
- restore_datasets.py and restore_regression.py: recover missing local data from the expected archives without inventing replacements. Required archives and historical records must be supplied locally.
- validate_assets.py: inspect locally available image/checkpoint assets. Generated JSON reports stay local.

Keep identical images and capture sessions within one split. Session grouping alone cannot prove scene independence. Use reviewed originals rather than model-annotated output as training truth. Fix model and threshold before the final independent test.

## Evaluation

Historical person_ft.pt results are documented in [results.md](../docs/results.md). Training/test independence remains unverified. They must not be assigned to the current gallery worker or a candidate model.

evaluate.py and evaluate_camera.py create local evaluation reports. Positive-only datasets cannot establish false-positive rate. smoke_http.py tests the standalone HTTP service on a temporary localhost port. Service tests need a real local checkpoint and their declared image fixture; they do not demonstrate live hardware accuracy.

No-person output means no detection passed the configured checks, not proof of an empty area. Per-image confidence is not overall accuracy. Preserve capture/upload/inference errors separately from no-person results.
