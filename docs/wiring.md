# Main ESP32 and ESP32-CAM wiring and power

This records the **main-controller sketch supplied by the user**, not a readback of either board's flash. The ESP32-CAM sketch identity remains unverified. Do not flash a guessed camera sketch over the working five-photo uploader merely to match a filename.

| Main ESP32 connection | Device connection | Purpose |
|---|---|---|
| GPIO19 | ESP32-CAM GPIO13 | Active-high camera trigger, 500 ms |
| GND | ESP32-CAM GND and sensor grounds | Common signal reference |
| PIR sensor output | GPIO13 | Motion input |
| Ultrasonic TRIG | GPIO5 | Trigger output |
| Ultrasonic ECHO **through a 5 V-to-3.3 V level divider** | GPIO18 | Distance input; never apply 5 V directly |
| Passive piezo +, piezo - to GND | GPIO23 | Audible alarm |

The supplied main sketch requires PIR motion **and** a valid distance at or below 80 cm for three samples before automatic triggering. It rearms only after PIR is clear and distance is above 100 cm continuously for two seconds. `T` in the main Serial Monitor manually pulses GPIO19 when armed. A serial `EVENT` or `GPIO19 returned LOW` line does not confirm camera capture/upload. The sketch uses `BEEP_MS = 1000` even though one printed log line says “two-second alarm”; the actual configured beep is one second.

Power the ESP32-CAM 5V pin from a stable **regulated 5 V** supply capable of its capture/Wi-Fi current peaks. Connect that supply's GND to camera GND and main ESP32 GND. Do not feed 5 V into GPIO13 or the camera's 3V3 pin. Powering the camera from the main ESP32's 5 V rail may fail if the upstream USB source, regulator, or wiring sags under load. Measure between the camera's **5V and GND pins while it captures and uploads**; check the source's current capacity and wiring. Software cannot measure the camera's 5 V pin without additional measurement hardware. Turn power off before rewiring.

The previous wiring intentionally has **no** ESP32-CAM U0T-to-main-GPIO16 serial connection. To read camera boot/upload logs, attach a suitable USB-to-UART adapter to the camera separately with a common ground and correct logic levels; avoid simultaneously driving its UART from multiple sources. Remove flashing connections before normal operation.

## Boot, reset, and COM port

1. Connect the laptop to the same hotspot as the camera. Confirm its Wi-Fi IPv4 and that `START_ALL.bat` reports both services ready.
2. Power/reset the ESP32-CAM in normal run mode; remove GPIO0-to-GND if it was used for flashing. Allow it to join Wi-Fi before any trigger. A camera serial adapter, if connected, should show Wi-Fi/upload diagnostics at the firmware's configured baud rate (often 115200; verify on that sketch).
3. Connect/power the main ESP32. In Arduino IDE, choose the **main ESP32's** current COM port; COM6 was observed previously and is not guaranteed. Set Serial Monitor to **115200 baud**, open it, and press the main board's EN/RST button if the ready line was missed.
4. Wait for `MAIN ESP32 READY` and `ARMED` or `REARMED`. Keep the camera aimed and powered; send one `T` for a manual test. Wait for the five-photo burst to finish before another trigger.
5. If the main board enters a reboot loop or prints `csum err`, inspect its USB power/cable, flash/boot connections, and board settings before treating it as an ML failure.

Current firmware identity log: main board — user-supplied main sketch (GPIO19 trigger, no UART camera log), last upload claimed by user; exact flashed binary/hash unverified. Camera board — five-photo HTTP uploader demonstrated by live bursts, exact sketch filename/version unverified. Record the actual Arduino sketch path, board type, and upload date after the next deliberate flash; do not infer it from files on the PC.
