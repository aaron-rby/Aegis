# OV3660 higher-detail five-photo uploader

Compiled successfully on 25 October 2026 using the installed Espressif Arduino core **3.3.12**, target `esp32:esp32:esp32cam`: 1,034,953 bytes program storage and 60,280 bytes static RAM. Not flashed or physically tested. See `WIRING.png` or the editable `WIRING.svg` for both connection modes.

For a **classic ESP32-CAM with an AI-Thinker-compatible PCB pin map and OV3660 sensor**, matching the previous working pin configuration. Not an ESP32-S3 sketch. Sensor PID is checked after initialization; a different detected sensor is reported rather than silently assumed to be OV3660.

## Image settings

- PSRAM: SVGA **800Ã—600**, JPEG quality **12**, one framebuffer.
- No PSRAM: explicitly reported QVGA fallback. High-resolution operation requires working PSRAM.
- Automatic exposure, white balance and gain; six discarded initialization frames for settling.
- Discards the waiting frame before each captured photo. Checks both JPEG boundary markers.
- Flash off. Adequate scene lighting and focus are still necessary. More pixels do not fix darkness, blur, brownouts or bad connections.
- Edit `HQ_FRAME_SIZE` to `FRAMESIZE_XGA` for 1024Ã—768 only after verifying SVGA delivery. Do not start at the sensor's maximum resolution on an unstable supply.
- Vertical flip and horizontal mirror are explicit configuration choices; enable only as needed for mounting orientation.

## Delivery behavior

Five photos are requested for each accepted GPIO13 rising edge. Each image is held in RAM with the same ID for up to six delivery attempts. Advance to the next slot only after HTTP 200/201 plus the gallery's matching saved-filename acknowledgement. The gallery receiver already handles duplicate retries with identical content and ID.

If a slot cannot be confirmed, the burst stops and prints `BURST FAILED: N/5 saved`; it never reports `5/5` merely because five attempts were made. A new trigger starts a new burst, not a resume. No durable offline queue: resets/power loss discard unsent images. A server save followed by a lost acknowledgement may be reported as unconfirmed even though the PC has the file.

Per-photo budget is approximately 150 seconds (a blocking HTTP operation may finish after that check); up to three capture attempts and six uploads. Bursts can take much longer than the old controller's holdoff. Busy triggers are ignored when observed; pulses wholly inside blocking camera/HTTP calls can be missed. The no-feedback controller cannot know completion. Use deliberately matched completion-feedback firmware if the main controller must wait for all uploads. This sketch does not implement the separate `@CAM` integrated protocol or ML verdicts.

## Configure before upload

Open `esp32cam_ov3660_hq.ino` in Arduino IDE, then edit its `config.h` tab:

1. Set Wi-Fi name and password.
2. Set `SERVER_URL` to `http://CURRENT_LAPTOP_WIFI_IP:5000/upload`.
3. Set `UPLOAD_TOKEN` to the token used by the existing local gallery receiver. Do not confuse it with Sentinel's separate `X-Device-Token`.
4. Start the original port-5000 gallery receiver. This uploader does not directly upload to the port-8765 Sentinel API.

The template intentionally contains no real Wi-Fi credentials. It refuses to run while the key placeholders remain.

## Programming with the main ESP32 as the USB bridge

See **WIRING.svg**. Change wiring with power disconnected. These instructions assume a conventional DevKit with a USB-to-UART chip connected to its UART0 header pins, such as the CP210x board previously used. Native-USB boards or other PCB wiring need a matching programmer arrangement.

| Main ESP32 DevKit | ESP32-CAM |
|---|---|
| GPIO3 / RX0 | U0R / RX0 / GPIO3 |
| GPIO1 / TX0 | U0T / TX0 / GPIO1 |
| GND | GND |
| EN â†’ GND locally | Holds main ESP32 processor in reset |
| â€” | GPIO0 â†’ GND for programming |

The apparent RXâ†’RX and TXâ†’TX connections are intentional here: the main chip is held reset and the onboard **USB bridge TX is wired to the main RX0 header**, while USB bridge RX is wired to TX0. This is not a UART link between two running ESP32 processors. For a standalone USB-UART adapter, use adapter TXâ†’camera RX and adapter RXâ†’camera TX instead.

Power the camera at its 5V pin using a stable regulated supply, join supply/main/camera grounds, and disconnect the old positive power feed from the main board. Do not tie two supplies' +5 V outputs together or apply 5 V to UART/GPIO/3V3 pins. No microSD because GPIO13 is in use. Disconnect main GPIO19â†’camera GPIO13 while programming.

1. Close Serial Monitor and click **Disconnect** in Sentinel if it owns the COM port.
2. Connect the laptop USB to the main ESP32. Keep its ENâ†’GND jumper fitted while programming the camera.
3. Select **AI Thinker ESP32-CAM** (only for the matching classic PCB). This board profile enables PSRAM in the installed core. Select the main board's actual USB COM port; do not assume COM6 forever.
4. Choose **Upload Speed: 115200**, then **Verify** and **Upload**.
5. If upload stays at `Connecting...`, keep camera GPIO0 grounded and press/release the **camera's** reset button. The main board's auto-reset circuit does not reset the camera through the UART jumpers.
6. After successful upload, disconnect power. Remove camera GPIO0â†’GND and main ENâ†’GND, and remove the two UART jumper wires.
7. Restore **main GPIO19â†’camera GPIO13**, the existing trigger pull-down to GND, and common GND. Leave the sensor controller's original firmware unchanged. Power both boards normally and restart the camera.

The main board's BOOT button is not the camera's boot control. Holding main EN low and pulling camera GPIO0 low are two different operations on different boards.

## Normal running wiring

| Connection | Destination |
|---|---|
| Main GPIO19 | Camera GPIO13 |
| Trigger node | Existing 1 kÎ© pull-down â†’ GND, not in series |
| Camera 5V | Stable regulated 5V source |
| Camera GND | Supply GND and main GND |
| Main PIR input | GPIO13, unchanged |
| Main ultrasonic TRIG / divided ECHO | GPIO5 / GPIO18, unchanged |

## What to verify physically

Check actual PID `0x3660`, PSRAM detected, logged photo dimensions 800Ã—600, and `BURST COMPLETE: 5/5 photos saved on PC`. Test repeated bursts under the same lighting as the older sketch and compare the actual images. Compile success is not proof of correct PCB identity, exposure, physical upload or improved person-detection accuracy. Do not disable brownout protection.

References: [Espressif camera example](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/CameraWebServer.ino), [ESP32 boot modes](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html), [DevKitC V4 USB-UART schematic](https://dl.espressif.com/dl/schematics/esp32_devkitc_v4-sch-20180607a.pdf).
