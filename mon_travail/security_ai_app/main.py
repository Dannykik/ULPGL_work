import datetime
import os
from typing import Any, Dict, List, Optional

# Compat PyTorch 2.6+ (évite l'erreur weights_only=True par défaut)
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

import cv2
import numpy as np
import requests
import torch
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from tensorflow.keras.models import load_model
from ultralytics import YOLO
from fastapi.middleware.cors import CORSMiddleware

def _patch_torch_for_ultralytics() -> None:
    """Compatibilité PyTorch 2.6+ pour charger des checkpoints YOLO legacy."""
    try:
        from ultralytics.nn.tasks import (
            ClassificationModel,
            DetectionModel,
            OBBModel,
            PoseModel,
            SegmentationModel,
        )

        torch.serialization.add_safe_globals(
            [DetectionModel, SegmentationModel, ClassificationModel, PoseModel, OBBModel]
        )
    except Exception:
        pass


_patch_torch_for_ultralytics()

ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.0015787"))
WEAPON_CONF_THRESHOLD = float(os.getenv("WEAPON_CONF_THRESHOLD", "0.4"))
HUMAN_CONF_THRESHOLD = float(os.getenv("HUMAN_CONF_THRESHOLD", "0.3"))
KNIFE_CONF_THRESHOLD = float(os.getenv("KNIFE_CONF_THRESHOLD", "0.15"))
API_KEY = os.getenv("SECURITY_API_KEY", "")

DETECTION_MODEL_PATH = os.getenv("DETECTION_MODEL_PATH", "models/detection_model.pt")
if not os.path.exists(DETECTION_MODEL_PATH):
    DETECTION_MODEL_PATH = os.getenv("FALLBACK_DETECTION_MODEL_PATH", "models/yolov8_weapon.pt")

ANOMALY_MODEL_PATH = os.getenv("ANOMALY_MODEL_PATH", "models/autoencoder_ucsd.keras")
HUMAN_MODEL_PATH = os.getenv("HUMAN_MODEL_PATH", "models/yolov8n.pt")
KNIFE_MODEL_PATH = os.getenv("KNIFE_MODEL_PATH", "models/yolov8s.pt")
CAMERA_STREAM_URL = os.getenv("CAMERA_STREAM_URL", "http://127.0.0.1:8000/stream")
SAVE_DIR = os.getenv("SAVE_DIR", "saved_events")
os.makedirs(SAVE_DIR, exist_ok=True)

if not os.path.exists(DETECTION_MODEL_PATH):
    raise RuntimeError(f"Modèle de détection introuvable: {DETECTION_MODEL_PATH}")
if not os.path.exists(ANOMALY_MODEL_PATH):
    raise RuntimeError(f"Modèle d'anomalie introuvable: {ANOMALY_MODEL_PATH}")


app = FastAPI(title="Security AI API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en production mets ton domaine
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _load_yolo_model(path: str, model_name: str) -> Optional[YOLO]:
    if not os.path.exists(path):
        print(f"[WARN] {model_name} absent ({path}). Détection désactivée.")
        return None
    try:
        return YOLO(path)
    except Exception as exc:
        raise RuntimeError(
            f"Impossible de charger {model_name}: {path}. "
            "Si vous utilisez PyTorch 2.6+, installez torch==2.5.1 (ou <2.6)."
        ) from exc


weapon_model = _load_yolo_model(DETECTION_MODEL_PATH, "modèle de détection")
anomaly_model = load_model(ANOMALY_MODEL_PATH, compile=False)
human_model = _load_yolo_model(HUMAN_MODEL_PATH, "modèle humain")
knife_model = _load_yolo_model(KNIFE_MODEL_PATH, "modèle couteau")

stats = {
    "total_frames": 0,
    "total_weapons": 0,
    "total_anomalies": 0,
    "critical_events": 0,
    "total_humans": 0,
}

event_history: List[Dict[str, Any]] = []


def _check_api_key(x_api_key: Optional[str]) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _compute_anomaly_score(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (128, 128)).astype("float32") / 255.0
    input_img = resized.reshape(1, 128, 128, 1)
    reconstructed = anomaly_model.predict(input_img, verbose=0)
    return float(np.mean((input_img - reconstructed) ** 2))


def _extract_detections(results: Any, target_class_name: Optional[str] = None) -> List[Dict[str, Any]]:
    detections: List[Dict[str, Any]] = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            class_name = result.names.get(cls_id, str(cls_id))
            if target_class_name and class_name.lower() != target_class_name.lower():
                continue
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            detections.append(
                {
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                }
            )
    return detections


def _detect_weapons(frame: np.ndarray) -> List[Dict[str, Any]]:
    if weapon_model is None:
        return []
    return _extract_detections(weapon_model(frame, conf=WEAPON_CONF_THRESHOLD))


def _detect_humans(frame: np.ndarray) -> List[Dict[str, Any]]:
    if human_model is None:
        return []
    return _extract_detections(human_model(frame, conf=HUMAN_CONF_THRESHOLD), target_class_name="person")


def _detect_knives(frame: np.ndarray) -> List[Dict[str, Any]]:
    if knife_model is None:
        return []
    detections = _extract_detections(knife_model(frame, conf=KNIFE_CONF_THRESHOLD), target_class_name="knife")
    for detection in detections:
        detection["risk_weight"] = 5
    return detections


def _risk_level(weapon_detected: bool, anomaly_detected: bool, human_detected: bool) -> str:
    if human_detected and weapon_detected:
        return "critical"
    if human_detected:
        return "human_intrusion"
    if weapon_detected:
        return "dangerous_object"
    if anomaly_detected:
        return "anomaly"
    return "normal"


def _alert_actions(risk_level: str) -> Dict[str, Any]:
    if risk_level == "critical":
        return {"threat_detected": True, "buzzer_on": True, "display_message": "ALERTE ROUGE"}
    if risk_level == "human_intrusion":
        return {"threat_detected": True, "buzzer_on": True, "display_message": "ALERTE HUMAIN"}
    if risk_level in {"dangerous_object", "anomaly"}:
        return {"threat_detected": True, "buzzer_on": True, "display_message": "ALERTE"}
    return {"threat_detected": False, "buzzer_on": False, "display_message": "Affichage normal"}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "detection_model": DETECTION_MODEL_PATH,
        "anomaly_model": ANOMALY_MODEL_PATH,
        "human_model_enabled": human_model is not None,
        "knife_model_enabled": knife_model is not None,
    }


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return """
    <html><head><title>Security AI Dashboard</title>
    <style>body{font-family:Arial;background:#111;color:white;text-align:center}.card{background:#222;padding:20px;margin:10px;border-radius:10px;display:inline-block}h1{color:#ff4444}</style>
    </head><body>
    <h1>🔥 Security AI Dashboard</h1>
    <div class="card">Total Frames: <span id="frames">0</span></div>
    <div class="card">Weapons: <span id="weapons">0</span></div>
    <div class="card">Anomalies: <span id="anomalies">0</span></div>
    <div class="card">Critical Events: <span id="critical">0</span></div>
    <div class="card">Humans: <span id="humans">0</span></div>
    <script>
      async function loadStats(){
        const res = await fetch('/stats');
        const data = await res.json();
        document.getElementById('frames').innerText = data.total_frames || 0;
        document.getElementById('weapons').innerText = data.total_weapons || 0;
        document.getElementById('anomalies').innerText = data.total_anomalies || 0;
        document.getElementById('critical').innerText = data.critical_events || 0;
        document.getElementById('humans').innerText = data.total_humans || 0;
      }
      setInterval(loadStats, 1000);
    </script></body></html>
    """


@app.get("/stats")
def get_stats() -> JSONResponse:
    return JSONResponse(content={k: int(v) for k, v in stats.items()})


@app.post("/analyze_frame")
async def analyze_frame(
    frame: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _check_api_key(x_api_key)

    raw = await frame.read()
    np_img = np.frombuffer(raw, np.uint8)
    decoded = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    if decoded is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    weapon_detections = _detect_weapons(decoded)
    knife_detections = _detect_knives(decoded)
    all_weapon_detections = weapon_detections + knife_detections
    human_detections = _detect_humans(decoded)
    anomaly_score = _compute_anomaly_score(decoded)

    weapon_detected = len(all_weapon_detections) > 0
    anomaly_detected = anomaly_score > ANOMALY_THRESHOLD
    human_detected = len(human_detections) > 0
    risk_level = _risk_level(weapon_detected, anomaly_detected, human_detected)

    stats["total_frames"] += 1
    if weapon_detected:
        stats["total_weapons"] += 1
    if anomaly_detected:
        stats["total_anomalies"] += 1
    if human_detected:
        stats["total_humans"] += 1
    if risk_level in {"critical", "human_intrusion"}:
        stats["critical_events"] += 1

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{SAVE_DIR}/{risk_level}_{timestamp}.jpg"
        for detection in all_weapon_detections + human_detections:
            x1, y1, x2, y2 = detection["bbox"]
            color = (0, 0, 255) if detection.get("class_name", "").lower() == "person" else (255, 0, 0)
            cv2.rectangle(decoded, (x1, y1), (x2, y2), color, 2)
        cv2.imwrite(filename, decoded)

    event_history.append(
        {
            "time": datetime.datetime.now().isoformat(),
            "risk_level": risk_level,
            "weapon_count": len(all_weapon_detections),
            "humans_detected": len(human_detections),
            "anomaly_score": anomaly_score,
        }
    )

    return {
        "weapon_detected": weapon_detected,
        "weapon_count": len(all_weapon_detections),
        "weapon_detections": all_weapon_detections,
        "anomaly_detected": anomaly_detected,
        "anomaly_score": anomaly_score,
        "human_detected": human_detected,
        "human_count": len(human_detections),
        "human_detections": human_detections,
        "risk_level": risk_level,
        **_alert_actions(risk_level),
    }


@app.post("/predict")
async def predict_legacy(frame: UploadFile = File(...), x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    return await analyze_frame(frame=frame, x_api_key=x_api_key)


@app.get("/camera_feed")
def camera_feed() -> Response:
    try:
        response = requests.get(CAMERA_STREAM_URL, stream=True, timeout=5)
        return StreamingResponse(response.raw, media_type="multipart/x-mixed-replace; boundary=frame")
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
