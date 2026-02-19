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

---

## 🔗 Fusion des deux modèles avec une caméra ESP32

Si vous voulez combiner votre **modèle de détection d'armes** et votre **autoencodeur d'anomalies** avec une caméra ESP32-CAM, vous pouvez utiliser l'architecture suivante (simple et réaliste pour un mémoire).

### 1) Flux global recommandé

1. **ESP32-CAM capture** des images (ou un flux MJPEG court).
2. ESP32 envoie les frames au **serveur Python** (votre machine) via HTTP.
3. Le serveur exécute en parallèle :
   - le modèle **YOLO (arme)**
   - le modèle **Autoencodeur (anomalie de scène)**
4. Le serveur applique une logique de **fusion de décision**.
5. Le système retourne :
   - état `normal` / `anormal`
   - présence d'arme (`oui/non` + classe)
   - **niveau de risque** final (🟢🟡🟠🔴)
6. En cas de risque élevé : envoi d'une **alerte** (email, Telegram, dashboard, etc.).

### 2) Fusion de décision (règle simple)

Vous pouvez démarrer avec ces règles :

- `arme = 0` et `anomalie = 0` → **🟢 Normal**
- `arme = 0` et `anomalie = 1` → **🟡 Anomalie comportementale**
- `arme = 1` et `anomalie = 0` → **🟠 Objet dangereux**
- `arme = 1` et `anomalie = 1` → **🔴 Menace critique**

Ensuite, vous pouvez pondérer avec les scores (`confidence YOLO`, `MSE autoencodeur`) pour obtenir un risque continu.

### 3) API minimale côté serveur

Exposez une route comme :

- `POST /analyze_frame`

Entrée : image JPEG envoyée par ESP32.

Sortie JSON (exemple) :

```json
{
  "weapon_detected": true,
  "weapon_class": "gun",
  "weapon_conf": 0.91,
  "anomaly_score": 0.037,
  "anomaly_detected": true,
  "risk_level": "critical"
}
```

### 4) Conseils pratiques pour ESP32-CAM

- Utiliser une résolution modérée (`QVGA` ou `VGA`) pour limiter la latence.
- Envoyer 1 image toutes les 300–700 ms (au lieu de 30 FPS).
- Ajouter une clé API simple dans le header HTTP pour sécuriser l'envoi.
- Garder l'inférence sur votre machine (pas sur l'ESP32), car l'ESP32 est trop limité pour YOLO/autoencodeur.

### 5) Architecture adaptée à votre mémoire (Région des Grands Lacs)

- **Couche acquisition** : ESP32-CAM dans zones cibles.
- **Couche analyse IA** : serveur local (YOLO + Autoencodeur + fusion).
- **Couche supervision** : Streamlit + journal d'événements + alertes.
- **Impact attendu** : détection précoce des menaces et appui à la sécurité communautaire.

Cette architecture est progressive : vous pouvez d'abord valider sur webcam locale, puis remplacer la source vidéo par l'ESP32-CAM sans changer le cœur IA.

---

## 🚀 Suite réalisée : API prête pour ESP32-CAM

Un serveur FastAPI est disponible dans `main.py` avec :

- `GET /health` : test rapide de disponibilité
- `POST /analyze_frame` : analyse d'une image envoyée (multipart)
- `POST /predict` : alias de compatibilité

### Lancer l'API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Variables d'environnement utiles

- `SECURITY_API_KEY` : clé API attendue dans le header `x-api-key`
- `ANOMALY_THRESHOLD` : seuil anomalie (défaut `0.02`)
- `WEAPON_CONF_THRESHOLD` : confiance minimale YOLO (défaut `0.4`)
- `DETECTION_MODEL_PATH` : chemin du modèle de détection YOLO (défaut `models/yolov8_weapon.pt`)
- `ANOMALY_MODEL_PATH` : chemin du modèle autoencodeur (défaut `models/autoencoder_ucsd.h5`)

### Exemple de requête (depuis PC/ESP32 gateway)

```bash
curl -X POST "http://localhost:8000/analyze_frame" \
  -H "x-api-key: VOTRE_CLE" \
  -F "frame=@image.jpg"
```

Cette réponse JSON peut être affichée directement dans Streamlit pour déclencher les alertes selon `risk_level`.

---

## 🧩 Intégration de votre algorithme ESP32 (bouton + buzzer + écran)

La logique de votre organigramme est maintenant reflétée dans le projet :

1. **Appui long bouton** côté ESP32 → ON/OFF de la surveillance.
2. Si ON : capture image périodique + envoi au serveur (`/analyze_frame`).
3. Le serveur IA renvoie :
   - `risk_level`
   - `threat_detected`
   - `buzzer_on`
   - `display_message`
4. L'ESP32 applique l'action :
   - menace détectée → buzzer ON + écran ALERTE
   - pas de menace → affichage normal + buzzer OFF

### Fichier ESP32 ajouté

- `esp32_cam_client/esp32_cam_client.ino`

Ce sketch montre :
- la détection d'appui long,
- l'alternance **Système ON / OFF**,
- l'envoi d'image au serveur FastAPI,
- l'activation du buzzer selon la réponse IA.

> Remarque : vous devez compléter la configuration `camera_config_t` selon votre carte ESP32-CAM (AI Thinker, etc.).

---

## 🧪 Démarrage local avec Conda (Windows/Linux)

### 1) Cloner et se placer dans le projet

```bash
git clone <URL_DU_REPO>
cd ULPGL_work/mon_travail/security_ai_app
```

### 2) Créer l'environnement Conda

```bash
conda create -n security_ai python=3.10 -y
conda activate security_ai
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Lancer l'API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4) Test rapide

```bash
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/analyze_frame" -F "frame=@image.jpg"
```

### ⚠️ Dépannage PyTorch 2.6 (`_pickle.UnpicklingError`)

Si vous voyez une erreur liée à `weights_only` lors du chargement YOLO :

1. Réinstallez PyTorch en version `<2.6` (recommandé `2.5.1`) :

```bash
pip uninstall -y torch torchvision torchaudio
pip install "torch<2.6" torchvision torchaudio
```

2. Relancez ensuite `uvicorn` (ou `python main.py`).

```bash
python -c "import torch; print(torch.__version__)"
```

La version doit être `<2.6` si le checkpoint reste incompatible.

> Le projet force aussi `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` et ajoute des safe-globals ultralytics pour améliorer la compatibilité avec les checkpoints YOLO legacy.

### 🔁 Si vous avez changé le modèle de détection

Vous pouvez lancer avec votre nouveau fichier sans modifier le code :

```bash
# Linux/macOS
export DETECTION_MODEL_PATH="models/mon_nouveau_modele.pt"
export ANOMALY_MODEL_PATH="models/autoencoder_ucsd.h5"
uvicorn main:app --host 0.0.0.0 --port 8000
```

```powershell
# Windows PowerShell
$env:DETECTION_MODEL_PATH = "models/mon_nouveau_modele.pt"
$env:ANOMALY_MODEL_PATH = "models/autoencoder_ucsd.h5"
uvicorn main:app --host 0.0.0.0 --port 8000
```

Si le fichier n'existe pas, l'API arrête le démarrage avec un message explicite.
