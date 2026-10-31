// Resolution test derived from the local AI-Thinker-pinout uploader.
// Confirm your board pinout before uploading. OV3660 is a sensor, not a board model.
constexpr bool TEST_SVGA = true; // false = VGA baseline, true = SVGA test
// Main ESP32 GPIO19 -> camera GPIO13. No microSD (shares GPIO13).
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"
#include "esp_camera.h"
#include "esp_system.h"

// EDIT THESE THREE SETTINGS. Both PC and camera must share a reachable LAN.


// Use your PC's Wi-Fi IPv4 address from ipconfig, NEVER localhost here.



constexpr int TRIGGER_PIN = 13;
constexpr int PHOTOS = 5;
bool cameraReady = false, lastTrigger = false, pending = false;
unsigned long lastCameraTry = 0, lastWiFiTry = 0, queuedAt = 0, lastStatus = 0;
uint32_t burst = 0;
String session;

bool initializeCamera() {
  lastCameraTry = millis();
  Serial.println("Starting camera initialization...");
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
  if (!psramFound()) {
    Serial.println("RESOLUTION TEST STOPPED: PSRAM required; check board selection and PSRAM setting.");
    return false;
  }
  c.frame_size = TEST_SVGA ? FRAMESIZE_SVGA : FRAMESIZE_VGA;
  c.jpeg_quality = 12;
  c.fb_count = 1;
  c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x; retry in 10 seconds\n", err);
    esp_camera_deinit();
    return false;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  Serial.printf("Sensor PID: 0x%04x | PSRAM: %u bytes | test: %s | JPEG quality: 12\n",
                sensor ? sensor->id.PID : 0, (unsigned)ESP.getPsramSize(), TEST_SVGA ? "800x600" : "640x480");
  Serial.println("CAMERA READY");
  return true;
}

bool captureAndUpload(int photo) {
  unsigned long captureStart = millis();
  // Discard a waiting frame so each photo comes from a new acquisition.
  camera_fb_t* stale = esp_camera_fb_get();
  if (!stale) { Serial.println("No first frame"); return false; }
  esp_camera_fb_return(stale);
  camera_fb_t* frame = esp_camera_fb_get();
  if (!frame) { Serial.println("No fresh frame"); return false; }
  if (frame->format != PIXFORMAT_JPEG || frame->len < 4 ||
      frame->buf[0] != 0xff || frame->buf[1] != 0xd8) {
    Serial.println("Invalid JPEG frame");
    esp_camera_fb_return(frame);
    return false;
  }
  String id = session + "-" + String(burst) + "-" + String(photo);
  String url = String(SERVER_URL) + "?id=" + id;
  Serial.printf("Photo %d/5 CAPTURED: %ux%u, %u bytes, capture %lu ms\n", photo, (unsigned)frame->width, (unsigned)frame->height, (unsigned)frame->len, millis() - captureStart);
  bool saved = false;
  // Retry the SAME JPEG and ID. Server treats repeated delivery as one photo.
  for (int attempt = 1; attempt <= 2 && !saved; ++attempt) {
    if (WiFi.status() != WL_CONNECTED) break;
    WiFiClient client;
    HTTPClient http;
    http.setConnectTimeout(3000);
    http.setTimeout(5000);
    if (http.begin(client, url)) {
      http.addHeader("Content-Type", "image/jpeg");
      http.addHeader("X-Camera-Token", UPLOAD_TOKEN);
      unsigned long uploadStart = millis();
      int status = http.POST(frame->buf, frame->len);
      Serial.printf("UPLOAD TIME: %lu ms\n", millis() - uploadStart);
      saved = status == 200 || status == 201;
      Serial.printf("Photo %d/5 upload attempt %d: HTTP %d%s\n",
                    photo, attempt, status, saved ? " SAVED ON PC" : " FAILED");
      if (status > 0) Serial.println(http.getString());
      else Serial.println(HTTPClient::errorToString(status));
      http.end();
    }
    if (!saved) delay(300);
  }
  esp_camera_fb_return(frame);
  return saved;
}

void setup() {
  Serial.begin(115200); delay(300);
  Serial.println("@CAM BOOT");
  pinMode(TRIGGER_PIN, INPUT_PULLDOWN);
  pinMode(4, OUTPUT); digitalWrite(4, LOW);
  // Initialize camera before starting Wi-Fi; brownout protection stays enabled.
  cameraReady = initializeCamera();
  WiFi.mode(WIFI_STA); WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  String mac = WiFi.macAddress(); mac.replace(":", "");
  session = mac + "-" + String(esp_random(), HEX);
  Serial.println("PC destination: " + String(SERVER_URL));
  Serial.println("Waiting for camera/Wi-Fi readiness. Five JPEG uploads per trigger.");
}

void loop() {
  unsigned long now=millis();
  bool high=digitalRead(TRIGGER_PIN)==HIGH;
  if(high && !lastTrigger && !pending) {
    pending=true; queuedAt=now; ++burst;
    Serial.println("@CAM BUSY");
    Serial.printf("TRIGGER RECEIVED: burst %lu\n",(unsigned long)burst);
  }
  lastTrigger=high;
  if(!cameraReady && now-lastCameraTry>=10000) cameraReady=initializeCamera();
  if(WiFi.status()!=WL_CONNECTED && now-lastWiFiTry>=10000) {
    lastWiFiTry=now; Serial.println("Wi-Fi disconnected; reconnecting..."); WiFi.reconnect();
  }
  if(pending && now-queuedAt>=30000) {
    pending=false;
    Serial.println("BURST FAILED: camera/Wi-Fi unavailable for 30 seconds; 0/5 saved.");
    Serial.println("@CAM DONE 0/5");
  }
  if(pending && cameraReady && WiFi.status()==WL_CONNECTED) {
    pending=false;
    Serial.println("@CAM BUSY");
    Serial.println("Camera IP: " + WiFi.localIP().toString());
    unsigned long burstStart=millis();
    int saved=0;
    for(int photo=1;photo<=PHOTOS;++photo) {
      if(captureAndUpload(photo)) ++saved;
      if(photo<PHOTOS) delay(1000);
    }
    Serial.printf("BURST COMPLETE: %d/5 photos saved on PC, %lu ms\n",saved,millis()-burstStart);
    Serial.printf("@CAM DONE %d/5\n",saved);
    lastTrigger=digitalRead(TRIGGER_PIN)==HIGH;
  }
  now=millis();
  if(now-lastStatus>=2000) {
    lastStatus=now;
    if(pending) Serial.println("@CAM BUSY");
    else if(cameraReady && WiFi.status()==WL_CONNECTED) Serial.println("@CAM READY");
    else Serial.println("@CAM WAIT");
  }
  delay(5);
}
