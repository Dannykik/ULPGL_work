#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==========================
// Wi-Fi + API configuration
// ==========================
const char* WIFI_SSID = "VOTRE_WIFI";
const char* WIFI_PASSWORD = "VOTRE_MDP";
const char* API_URL = "http://192.168.1.10:8000/analyze_frame";
const char* API_KEY = "VOTRE_CLE_API";

// ==========================
// Hardware pins
// ==========================
const int BUTTON_PIN = 12; // bouton poussoir (avec pull-up)
const int BUZZER_PIN = 13;

// Long press
const unsigned long LONG_PRESS_MS = 1500;
unsigned long buttonPressStart = 0;
bool lastButtonState = HIGH;

// Système
bool surveillanceEnabled = false;
unsigned long lastCaptureMs = 0;
const unsigned long CAPTURE_INTERVAL_MS = 500;

void setDisplayMessage(const String& message) {
  // Remplacer par votre écran OLED/LCD.
  Serial.println("[ECRAN] " + message);
}

void setBuzzer(bool enabled) {
  digitalWrite(BUZZER_PIN, enabled ? HIGH : LOW);
}

void toggleSurveillance() {
  surveillanceEnabled = !surveillanceEnabled;

  if (!surveillanceEnabled) {
    setBuzzer(false);
    setDisplayMessage("Systeme OFF");
    return;
  }

  setDisplayMessage("Surveillance activee");
}

bool checkLongPressToggle() {
  bool buttonState = digitalRead(BUTTON_PIN);

  if (lastButtonState == HIGH && buttonState == LOW) {
    buttonPressStart = millis();
  }

  if (lastButtonState == LOW && buttonState == HIGH) {
    if (millis() - buttonPressStart >= LONG_PRESS_MS) {
      toggleSurveillance();
      lastButtonState = buttonState;
      return true;
    }
  }

  lastButtonState = buttonState;
  return false;
}

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connecte");
}

bool sendFrameAndApplyDecision(camera_fb_t* fb) {
  HTTPClient http;
  http.begin(API_URL);

  // multipart simple
  String boundary = "----ESP32Boundary";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.addHeader("x-api-key", API_KEY);

  String head = "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"frame\"; filename=\"frame.jpg\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  int totalLen = head.length() + fb->len + tail.length();
  uint8_t* payload = (uint8_t*)malloc(totalLen);
  if (!payload) {
    Serial.println("Erreur memoire payload");
    http.end();
    return false;
  }

  memcpy(payload, head.c_str(), head.length());
  memcpy(payload + head.length(), fb->buf, fb->len);
  memcpy(payload + head.length() + fb->len, tail.c_str(), tail.length());

  int code = http.POST(payload, totalLen);
  free(payload);

  if (code <= 0) {
    Serial.printf("Erreur HTTP: %d\n", code);
    http.end();
    return false;
  }

  String response = http.getString();
  http.end();

  DynamicJsonDocument doc(2048);
  auto err = deserializeJson(doc, response);
  if (err) {
    Serial.println("JSON invalide");
    return false;
  }

  bool threatDetected = doc["threat_detected"] | false;
  const char* displayMessage = doc["display_message"] | "Affichage normal";

  setDisplayMessage(String(displayMessage));
  setBuzzer(threatDetected);

  return true;
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  setBuzzer(false);

  // IMPORTANT: ajouter ici votre configuration camera ESP32-CAM (pins + init)
  // camera_config_t config = ...
  // esp_camera_init(&config);

  connectWifi();
  setDisplayMessage("Systeme OFF");
}

void loop() {
  checkLongPressToggle();

  if (!surveillanceEnabled) {
    delay(100);
    return;
  }

  if (millis() - lastCaptureMs < CAPTURE_INTERVAL_MS) {
    delay(10);
    return;
  }

  lastCaptureMs = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Capture echouee");
    return;
  }

  sendFrameAndApplyDecision(fb);
  esp_camera_fb_return(fb);
}
