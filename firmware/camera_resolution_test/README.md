# OV3660 VGA/SVGA comparison

This separate sketch is based on the local integrated camera uploader, NOT a verified readback of the flashed camera. It assumes the AI-Thinker ESP32-CAM pin map. Confirm the board and active sketch before uploading; do not use this pin map blindly on an ESP32-S3 board. Credentials were copied from that local source; verify them privately and do not share this sketch publicly.

The camera sensor PID is logged on initialization (OV3660 is 0x3660). PSRAM is required by this test. JPEG quality stays at 12 and there is one framebuffer, so the main comparison changes only resolution. Nothing has been uploaded automatically.

1. Keep the currently working camera sketch as your rollback copy. Start the backend and ML worker with START_ALL.bat.
2. Confirm Wi-Fi, camera upload token and SERVER_URL match the working camera. Select the correct camera board and port in Arduino IDE. Leave the main controller firmware unchanged.
3. Set TEST_SVGA=false and upload to the camera for the 640x480 baseline. Open camera Serial Monitor at 115200. Record its sensor PID, PSRAM, actual dimensions, bytes, capture/upload times and burst completion times.
4. Capture at least 10 person-present and 10 empty-scene bursts across bright and dim lighting. Record each burst ID, scene label, five-frame success count and ML event result. Keep the position, subject distance, lighting and JPEG quality consistent between modes. A missed event means all analyzed frames fail to detect the visibly present person. Count incomplete bursts separately; they are not confirmed negative events.
5. Set TEST_SVGA=true and repeat at 800x600 using the same scenes. Check the actual received JPEG dimensions, not just the configured value.
6. Compare missed-person events and false alarms, median upload/burst time and number of complete 5/5 bursts. Keep SVGA only if the measured benefit is worth its latency and reliability. Restore the saved camera sketch if it performs worse.

Existing 640x480 photos cannot be used to manufacture a genuine 800x600 comparison. Upscaling does not recover missing camera detail. Sensor identity, PSRAM and physical A/B results remain unverified until the board is run.
