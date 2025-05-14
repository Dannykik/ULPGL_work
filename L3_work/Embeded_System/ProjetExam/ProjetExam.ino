#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// LCD via I2C (à adapter si nécessaire)
LiquidCrystal_I2C lcd1(0x25, 16, 2);
LiquidCrystal_I2C lcd2(0x24, 16, 2);
LiquidCrystal_I2C lcd3(0x22, 16, 2);

// Boutons d'appel
const int btnEtage0 = 2;
const int btnEtage1 = 3;
const int btnEtage2 = 4;

// Capteurs de position
const int capteur0 = A0;
const int capteur1 = A1;
const int capteur2 = A2;

// LEDs direction
const int ledMonte = 9;
const int ledDescend = 10;

// Buzzer
const int buzzer = 12;

// Moteur
const int motorIN1 = 7;
const int motorIN2 = 8;
const int motorEN  = 5;

// Servo porte
Servo servoPorte;
const int pinServo = 6;

// Capteur obstacle IR
const int capteurObstacle = A3;

// Variables globales
int etageActuel = 0;
int appelEtage = -1;
bool enMouvement = false;

// Déclaration des prototypes des fonctions
void afficherEtage();
void lireBoutons();
void gererBluetooth();
void deplacerCabine(int destination);
bool capteurAtteint(int etage);
void arretEtOuverture();

void setup() {
  Serial.begin(9600);

  // Initialisation LCDs
  lcd1.init(); lcd2.init(); lcd3.init();
  lcd1.backlight(); lcd2.backlight(); lcd3.backlight();
  lcd1.setCursor(0, 0); lcd1.print("Ascenseur Pret");
  lcd2.setCursor(0, 0); lcd2.print("Ascenseur Pret");
  lcd3.setCursor(0, 0); lcd3.print("Ascenseur Pret");

  // Initialisation des broches
  pinMode(btnEtage0, INPUT_PULLUP);
  pinMode(btnEtage1, INPUT_PULLUP);
  pinMode(btnEtage2, INPUT_PULLUP);

  pinMode(capteur0, INPUT);
  pinMode(capteur1, INPUT);
  pinMode(capteur2, INPUT);
  pinMode(capteurObstacle, INPUT);

  pinMode(ledMonte, OUTPUT);
  pinMode(ledDescend, OUTPUT);
  pinMode(buzzer, OUTPUT);
  
  pinMode(motorIN1, OUTPUT);
  pinMode(motorIN2, OUTPUT);
  pinMode(motorEN, OUTPUT);
  digitalWrite(motorEN, HIGH);

  servoPorte.attach(pinServo);
  servoPorte.write(0);  // porte fermée

  afficherEtage();
}

void loop() {
  lireBoutons();
  gererBluetooth();

  if (appelEtage != -1 && appelEtage != etageActuel && !enMouvement) {
    deplacerCabine(appelEtage);
  }

  if (etageActuel == appelEtage && appelEtage != -1 && !enMouvement) {
    arretEtOuverture();
    appelEtage = -1;
  }
}

void lireBoutons() {
  if (digitalRead(btnEtage0) == LOW) appelEtage = 0;
  else if (digitalRead(btnEtage1) == LOW) appelEtage = 1;
  else if (digitalRead(btnEtage2) == LOW) appelEtage = 2;
}

void gererBluetooth() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == '0') appelEtage = 0;
    else if (cmd == '1') appelEtage = 1;
    else if (cmd == '2') appelEtage = 2; 
  }
}

void deplacerCabine(int destination) {
  if (destination == etageActuel) return;

  enMouvement = true;

  // Affichage sur les 3 LCD
  String texte = "Aller a l'etage " + String(destination);
  lcd1.clear(); lcd1.setCursor(0, 0); lcd1.print(texte);
  lcd2.clear(); lcd2.setCursor(0, 0); lcd2.print(texte);
  lcd3.clear(); lcd3.setCursor(0, 0); lcd3.print(texte);
  Serial.println(texte);

  // Direction du moteur
  if (destination > etageActuel) {
    digitalWrite(ledMonte, HIGH);
    digitalWrite(ledDescend, LOW);
    digitalWrite(motorIN1, HIGH);
    digitalWrite(motorIN2, LOW);
  } else {
    digitalWrite(ledMonte, LOW);
    digitalWrite(ledDescend, HIGH);
    digitalWrite(motorIN1, LOW);
    digitalWrite(motorIN2, HIGH);
  }

  analogWrite(motorEN, 200);

  // Attente du capteur de destination
  /*
   *  while (!capteurAtteint(destination)) {
   *  delay(100);
   *  }
   */
  delay(3000);

  analogWrite(motorEN, 0);
  digitalWrite(ledMonte, LOW);
  digitalWrite(ledDescend, LOW);
  etageActuel = destination;
  enMouvement = false;
  afficherEtage();
}

bool capteurAtteint(int etage) {
  switch (etage) {
    case 0: return digitalRead(capteur0) == LOW;
    case 1: return digitalRead(capteur1) == LOW;
    case 2: return digitalRead(capteur2) == LOW;
    default: return false;
  }
}

void afficherEtage() {
  String texte = "Etage: " + String(etageActuel);
  lcd1.clear(); lcd1.setCursor(0, 0); lcd1.print(texte);
  lcd2.clear(); lcd2.setCursor(0, 0); lcd2.print(texte);
  lcd3.clear(); lcd3.setCursor(0, 0); lcd3.print(texte);
  Serial.println(texte);  //Affichage dans l'application bluethooth
}

void arretEtOuverture() {
  tone(buzzer, 1000, 300); // signal sonore d’arrivée
  delay(500);

  // Ouvrir porte uniquement si pas d’obstacle
  if (digitalRead(capteurObstacle) == LOW) {
    lcd1.clear(); lcd1.setCursor(0, 0); lcd1.print("Porte Ouverte");
    lcd2.clear(); lcd2.setCursor(0, 0); lcd2.print("Porte Ouverte");
    lcd3.clear(); lcd3.setCursor(0, 0); lcd3.print("Porte Ouverte");
    Serial.println("Porte Ouverte");
    servoPorte.write(90);  // porte ouverte
    delay(2000);           // temps ouvert
    servoPorte.write(0);   // refermer
    lcd1.clear(); lcd1.setCursor(0, 0); lcd1.print("Porte Fermée");
    lcd2.clear(); lcd2.setCursor(0, 0); lcd2.print("Porte Fermée");
    lcd3.clear(); lcd3.setCursor(0, 0); lcd3.print("Porte Fermée");
    Serial.println("Porte Fermée");
  } else {
    // Clignote pour montrer obstacle
    for (int i = 0; i < 5; i++) {
      digitalWrite(buzzer, HIGH);
      delay(100);
      digitalWrite(buzzer, LOW);
      delay(100);
    }
  }
}
