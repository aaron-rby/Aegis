# Aegis camera fine-tuning workflow

The running model and original captures are unchanged. Confidence scores are not artificially raised. The goal is fewer missed person events at an acceptable false-alarm rate. No CUDA GPU was detected during setup.

## Label originals
Run START_LABELING.bat, then open http://127.0.0.1:5010. Draw boxes around EVERY identifiable person and select Save person boxes. Confirm empty scene only after checking no person is visible. Exclude images too uncertain to label. Boxes and review status are saved locally in ml/camera_labels/annotations.json, with a hash of the original. No model-generated labels are treated as truth. Use originals, never annotated JPEGs.

The separate image_quality_review.csv ranks captures by a rough blur score and includes brightness. Scores vary by scene and resolution; they must not automatically determine whether a person exists. No captures were deleted.

Start with a varied set, ideally hundreds of frames across different people, lighting, distances and sessions. Avoid many near-duplicates. Use independent recording sessions/scenes for evaluation; session tokens alone cannot prove that two recordings show different scenes.

## Export reviewed labels
From project-root PowerShell:

    .\ml\.venv\Scripts\python.exe ml\camera_labeler.py --export ml\camera_dataset_v1
    .\ml\.venv\Scripts\python.exe ml\camera_training.py check --data ml\camera_dataset_v1\data.yaml

Export uses only manually saved person/empty labels. Uncertain/unreviewed frames are excluded. Entire camera sessions and byte-identical images stay within one split. Allocation aims for 70/15/15; exact proportions vary with session sizes. Every split must contain positive and empty examples. Original images and existing exports are never overwritten. Record and reserve new independent scenes if the resulting split is not representative.

## Train separately
Pause the production ML worker before starting CPU/GPU training. This computer has no detected CUDA GPU. To explicitly accept slow CPU training:

    .\ml\.venv\Scripts\python.exe ml\camera_training.py train --device cpu --data ml\camera_dataset_v1\data.yaml --epochs 50 --batch 2 --name person_v1

For a CUDA-enabled machine, use --device 0. Copy only the reviewed dataset and training code to that machine; do not publish credentials or private captures. A portable dataset requires updating the path in data.yaml. Training produces ml/runs_camera/person_v1/weights/best.pt, preserving ml/yolo11m.pt. Real camera blur is retained in data; this first run does not add unverified synthetic blur transforms.

## Validation threshold sweep

    .\ml\.venv\Scripts\python.exe ml\camera_training.py evaluate --candidate ml\runs_camera\person_v1\weights\best.pt --split val

This compares the current model and candidate using the production detector, filters and imgsz=960 at confidence thresholds .25/.35/.45/.55. Review person-event recall AND false alarms. Reports are saved under ml/camera_labels. Choose a threshold from validation results only.

## Final test
With model and threshold fixed (example .35):

    .\ml\.venv\Scripts\python.exe ml\camera_training.py evaluate --candidate ml\runs_camera\person_v1\weights\best.pt --split test --threshold .35

Do not tune against test results repeatedly. Add a fresh held-out session if you use the test set to guide subsequent changes. Treat a 90% event-recall goal as an observed metric with sample-size limits, not a confidence-score guarantee. Verify that the candidate improves difficult examples without excessive empty-event alarms and measure inference latency separately.

## Deployment
Nothing automatically deploys a candidate. Keep the current model and compare reports first. Update only backend/config.local.json model_path to the chosen checkpoint after verification, and restart the ML worker. The production threshold is currently hardcoded .35 in backend/worker.py; an alternative validated threshold must be implemented consistently rather than merely changing a displayed score. Existing saved events are not automatically reprocessed.
