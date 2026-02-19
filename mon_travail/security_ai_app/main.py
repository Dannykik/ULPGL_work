import os
from typing import Any, Dict, List, Optional

# Compat PyTorch 2.6+ (évite l'erreur weights_only=True par défaut)
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

import cv2
import numpy as np
import torch
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from tensorflow.keras.models import load_model
from ultralytics import YOLO

app = FastAPI(title="Security AI API", version="1.0.0")


def _patch_torch_for_ultralytics() -> None:
    """Compatibilité PyTorch 2.6+ pour charger des checkpoints YOLO legacy."""
    try:
        from ultralytics.nn.tasks import (
            DetectionModel,
            SegmentationModel,
            ClassificationModel,
            PoseModel,
            OBBModel,
        )

        torch.serialization.add_safe_globals(
            [DetectionModel, SegmentationModel, ClassificationModel, PoseModel, OBBModel]
        )
    except Exception:
        # Si l'API interne change selon version ultralytics, on continue avec le fallback existant.
        pass


_patch_torch_for_ultralytics()

ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.02"))
WEAPON_CONF_THRESHOLD = float(os.getenv("WEAPON_CONF_THRESHOLD", "0.4"))
API_KEY = os.getenv("SECURITY_API_KEY")
DETECTION_MODEL_PATH = os.getenv("DETECTION_MODEL_PATH", "models/detection_model.pt")
ANOMALY_MODEL_PATH = os.getenv("ANOMALY_MODEL_PATH", "models/autoencoder_ucsd.h5")

if not os.path.exists(DETECTION_MODEL_PATH):
    raise RuntimeError(f"Modèle de détection introuvable: {DETECTION_MODEL_PATH}")
if not os.path.exists(ANOMALY_MODEL_PATH):
    raise RuntimeError(f"Modèle d'anomalie introuvable: {ANOMALY_MODEL_PATH}")

try:
    weapon_model = YOLO(DETECTION_MODEL_PATH)
except Exception as exc:
    raise RuntimeError(
        f"Impossible de charger le modèle de détection: {DETECTION_MODEL_PATH}. "
        "Si vous utilisez PyTorch 2.6+, installez torch==2.5.1 (ou <2.6) "
        "et relancez."
    ) from exc

anomaly_model = load_model(ANOMALY_MODEL_PATH, compile=False)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _check_api_key(x_api_key: Optional[str]) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _compute_anomaly_score(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (128, 128)).astype("float32") / 255.0
    input_img = resized.reshape(1, 128, 128, 1)
    reconstructed = anomaly_model.predict(input_img, verbose=0)
    mse = float(np.mean((input_img - reconstructed) ** 2))
    return mse


def _detect_weapons(frame: np.ndarray) -> List[Dict[str, Any]]:
    detections: List[Dict[str, Any]] = []
    results = weapon_model(frame, conf=WEAPON_CONF_THRESHOLD)

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            detections.append(
                {
                    "class_id": cls_id,
                    "class_name": result.names.get(cls_id, str(cls_id)),
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                }
            )

    return detections


def _risk_level(weapon_detected: bool, anomaly_detected: bool) -> str:
    if weapon_detected and anomaly_detected:
        return "critical"
    if weapon_detected:
        return "dangerous_object"
    if anomaly_detected:
        return "anomaly"
    return "normal"


def _esp32_actions(risk_level: str) -> Dict[str, Any]:
    if risk_level == "critical":
        return {
            "threat_detected": True,
            "buzzer_on": True,
            "display_message": "ALERTE ROUGE",
        }
    if risk_level in {"dangerous_object", "anomaly"}:
        return {
            "threat_detected": True,
            "buzzer_on": True,
            "display_message": "ALERTE",
        }
    return {
        "threat_detected": False,
        "buzzer_on": False,
        "display_message": "Affichage normal",
    }


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
    anomaly_score = _compute_anomaly_score(decoded)

    weapon_detected = len(weapon_detections) > 0
    anomaly_detected = anomaly_score > ANOMALY_THRESHOLD

    risk_level = _risk_level(weapon_detected, anomaly_detected)
    esp32_actions = _esp32_actions(risk_level)

    return {
        "system_state": "surveillance_active",
        "weapon_detected": weapon_detected,
        "weapon_count": len(weapon_detections),
        "weapon_detections": weapon_detections,
        "anomaly_score": anomaly_score,
        "anomaly_threshold": ANOMALY_THRESHOLD,
        "anomaly_detected": anomaly_detected,
        "risk_level": risk_level,
        **esp32_actions,
    }


@app.post("/predict")
async def predict_legacy(frame: UploadFile = File(...), x_api_key: Optional[str] = Header(default=None)):
    return await analyze_frame(frame=frame, x_api_key=x_api_key)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
