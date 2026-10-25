# Phase 1 baseline — 20 October 2026

## Verified software and data

- Laptop Wi-Fi IPv4 during audit: `172.20.10.7`.
- Gallery: listening on port 5000 and responding to `/api/photos` and `/api/ml-results`.
- Active ML watcher: one launcher with its Python child, using the downloaded project copy of `ml/watch_gallery.py`; configured model `yolo11m.pt`, threshold 0.35.
- Source capture directory: `C:\Users\aaron\Documents\Intruder Detection System Project\local-photo-gallery\captures`.
- Source prediction directory: `C:\Users\aaron\Downloads\AI-Intrusion-Detection-main\AI-Intrusion-Detection-main\ml\gallery_predictions`.
- Before new physical testing: 340 JPEG captures, 45 JSON prediction records, 45 annotated JPEGs. Newest photo and prediction source both named `582ABD7BB88C-175cc9f9-7-5.jpg`.
- Historical burst `582ABD7BB88C-175cc9f9-6` has five photos and five `PERSON DETECTED` records; visual review confirms a person in a sampled frame. Historical burst `...-7` has five photos and five `NO PERSON DETECTED` records, but visual review shows a finger over the lens and parts of a face in several frames. Burst 7 is **not** a valid empty-scene accuracy check.
- At the time of this audit, no serial COM device or Arduino Serial Monitor process was connected. Live hardware and serial output could not be verified remotely.
- Receiver test `python -m unittest -v test_server.py` passed on 20 October 2026 at 18:56:50. It covered five JPEG uploads, duplicate-safe retry, photo/gallery reads, and rejection of bad token, malformed JPEG, invalid ID, and conflicting duplicate.

## Firmware identity — reported, not verified on flash

- User-provided main ESP32 source matches the local `main_buzzer.ino` design: PIR GPIO13, ultrasonic TRIG5 / ECHO18, camera trigger GPIO19, buzzer GPIO23, manual `T` trigger, and no camera status wire on GPIO16.
- The pasted main source has `BEEP_MS = 1000`; the local `main_buzzer.ino` has `BEEP_MS = 2000`. This difference means the local file is not an exact copy of the reported upload. The main board's flash contents were not read, so its exact firmware remains unverified.
- The user is unsure which ESP32-CAM sketch was last flashed. Do not assume a local camera sketch matches the board.
- The local `integrated/camera_uploader/camera_uploader.ino` points to `172.20.10.7:5000`; the older `esp32cam_upload/esp32cam_upload.ino` points to `172.17.98.4:5000`. Do not flash the older URL unchanged.

## Verified backup

- Directory: `C:\Users\aaron\Pictures\AI-Intrusion-Detection\backups\phase1-2026-10-20_18-54-05`.
- Files copied: 455; total bytes: 52,673,855.
- Includes 340 capture JPEGs, 45 prediction JSON records, 45 annotated JPEGs, models, active backend/ML source, launchers, and available firmware source.
- `manifest.json` records the original path, backup path, byte count, and SHA-256 for each file. `summary.json` records counts. All 455 source/destination hash pairs matched immediately after copying. Originals were left in place.

## Physical baseline still required

1. Reconnect the boards, verify stable camera 5V and current Wi-Fi IP, and capture the main Serial Monitor at 115200 baud.
2. Trigger one person burst with `T`. Record the serial messages, HTTP results if available, five unique filenames, five final ML results, and time from trigger to final prediction.
3. Let the controller rearm, fix the camera aimed at an empty room, leave the field of view entirely, and repeat. Do not cover the lens or hold the camera during the empty-scene burst.
4. Check that both bursts have exactly five photos and five matching prediction records. Review person boxes and any false positives. An incomplete burst is a camera/power/network issue to diagnose before calling Phase 1 complete.

Status: backup, software inventory, and live two-burst end-to-end smoke test complete. See the 19:12 empty-scene and 19:14 person-burst results below. Fixed full-body camera framing and exact flashed camera-sketch identity remain unverified.

## Live serial observation at 18:58

- User-provided main Serial Monitor output shows the sensor controller running and reporting `ARMED` at 115200 baud. COM6 was visible to Windows.
- Several `PIR:MOTION` readings occurred, but ultrasonic distance was about 259–263 cm, above the sketch's 80 cm detection threshold. Each line remained `AGREEMENT:0/3`; no `EVENT` or manual `T` trigger appears in the supplied excerpt.
- The gallery still held 340 photos and 45 predictions, with no new photo after 18:34:53. Therefore this excerpt does not test camera capture, upload, or ML processing. Manual `T` trigger requested next.
- A second user-provided excerpt showed `PIR:MOTION` with distance about 169–171 cm, still above the 80 cm trigger limit, and `AGREEMENT:0/3`. There was still no `EVENT` line and the gallery remained at 340 photos. No manual `T` submission has been confirmed.

## Manual trigger and network finding at 19:05

- User screenshot confirms `EVENT 1: MANUAL TEST - GPIO19 HIGH for 500 ms` followed by `GPIO19 returned LOW`. The main board sent the pulse. Its firmware states that camera capture/upload is not confirmed by this board.
- Gallery remained at 340 photos and 45 predictions after the pulse; no new JPEG arrived.
- The laptop Wi-Fi changed from the earlier phone-hotspot address `172.20.10.7` to `172.17.103.228` on network `T-VIT 3`. The gallery responds at the new laptop address, but the inspected camera sketches have upload URLs `172.20.10.7` and `172.17.98.4`. The currently flashed camera sketch remains unknown.
- This network/address mismatch is sufficient to explain failed uploads. Camera power and GPIO13 trigger reception remain unverified. Next: put laptop and camera on the same reachable hotspot, verify the laptop IP and camera upload URL, then repeat one manual `T` burst. Do not infer a wiring fault until the network mismatch is removed.

## Hotspot restored and live bursts at 19:08–19:09

- Laptop Wi-Fi IPv4 returned to `172.20.10.7`. The gallery returned HTTP 200 at `http://172.20.10.7:5000/`. The gallery batch process and ML watcher batch/Python processes were running.
- Captures rose from 340 to 350, and prediction JSON records from 45 to 55. Two distinct bursts, `582ABD7BB88C-f9f90835-1` and `582ABD7BB88C-f9f90835-2`, each contain five JPEGs and five corresponding ML records. The first ran from 19:08:24 to 19:08:31; the second from 19:08:52 to 19:09:16. This verifies successful camera trigger/upload and ML processing for both bursts. Exact trigger-to-final-result latency is unavailable without a timestamped serial `EVENT` line.
- Burst 1 predicted person in frames 1–2 and no person in frames 3–5. Burst 2 predicted person in frames 1, 2, and 5; no person in frames 3–4. Visual review shows the person moving into or out of the view, with the empty ceiling/room in other frames. These mixed outputs are consistent with changing camera view. They do not establish fixed-scene accuracy.
- User confirmed five new gallery photos following a manual `T`. The second full burst also appeared while testing; its triggering serial lines have not yet been supplied. Camera sketch identity remains unverified.
- Remaining acceptance: obtain one stable, well-lit person burst with the complete person in frame for all five exposures, then one genuinely empty-scene burst with the camera fixed. Record timestamped serial `EVENT`/rearm lines if possible and inspect all ten predictions.

## Empty-scene burst at 19:12

- User reported the empty-scene burst finished and supplied main Serial Monitor screenshot showing `REARMED: area clear continuously for 2 seconds.` with PIR clear and the ultrasonic target outside the detection zone. The screenshot did not include the `EVENT` line.
- Captures rose from 350 to 355 and prediction JSON records from 55 to 60. Burst `582ABD7BB88C-3cae8d1e-1` has all five numbered JPEGs and five corresponding ML records, captured between 19:12:11 and 19:12:30; the final prediction was processed at 19:12:31.
- All five ML records say no person (count 0). Visual review of frames 1, 3, and 5 shows the empty room/ceiling and no visible person. This passes the empty-scene upload/processing check and sampled visual accuracy check.
- A stable five-frame person burst with the person fully visible throughout is still needed to complete the planned positive accuracy check. The previous two bursts showed a person entering/leaving the frame and mixed ML results.

## Person burst at 19:14

- Captures rose from 355 to 360 and prediction JSON records from 60 to 65. Burst `582ABD7BB88C-3cae8d1e-2` has all five numbered JPEGs and matching ML records, captured between 19:14:08 and 19:14:17; the final prediction was processed at 19:14:18.
- All five ML records detected one person, with confidence 0.75, 0.59, 0.82, 0.85, and 0.84. Visual review of frames 1, 3, and 5 confirms a person, though the camera still points upward and the person is partly cropped. This passes the positive capture/upload/ML-detection check, but it does not establish performance for a full-body, fixed security-camera scene.
- Together with the empty-scene burst, the live end-to-end smoke test passed: ten new JPEGs, ten corresponding ML records, five positive classifications in the person burst, and five negative classifications in the empty-scene burst. The main board screenshot verified rearming. Camera flash identity and timestamped serial/upload HTTP log remain unverified; do not claim those details were measured.
