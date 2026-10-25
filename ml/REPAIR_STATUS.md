# Folder completion and verification — 20 October 2026

All 56 file/directory paths listed in your supplied tree are present. See `structure_audit.json` for the complete path-by-path check.

## What was restored or corrected

- Restored `build_dataset.py`, `test.py`, `.gitignore`, `test.jpg` and `test_cam.jpg`. Original source/sample files were found in another local Downloads copy. Active scripts now use paths relative to their own location, not the shell's current directory.
- Created `camo_eval/no_person`, `data/screen_negatives`, and `weights`. `weights/README.md` points to existing checkpoints; no fake weights are supplied.
- Recreated the canonical `venv` on this computer, installed the pinned dependencies, and changed SETUP.bat and START_SERVER.bat to use it. The old incomplete environment is preserved in `venv_legacy`; the prior working `.venv` remains available.
- Promoted the complete rebuilt dataset to canonical `train_data`, repaired its YAML path, and updated builder/training/audit scripts. The incomplete original is preserved in `train_data_legacy`.
- Completed `camo_eval/person` with the 237 held-out source-test images.
- Generated real `rs.log`, `rs.err`, `srv.log`, `srv.err`, `train.log` and `train.err`. `train.log` explicitly records a CHECK ONLY validation, not a new training run. Historical train_all files remain intact.
- Improved evaluation for positive-only datasets: recall is available, while precision/F1/false-positive rate are marked unavailable without negative scenes.
- Added exact-content exclusions for both original regression data and `data_prepared` when building training data.

## Verification completed

| Check | Result |
|---|---|
| Requested paths | 56/56 present |
| Canonical venv dependencies | pip check passed |
| Service, evaluation and camera failure regression tests | 16 passed; review-tests.log |
| Real HTTP server startup and request | Passed; http-smoke.json |
| Static-image demo | Passed; static-test.log and results_current/test_annotated.jpg |
| Evaluation dataset builder | Prepared 120 COCO examples; data_prepared/manifest.json |
| Training inputs | 6,037 train, 1,099 validation; train.log |
| Held-out source-test set | 237 images |
| Dataset labels | No missing or invalid labels |
| Exact overlap | None across dataset splits or with regression/prepared evaluation data |
| Image decoding | 7,837 images checked, no failures; asset_validation.json |
| Checkpoint archive integrity | All four checkpoints passed |

Earlier fresh image evaluation remains in results_current/report.json: on 218 recovered images, threshold 0.50 gave 129 TP, 2 FP, 7 FN and 80 TN (98.47% precision, 94.85% recall). This does not prove independence from the historical model's training data or end-to-end deployment accuracy. No fresh full training was run.

## Start using it

Double-click `START_SERVER.bat`, or run:

```powershell
cd C:\Users\aaron\Pictures\AI-Intrusion-Detection\ml
.\venv\Scripts\python.exe test.py
.\START_SERVER.bat
```

The service binds localhost by default. For the boards, configure CAMERA_URL and CAMERA_TOKEN and use SERVER_HOST=0.0.0.0 on a trusted LAN. README.md describes the endpoints, configuration, optional training, and hardware setup requirements.

## Limits that require actual data or hardware

- `camo_eval/no_person` and `data/screen_negatives` are intentionally empty until suitable real labeled scenes are supplied.
- Nine historical regression images are not present in the available dataset archives. The restored test.jpg and test_cam.jpg are genuine files from the other local copy, not replacements falsely labeled as those nine originals.
- Physical camera communication, flashed board firmware, sensors, buzzer driver/control, and end-to-end timing need the actual boards and their connection details. No ESP32 firmware is included in the supplied folder tree. The local HTTP test used saved photos and did not activate a camera.
- Exact duplicate checks cannot rule out near-duplicate scene leakage. The historical model's builder included hidden; new dataset builds exclude it, without changing the provenance of the existing checkpoint.
- Person detection does not establish liveness, identity, or authorization. The service is a local prototype without public-facing authentication.
