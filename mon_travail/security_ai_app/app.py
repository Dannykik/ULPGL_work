import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
from utils.anomaly import load_anomaly_model, predict_anomaly
from utils.alert import risk_decision

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Intelligent Security System", layout="wide")

# ---------------- SIDEBAR ----------------
st.sidebar.image("assets/logo.png", width=150)
st.sidebar.title("AI Security System")
st.sidebar.markdown("**Surveillance intelligente temps réel**")

# ---------------- LOAD MODELS ----------------
@st.cache_resource
def load_models():
    yolo = YOLO("models/yolov8_weapon.pt")
    anomaly_model = load_anomaly_model("models/autoencoder_ucsd.h5")
    return yolo, anomaly_model

yolo_model, anomaly_model = load_models()

# ---------------- MAIN UI ----------------
st.title("🔐 Système Intelligent de Détection de Menaces")
st.markdown("**Fusion : Détection d’objets dangereux + Anomalies comportementales**")

col1, col2 = st.columns(2)
frame_window = col1.image([], channels="BGR")
status_box = col2.empty()

# ---------------- VIDEO LOOP ----------------
cap = cv2.VideoCapture(0)
frames_buffer = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # YOLO detection
    results = yolo_model(frame, conf=0.4, verbose=False)
    detected_objects = []

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            label = yolo_model.names[cls]
            detected_objects.append(label)

    # Buffer pour anomalie
    frames_buffer.append(cv2.resize(frame, (224, 224)))
    if len(frames_buffer) > 16:
        frames_buffer.pop(0)

    anomaly_score = 0.0
    if len(frames_buffer) == 16:
        anomaly_score = predict_anomaly(anomaly_model, frames_buffer)

    risk, icon = risk_decision(anomaly_score, detected_objects)

    # UI update
    frame_window.image(frame)
    status_box.markdown(f"""
    ### {icon} État du système
    - **Risque** : `{risk}`
    - **Score anomalie** : `{anomaly_score:.2f}`
    - **Objets détectés** : `{detected_objects}`
    """)

    if risk == "MENACE CRITIQUE":
        st.error("🚨 ALERTE ENVOYÉE AU CENTRE DE CONTRÔLE")

cap.release()
