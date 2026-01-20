// Definition des broches
#define BUTTON_PIN 14
#define BUZZER_PIN 12

#define SDA_PIN 15
#define SCL_PIN 13
// Connexion WIFI
#include <WiFi.h>

const char* ssid = "TON_WIFI";
const char* password = "MOT_DE_PASSE";

void connectWiFi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}
// Bouton + etat du systeme
bool systemActive = false;

void checkButton() {
  if (digitalRead(BUTTON_PIN) == LOW) {
    systemActive = !systemActive;
    delay(500);
  }
}
// Capture d'inage ESP32
#include "esp_camera.h"

camera_fb_t * captureImage() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) return NULL;
  return fb;
}
// Envoi d'image vers serveur IA
#include <HTTPClient.h>

String sendToServer(uint8_t* image, size_t length) {
  HTTPClient http;
  http.begin("http://IP_SERVEUR:8000/predict");
  http.addHeader("Content-Type", "application/octet-stream");

  int code = http.POST(image, length);
  String response = http.getString();
  http.end();

  return response;
}
// Buzzer + Ecran OLED
void alertOn() {
  digitalWrite(BUZZER_PIN, HIGH);
}

void alertOff() {
  digitalWrite(BUZZER_PIN, LOW);
}
// Loop principal
void loop() {
  checkButton();

  if (!systemActive) return;

  camera_fb_t* fb = captureImage();
  if (!fb) return;

  String result = sendToServer(fb->buf, fb->len);

  if (result.indexOf("ALERTE") >= 0) {
    alertOn();
  } else {
    alertOff();
  }

  esp_camera_fb_return(fb);
  delay(1500);
}
