#pragma once
// Copy to config.h and configure locally. Keep credentials private.
static const char WIFI_SSID[] = "YOUR_WIFI_NAME";
static const char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";
// Original JPEG receiver (port 5000), NOT the Sentinel dashboard (port 8765).
static const char SERVER_URL[] = "http://YOUR_LAPTOP_IP:5000/upload";
static const char UPLOAD_TOKEN[] = "REPLACE_WITH_A_RANDOM_TOKEN_AT_LEAST_16_CHARACTERS";

// SVGA = 800x600; change to FRAMESIZE_XGA for 1024x768 after testing.
// Higher resolutions need more RAM and take longer to upload.
static constexpr framesize_t HQ_FRAME_SIZE = FRAMESIZE_SVGA;
static constexpr int JPEG_QUALITY = 12; // Lower means less compression/larger JPEG.
static constexpr bool FLIP_VERTICAL = false; // Change only if the image is upside-down.
static constexpr bool MIRROR_HORIZONTAL = false;
