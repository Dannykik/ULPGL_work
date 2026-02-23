# Security AI App (Sans ESP32)

Cette version est orientée **100% sans ESP32**.

## Objectif

Application de surveillance avec :

- analyse IA côté serveur (`main.py`)
- application web de surveillance locale (`surveillance_app.py`)
- caméra de l'appareil (PC / téléphone via navigateur)

## 1) Lancer l'application de surveillance complète

```bash
cd mon_travail/security_ai_app
uvicorn surveillance_app:app --host 0.0.0.0 --port 8500
```

Ouvrir :

- `http://localhost:8500` (PC)
- `http://IP_DE_VOTRE_PC:8500` (téléphone sur le même Wi‑Fi)

### Fonctionnalités UI

- Activer / arrêter la vidéo
- Choisir la caméra
- Démarrer / arrêter l'enregistrement (`.webm`)
- Capture image (`.png`)
- Suivi de mouvement
- Journal des événements
- Tableau base de données

## 2) Base de données incluse

La base SQLite est créée automatiquement :

- `mon_travail/security_ai_app/surveillance.db`

Tables :

- `events`
- `recordings`

Endpoints :

- `POST /api/events`
- `GET /api/events`
- `POST /api/recordings`
- `GET /api/recordings`
- `GET /health`

## 3) API IA (optionnelle)

Si vous voulez uniquement le pipeline IA (détection + anomalie) :

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints principaux :

- `POST /analyze_frame`
- `POST /predict` (legacy)
- `GET /stats`
- `GET /health`
- `GET /camera_feed` (flux vidéo externe facultatif)

## 4) Variables utiles

- `SECURITY_API_KEY`
- `DETECTION_MODEL_PATH`
- `ANOMALY_MODEL_PATH`
- `HUMAN_MODEL_PATH`
- `KNIFE_MODEL_PATH`
- `CAMERA_STREAM_URL`

## 5) Dépendances

```bash
pip install -r requirements.txt
```

Si problème FastAPI/Pydantic `Sentinel` :

```bash
pip install --upgrade typing_extensions pydantic pydantic-core fastapi
```
