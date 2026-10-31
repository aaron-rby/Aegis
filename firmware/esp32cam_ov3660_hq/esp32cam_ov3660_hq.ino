/* Classic AI-Thinker-pin-map ESP32-CAM fitted with an OV3660.
   Do not use this pin map for ESP32-S3 or a different camera PCB.
   Main GPIO19 -> camera GPIO13, common GND; no microSD.
   Five acknowledged uploads; stop on failure instead of skipping a photo.
   Unsent images live in RAM only and are lost on reset/power loss.
*/
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include "esp_system.h"
#include "config.h"

constexpr int TRIGGER_PIN = 13;
constexpr int PHOTOS = 5;
constexpr uint32_t INTER_PHOTO_MS = 250;
constexpr int MAX_CAPTURE_ATTEMPTS = 3;
constexpr int MAX_UPLOAD_ATTEMPTS = 6;
constexpr uint32_t SLOT_TIMEOUT_MS = 150000;
constexpr uint32_t READY_TIMEOUT_MS = 60000;
bool cameraReady = false, busy = false, pending = false, previousTrigger = false;
uint32_t lastInit = 0, lastReconnect = 0, queuedAt = 0, burst = 0;
String session;

bool initializeCamera() {
  lastInit = millis();
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 5; c.pin_d1 = 18; c.pin_d2 = 19; c.pin_d3 = 21;
  c.pin_d4 = 36; c.pin_d5 = 39; c.pin_d6 = 34; c.pin_d7 = 35;
  c.pin_xclk = 0; c.pin_pclk = 22; c.pin_vsync = 25; c.pin_href = 23;
  c.pin_sccb_sda = 26; c.pin_sccb_scl = 27;
  c.pin_pwdn = 32; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  const bool psram = psramFound();
  c.frame_size = psram ? HQ_FRAME_SIZE : FRAMESIZE_QVGA;
  c.jpeg_quality = JPEG_QUALITY;
  c.fb_count = 1; // One buffer leaves more RAM available for higher-detail JPEGs.
  c.fb_location = psram ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("Camera initialization failed: 0x%x; retry in 10 seconds\n", unsigned(err));
    esp_camera_deinit();
    return false;
  }
  sensor_t* s = esp_camera_sensor_get();
  if (!s || s->id.PID != OV3660_PID) {
    Serial.printf("Expected OV3660; detected PID 0x%04x. Check sensor/board identification.\n", s ? s->id.PID : 0);
    esp_camera_deinit();
    return false;
  }
  if (s->set_whitebal(s, 1) != 0) Serial.println("Warning: auto white balance setting rejected");
  if (s->set_exposure_ctrl(s, 1) != 0) Serial.println("Warning: auto exposure setting rejected");
  if (s->set_gain_ctrl(s, 1) != 0) Serial.println("Warning: auto gain setting rejected");
  s->set_vflip(s, FLIP_VERTICAL);
  s->set_hmirror(s, MIRROR_HORIZONTAL);
  Serial.printf("OV3660 detected. PSRAM: %s. JPEG quality: %d.\n", psram ? "yes" : "NO: QVGA fallback", JPEG_QUALITY);
  // Give automatic exposure/white balance several actual frames to settle.
  for (int i = 0; i < 6; ++i) {
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame) esp_camera_fb_return(frame);
    delay(100);
  }
  Serial.println("CAMERA READY");
  return true;
}

void reconnectWiFi() {
  if (WiFi.status() != WL_CONNECTED && millis() - lastReconnect >= 10000) {
    lastReconnect = millis();
    WiFi.reconnect();
    Serial.println("Wi-Fi reconnect requested");
  }
}

void serviceTrigger() {
  const bool high = digitalRead(TRIGGER_PIN) == HIGH;
  if (high && !previousTrigger) {
    if (busy || pending) Serial.println("TRIGGER ignored: existing burst pending/active");
    else {
      pending = true; queuedAt = millis(); ++burst;
      Serial.printf("TRIGGER RECEIVED: burst %lu\n", (unsigned long)burst);
    }
  }
  previousTrigger = high;
}

void waitWithService(uint32_t duration) {
  const uint32_t start = millis();
  while (millis() - start < duration) {
    serviceTrigger(); reconnectWiFi(); delay(10);
  }
}

camera_fb_t* freshFrame() {
  camera_fb_t* old = esp_camera_fb_get();
  if (!old) return nullptr;
  esp_camera_fb_return(old);
  camera_fb_t* f = esp_camera_fb_get();
  if (!f) return nullptr;
  // The receiver requires both JPEG boundary markers.
  if (f->format != PIXFORMAT_JPEG || f->len < 4 ||
      f->buf[0] != 0xff || f->buf[1] != 0xd8 ||
      f->buf[f->len - 2] != 0xff || f->buf[f->len - 1] != 0xd9) {
    Serial.println("Capture rejected: incomplete/non-JPEG frame");
    esp_camera_fb_return(f);
    return nullptr;
  }
  return f;
}

bool captureAndDeliver(int photo) {
  const uint32_t start = millis();
  camera_fb_t* frame = nullptr;
  for (int attempt = 0; attempt < MAX_CAPTURE_ATTEMPTS && !frame; ++attempt) {
    frame = freshFrame();
    if (!frame) waitWithService(500);
  }
  if (!frame) { Serial.printf("Photo %d: capture failed\n", photo); return false; }
  const String id = session + "-" + String(burst) + "-" + String(photo);
  const String url = String(SERVER_URL) + "?id=" + id;
  Serial.printf("Photo %d/5 captured: %ux%u, %u bytes\n", photo, frame->width, frame->height, unsigned(frame->len));
  bool saved = false;
  for (int attempt = 1; attempt <= MAX_UPLOAD_ATTEMPTS; ++attempt) {
    while (WiFi.status() != WL_CONNECTED && millis() - start < SLOT_TIMEOUT_MS) waitWithService(100);
    if (millis() - start >= SLOT_TIMEOUT_MS) break;
    WiFiClient client;
    HTTPClient http;
    http.setConnectTimeout(4000);
    http.setTimeout(18000);
    int status = -1;
    String acknowledgement;
    if (http.begin(client, url)) {
      http.addHeader("Content-Type", "image/jpeg");
      http.addHeader("X-Camera-Token", UPLOAD_TOKEN);
      status = http.POST(frame->buf, frame->len);
      if (status == 200 || status == 201) acknowledgement = http.getString();
      http.end();
    }
    // Match the gallery receiver's {"saved": "<id>.jpg"} acknowledgement.
    const String expected = "\"" + id + ".jpg\"";
    saved = (status == 200 || status == 201) &&
            acknowledgement.indexOf("\"saved\"") >= 0 && acknowledgement.indexOf(expected) >= 0;
    Serial.printf("Photo %d/5 attempt %d: HTTP %d %s\n", photo, attempt, status, saved ? "SAVED ON PC" : "NOT CONFIRMED");
    if (saved) break;
    if (status == 400 || status == 401 || status == 403 || status == 404 || status == 409 || status == 413 || status == 415) {
      Serial.println("Non-retryable request/configuration error; check URL, token, ID and image size");
      break;
    }
    if (attempt < MAX_UPLOAD_ATTEMPTS) waitWithService(min(uint32_t(attempt * 2000), uint32_t(10000)));
  }
  esp_camera_fb_return(frame); // Retained for ALL retries, never replaced with a different JPEG.
  return saved;
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIGGER_PIN, INPUT_PULLDOWN);
  pinMode(4, OUTPUT); digitalWrite(4, LOW); // Flash stays off; provide adequate ambient light.
  if (String(WIFI_SSID).startsWith("YOUR_") || String(SERVER_URL).indexOf("YOUR_") >= 0 ||
      String(UPLOAD_TOKEN).startsWith("YOUR_")) {
    Serial.println("EDIT config.h: Wi-Fi, laptop IPv4 upload URL, and gallery upload token.");
    while (true) delay(1000);
  }
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  session = WiFi.macAddress(); session.replace(":", "");
  session += "-" + String(esp_random(), HEX);
  cameraReady = initializeCamera();
  Serial.printf("Receiver: %s\n", SERVER_URL);
  Serial.println("Ready for GPIO13 triggers. Five confirmed uploads requested per burst.");
}

void loop() {
  serviceTrigger(); reconnectWiFi();
  if (!cameraReady && millis() - lastInit >= 10000) cameraReady = initializeCamera();
  if (pending && millis() - queuedAt >= READY_TIMEOUT_MS) {
    pending = false;
    Serial.println("BURST FAILED: camera/Wi-Fi unavailable for 60 seconds; 0/5 saved");
  }
  if (pending && cameraReady && WiFi.status() == WL_CONNECTED) {
    pending = false; busy = true;
    int saved = 0;
    for (int photo = 1; photo <= PHOTOS; ++photo) {
      if (!captureAndDeliver(photo)) break; // Never skip a failed slot and claim a full burst.
      ++saved;
      if (photo < PHOTOS) waitWithService(INTER_PHOTO_MS);
    }
    if (saved == PHOTOS) Serial.println("BURST COMPLETE: 5/5 photos saved on PC");
    else Serial.printf("BURST FAILED: %d/5 saved; missing photo %d onward. New trigger starts a NEW burst.\n", saved, saved + 1);
    previousTrigger = digitalRead(TRIGGER_PIN) == HIGH;
    busy = false;
  }
  delay(5);
}
