// Flash ONLY the main ESP32. Leave the working five-photo ESP32-CAM firmware alone.
// Main GPIO19 -> camera GPIO13; GPIO23 -> passive piezo +; all grounds shared.
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"
#include "AlarmTiming.h"
#include "freertos/task.h"

// Edit these three values before uploading. Use the same hotspot as the laptop.



// Copy alarm_token from backend/config.local.json. Do not use camera_token here.


const int BUZZER_PIN = 23;
const int PIR_PIN = 13;
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int CAMERA_TRIGGER_PIN = 19;
const float DETECT_CM = 80.0;
const float CLEAR_CM = 100.0;
const unsigned long SAMPLE_MS = 250;
const unsigned long PULSE_MS = 500;
const unsigned long CLEARANCE_MS = 2000;
const unsigned long ALARM_POLL_MS = 1000;

bool armed = true;
bool pulseActive = false;
bool alarmBaselineReceived = false;
int agreements = 0;
unsigned long eventId = 0;
unsigned long lastSample = 0;
unsigned long triggerAt = 0;
unsigned long clearSince = 0;
unsigned long lastAlarmPoll = 0;
unsigned long lastWifiAttempt = 0;
String lastAlarmEvent;
AlarmTiming alarmTiming;
portMUX_TYPE alarmMux = portMUX_INITIALIZER_UNLOCKED;

void requestAlarm(AlarmKind kind) {
  portENTER_CRITICAL(&alarmMux);
  bool accepted = alarmTiming.request(millis(), kind);
  portEXIT_CRITICAL(&alarmMux);
  if (accepted) {
    Serial.printf("BUZZER REQUEST: %s, %lu ms\n",
                  kind == AlarmKind::Ml ? "ML PERSON" : "SENSOR FUSION",
                  static_cast<unsigned long>(kind == AlarmKind::Ml ? ML_BEEP_MS : SENSOR_BEEP_MS));
  }
}

void buzzerTask(void*) {
  bool sounding = false;
  for (;;) {
    portENTER_CRITICAL(&alarmMux);
    bool active = alarmTiming.activeAt(millis());
    portEXIT_CRITICAL(&alarmMux);
    if (active && !sounding) {
      tone(BUZZER_PIN, 2000);
      sounding = true;
    } else if (!active && sounding) {
      noTone(BUZZER_PIN);
      digitalWrite(BUZZER_PIN, LOW);
      sounding = false;
      Serial.println("BUZZER OFF");
    }
    // Independent of HTTP requests; no 1s/5s blocking delay in the main loop.
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

void sendCameraTrigger(const char* reason, bool sensorConfirmed) {
  if (!armed || pulseActive) {
    Serial.println("Not triggered: wait for REARMED.");
    return;
  }
  armed = false;
  agreements = 0;
  clearSince = 0;
  triggerAt = millis();
  eventId++;
  digitalWrite(CAMERA_TRIGGER_PIN, HIGH);
  pulseActive = true;
  if (sensorConfirmed) requestAlarm(AlarmKind::Sensor);
  Serial.printf("EVENT %lu: %s - GPIO19 HIGH for 500 ms\n", eventId, reason);
  Serial.println("Waiting for camera upload and laptop ML decision.");
}

void pollMlAlarm() {
  unsigned long now = millis();
  if (pulseActive || now - lastAlarmPoll < ALARM_POLL_MS) return;
  lastAlarmPoll = now;
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiAttempt >= 15000) {
      lastWifiAttempt = now;
      WiFi.reconnect();
      Serial.println("ML alarm: reconnecting Wi-Fi");
    }
    return;
  }
  WiFiClient client;
  HTTPClient http;
  if (!http.begin(client, ALARM_URL)) {
    Serial.println("ML alarm: invalid URL");
    return;
  }
  http.setTimeout(1200);
  http.addHeader("X-Alarm-Token", ALARM_TOKEN);
  int code = http.GET();
  String currentEvent;
  if (code == 200) {
    currentEvent = http.getString();
    currentEvent.trim();
  }
  http.end();
  if (code != 200) {
    Serial.printf("ML alarm: HTTP %d (check laptop, Wi-Fi, and token)\n", code);
    return;
  }
  // The first successful reply establishes a baseline: never alarm for old results at boot.
  if (!alarmBaselineReceived) {
    lastAlarmEvent = currentEvent;
    alarmBaselineReceived = true;
    Serial.println("ML alarm connected; watching for NEW person detections.");
    return;
  }
  if (currentEvent.length() && currentEvent != lastAlarmEvent) {
    lastAlarmEvent = currentEvent;
    requestAlarm(AlarmKind::Ml);
    Serial.printf("ML PERSON DETECTED in burst %s: five-second buzzer requested\n", currentEvent.c_str());
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  if (xTaskCreate(buzzerTask, "buzzerTimer", 2048, nullptr, 2, nullptr) != pdPASS) {
    Serial.println("BUZZER FAULT: timer task could not start; alarm output unavailable.");
  }
  digitalWrite(CAMERA_TRIGGER_PIN, LOW);
  pinMode(CAMERA_TRIGGER_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(ECHO_PIN, INPUT);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttempt = millis();
  Serial.println("MAIN ESP32 READY: sensor fusion = 1s buzzer; ML person detection = 5s buzzer.");
  Serial.println("PIR13, TRIG5, divided ECHO18, GPIO19 -> camera GPIO13.");
  Serial.println("Send T for a manual test after the camera has started.");
}

void loop() {
  unsigned long now = millis();
  if (pulseActive && now - triggerAt >= PULSE_MS) {
    digitalWrite(CAMERA_TRIGGER_PIN, LOW);
    pulseActive = false;
    Serial.println("GPIO19 returned LOW");
  }
  while (Serial.available()) {
    int command = Serial.read();
    if (command == 'T' || command == 't') sendCameraTrigger("MANUAL TEST", false);
  }
  pollMlAlarm();
  now = millis();
  if (now - lastSample < SAMPLE_MS) return;
  lastSample = now;

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long echo = pulseIn(ECHO_PIN, HIGH, 30000);
  bool valid = echo > 0;
  float cm = echo * 0.0343f / 2.0f;
  bool motion = digitalRead(PIR_PIN) == HIGH;
  bool nearby = valid && cm <= DETECT_CM;
  if (armed && motion && nearby) agreements++;
  else agreements = 0;
  Serial.printf("PIR:%s | ECHO:%lu us | ", motion ? "MOTION" : "CLEAR", echo);
  if (valid) Serial.printf("DISTANCE:%.1f cm | %s", cm, nearby ? "OBJECT" : "OUTSIDE ZONE");
  else Serial.print("NO ECHO | INVALID");
  Serial.printf(" | AGREEMENT:%d/3 | %s\n", agreements, armed ? "ARMED" : "WAIT CLEAR");
  if (armed && agreements >= 3) sendCameraTrigger("BOTH SENSORS AGREE", true);
  now = millis();
  if (!armed && !pulseActive && valid && !motion && cm > CLEAR_CM) {
    if (clearSince == 0) clearSince = now;
    if (now - clearSince >= CLEARANCE_MS) {
      armed = true;
      clearSince = 0;
      Serial.println("REARMED: area clear continuously for 2 seconds.");
    }
  } else clearSince = 0;
}
