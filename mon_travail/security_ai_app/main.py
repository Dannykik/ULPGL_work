import os
import datetime
from typing import Optional, Dict, Any, List
import cv2
import numpy as np
import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from tensorflow.keras.models import load_model
import keras
from ultralytics import YOLO

# =============================
# INITIALISATION
# =============================

keras.backend.clear_session()

ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.0015787"))
WEAPON_CONF_THRESHOLD = float(os.getenv("WEAPON_CONF_THRESHOLD", "0.4"))
API_KEY = "ma_cle_super_secrete"

weapon_model = YOLO("models/detection_model.pt")
anomaly_model = load_model("models/autoencoder_ucsd.keras", compile=False)

app = FastAPI(title="Security AI API", version="2.0.0")

# =============================
# STOCKAGE GLOBAL DES STATS
# =============================

SAVE_DIR = "saved_events"
os.makedirs(SAVE_DIR, exist_ok=True)

stats = {
    "total_frames": 0,
    "total_weapons": 0,
    "total_anomalies": 0,
    "critical_events": 0,
    "total_humans": 0
}

event_history: List[Dict[str, Any]] = []

# =============================
# HELPERS
# =============================

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
    detections = []
    results = weapon_model(frame, conf=WEAPON_CONF_THRESHOLD)

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            detections.append({
                "class_id": cls_id,
                "class_name": result.names.get(cls_id, str(cls_id)),
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
            })
    return detections
# =============================
# DETECTION HUMAINE SPECIFIQUE
# =============================

human_model = YOLO("yolov8n.pt")  # pré-entraîné COCO
def _detect_humans(frame: np.ndarray) -> List[Dict[str, Any]]:
    humans = []
    results = human_model(frame, conf=0.3)
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            class_name = result.names.get(cls_id, str(cls_id))
            if class_name.lower() == "person":
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                conf = float(box.conf[0])
                humans.append({
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })
    return humans

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

def _esp32_actions(risk_level: str) -> Dict[str, Any]:
    if risk_level == "critical":
        return {"threat_detected": True, "buzzer_on": True, "display_message": "ALERTE ROUGE"}
    if risk_level == "human_intrusion":
        return {"threat_detected": True, "buzzer_on": True, "display_message": "ALERTE HUMAIN"}
    if risk_level in {"dangerous_object", "anomaly"}:
        return {"threat_detected": True, "buzzer_on": True, "display_message": "ALERTE"}
    return {"threat_detected": False, "buzzer_on": False, "display_message": "Affichage normal"}

knife_model = YOLO("yolov8s.pt")  # modèle COCO
def _detect_knife(frame: np.ndarray) -> List[Dict[str, Any]]:
    detections = []

    results = knife_model(frame, conf=0.15)

    result = results[0]

    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        class_name = result.names.get(cls_id, str(cls_id))

        if class_name == "knife" and conf > 0.15:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

            detections.append({
                "class_id": cls_id,
                "class_name": "knife",
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
                "risk_weight": 5
            })

    return detections

# =============================
# DASHBOARD HTML
# =============================

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <html>
    <head>
        <title>Security AI Dashboard</title>
        <style>
    		body { font-family: Arial; background: #111; color: white; text-align:center; }
    		.card { background:#222; padding:20px; margin:10px; border-radius:10px; display:inline-block;}
    		h1 { color:#ff4444; }
    		h2 { color:#aaa; font-weight: normal; margin-top: -10px; }
	</style>
    </head>
    <body>
        <h1>🔥 Security AI Dashboard</h1>
	<h2> Travail de fin de cycle pour DK </h2>
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
        </script>
    </body>
    </html>
    """
@app.get("/stats")
def get_stats():
    # Conversion au cas où certains chiffres seraient numpy ou float
    json_stats = {k: int(v) if isinstance(v, (float,)) else v for k,v in stats.items()}
    return JSONResponse(content=json_stats)

# =============================
# ANALYSE PRINCIPALE
# =============================

SAVE_DIR = "saved_events"
os.makedirs(SAVE_DIR, exist_ok=True)

@app.post("/analyze_frame")
async def analyze_frame(
    frame: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None),
):
    _check_api_key(x_api_key)

    # Lecture et décodage de l'image
    raw = await frame.read()
    np_img = np.frombuffer(raw, np.uint8)
    decoded = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    if decoded is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # Détections
    weapon_detections = _detect_weapons(decoded)
    anomaly_score = _compute_anomaly_score(decoded)
    human_detections = _detect_humans(decoded)
    knife_detections = _detect_knife(decoded)
    all_weapon_detections = weapon_detections + knife_detections
    weapon_detected = len(all_weapon_detections) > 0

    anomaly_detected = anomaly_score > ANOMALY_THRESHOLD
    human_detected = len(human_detections) > 0

    # Mise à jour stats
    stats["total_frames"] += 1
    if weapon_detected:
    	stats["total_weapons"] += 1
    if anomaly_detected:
    	stats["total_anomalies"] += 1
    if human_detected:
    	stats["total_humans"] += 1

    # Définition du niveau de risque
    risk_level = _risk_level(weapon_detected, anomaly_detected, human_detected)

    # 🔥 Sauvegarde automatique des images critiques ou intrusion humaine
    if risk_level in {"critical", "human_intrusion"}:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{SAVE_DIR}/{risk_level}_{timestamp}.jpg"
        for det in weapon_detections + human_detections:
            x1, y1, x2, y2 = det["bbox"]
            # Rouge pour humain, bleu pour arme
            color = (0, 0, 255) if det.get("class_name", "") == "person" else (255, 0, 0)
            cv2.rectangle(decoded, (x1, y1), (x2, y2), color, 2)
        cv2.imwrite(filename, decoded)

    # Historique des événements pour dashboard
    event_history.append({
        "time": datetime.datetime.now().isoformat(),
        "risk_level": risk_level,
        "weapon_count": len(weapon_detections),
        "humans_detected": len(human_detections),
        "anomaly_score": anomaly_score
    })

    # Actions ESP32 (buzzer, écran)
    esp32_actions = _esp32_actions(risk_level)

    # Retour API
    return {
        "weapon_detected": weapon_detected,
        "anomaly_detected": anomaly_detected,
        "human_detected": human_detected,
        "risk_level": risk_level,
        "weapon_count": len(weapon_detections),
        "human_count": len(human_detections),
        "anomaly_score": anomaly_score,
        **esp32_actions
    }

# =============================
# CAMERA FEED
# =============================

ESP32_CAM_URL = "http://10.184.45.207:81/stream"

@app.get("/camera_feed")
def camera_feed():
    try:
        resp = requests.get(ESP32_CAM_URL, stream=True, timeout=5)
        return StreamingResponse(resp.raw, media_type="multipart/x-mixed-replace; boundary=frame")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
