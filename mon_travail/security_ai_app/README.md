# 🛡️ Intelligent Video Surveillance System  
### Détection d’objets dangereux et d’anomalies comportementales par Vision par Ordinateur

---

## 📌 Présentation du projet

Ce projet consiste en la conception et le développement d’un **système intelligent de vidéosurveillance** basé sur la **vision par ordinateur** et le **deep learning**, visant à renforcer la sécurité dans les milieux publics.

Le système combine :
- la **détection d’objets dangereux** (armes à feu, couteaux, grenades, etc.)
- la **détection d’anomalies comportementales** dans les scènes vidéo

Une **interface graphique interactive** a été développée avec **Streamlit** afin de visualiser les résultats en temps réel et de générer des alertes vers un centre de contrôle.

---

## 🎓 Cadre académique

**Université :** Université Libre des Pays des Grands Lacs (ULPGL)  
**Faculté :** Faculté des Sciences et Technologies  
**Niveau :** Licence (L3)  
**Type de projet :** Projet académique – Mémoire de fin de cycle  

---

## 🧠 Architecture du système

Le système repose sur une architecture modulaire composée de deux modèles principaux :

1. **Détection d’objets dangereux**
   - Modèle : YOLOv8
   - Tâche : Détection d’armes (pistolet, couteau, fusil, grenade)
   - Dataset : Dataset annoté (Roboflow)

2. **Détection d’anomalies comportementales**
   - Modèle : Autoencodeur (UCSD Anomaly Dataset)
   - Principe : Erreur de reconstruction (MSE)
   - Sortie : Score d’anomalie

Les sorties des deux modèles sont ensuite **fusionnées** pour déterminer le niveau de risque.

---

## 🚨 Niveaux de risque

- 🟢 Situation normale  
- 🟡 Anomalie comportementale détectée  
- 🟠 Objet dangereux détecté  
- 🔴 Menace critique (anomalie + objet dangereux)

En cas de menace, une **alerte est générée** et transmise vers un centre de contrôle (simulation, extensible vers ESP32).

---

## 🖥️ Interface graphique

L’interface graphique est développée avec **Streamlit** et permet :
- l’utilisation de la **webcam**
- l’affichage en temps réel des détections
- la visualisation du score d’anomalie
- l’affichage du niveau de risque
- l’intégration d’une identité visuelle académique (logo ULPGL)

---

## 📁 Structure du projet

