# 🛗 Projet de Système de Contrôle d'Ascenseur Intelligent

Ce projet est une simulation d'un **ascenseur à 3 étages** contrôlé par un microcontrôleur Arduino. Il utilise des écrans LCD I2C, des boutons, des capteurs, un moteur, un servo-moteur pour la porte, et un module Bluetooth pour les commandes à distance.

## 🔧 Fonctionnalités

- Appel de l’ascenseur à l’un des 3 étages via boutons ou Bluetooth.
- Affichage dynamique de l’état et de l’étage courant sur 3 écrans LCD I2C.
- Mouvement de la cabine (montée ou descente) avec indication par LEDs.
- Arrêt automatique à l’étage demandé, ouverture et fermeture automatique de la porte.
- Détection d’obstacle pour empêcher la fermeture de la porte.
- Avertissement sonore (buzzer) à l’arrivée à l’étage.

## 🧰 Matériel Utilisé

- Arduino Uno
- 3 x LCD I2C 16x2
- 3 x boutons poussoirs (un par étage)
- 3 x capteurs de position (ex: fin de course ou IR)
- 1 x Servo-moteur (SG90) pour la porte
- 1 x Module Bluetooth HC-05 ou HC-06
- 1 x Moteur DC pour déplacer la cabine (avec L298N ou similaire)
- LEDs pour la direction (monte/descend)
- 1 x buzzer
- 1 x capteur d’obstacle IR (devant la porte)

## 🔌 Schéma de Connexion

> Voir le fichier `schema_proteus.pdsprj` ou `schema.png` si inclus dans le dépôt.


## 📲 Commandes Bluetooth

Le module Bluetooth permet de contrôler l’ascenseur à distance via une application mobile :
- Envoyer `0` → Aller à l'étage 0
- Envoyer `1` → Aller à l'étage 1
- Envoyer `2` → Aller à l'étage 2

## 🚧 Améliorations Futures

- Ajout d’un écran OLED ou TFT pour une interface plus moderne.
- Interface mobile dédiée (Flutter, Android Studio).
- Ajout de la sécurité par mot de passe pour contrôler l’ascenseur.
- Historique des déplacements via carte SD.

## 🧑‍💻 Auteur

**KIKWAYA KASINDI Danny**  
Projet académique et d’apprentissage en génie électrique et informatique.  
[RDC - ULPGL Goma]  

---

> Ce projet est libre d'utilisation à des fins éducatives. Pour toute utilisation commerciale, merci de demander l'autorisation.

