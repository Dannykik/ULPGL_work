# ===============================
# Fix OpenMP conflict (PyTorch + TensorFlow on Windows)
# ===============================
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ===============================
# Imports
# ===============================
import streamlit as st
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from tensorflow.keras.models import load_model
import base64

# ===============================
# CONFIGURATION PAGE
# ===============================
st.set_page_config(
    page_title="Intelligent Video Surveillance System",
    page_icon="🛡️",
    layout="wide"
)

# ===============================
# BACKGROUND IMAGE (CSS)
# ===============================
def get_base64_image(path):
    with open(path, "rb") as img:
        return base64.b64encode(img.read()).decode()

bg_image = get_base64_image("assets/background.png")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image:
            linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.85)),
            url("data:image/png;base64,{bg_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}

    .main-container {{
        padding: 4rem;
        max-width: 900px;
    }}

    .title {{
        font-size: 46px;
        font-weight: 800;
        color: white;
    }}

    .subtitle {{
        font-size: 20px;
        color: #d1d5db;
        margin-top: 12px;
        line-height: 1.6;
    }}

    .badge {{
        display: inline-block;
        background-color: rgba(59,130,246,0.2);
        color: #93c5fd;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 14px;
        margin-bottom: 20px;
    }}

    .status-box {{
        background: rgba(0,0,0,0.55);
        padding: 20px;
        border-radius: 12px;
        margin-top: 15px;
        color: white;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ===============================
# CHARGEMENT DES MODÈLES
# ===============================
@st.cache_resource
def load_models():
    weapon_model = YOLO("models/yolov8_weapon.pt")
    anomaly_model = load_model(
        "models/autoencoder_ucsd.h5",
        compile=False
    )
    return weapon_model, anomaly_model

weapon_model, anomaly_model = load_models()

# ===============================
# FONCTION SCORE D'ANOMALIE
# ===============================
def compute_anomaly_score(frame, model):
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_resized = cv2.resize(frame_gray, (128, 128))
    frame_norm = frame_resized / 255.0
    frame_input = frame_norm.reshape(1, 128, 128, 1)

    reconstructed = model.predict(frame_input, verbose=0)
    mse = np.mean((frame_input - reconstructed) ** 2)
    return mse

# ===============================
# INTERFACE PRINCIPALE
# ===============================
st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.markdown('<div class="badge">🛡️ Système de vidéosurveillance intelligente</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="title">Intelligent Video Surveillance System</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="subtitle">
        Université Libre des Pays des Grands Lacs (ULPGL)<br>
        Faculté des Sciences et Technologies<br>
        Projet académique – Mémoire L3
    </div>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)
with col1:
    start = st.button("▶️ Démarrer la surveillance")
with col2:
    stop = st.button("⛔ Arrêter")

frame_placeholder = st.empty()
info_placeholder = st.empty()

st.markdown('</div>', unsafe_allow_html=True)

# ===============================
# CAPTURE WEBCAM
# ===============================
IS_CLOUD = os.environ.get("STREAMLIT_SERVER_RUNNING") == "true"
if start and not IS_CLOUD:
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or stop:
            break

        # -------------------------
        # DÉTECTION OBJETS DANGEREUX
        # -------------------------
        results = weapon_model(frame, conf=0.4)
        weapon_detected = False

        for r in results:
            for box in r.boxes:
                weapon_detected = True
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(
                    frame,
                    "Objet Dangereux",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2
                )

        # -------------------------
        # DÉTECTION ANOMALIE
        # -------------------------
        anomaly_score = compute_anomaly_score(frame, anomaly_model)
        anomaly_detected = anomaly_score > 0.02

        # -------------------------
        # FUSION DES DÉCISIONS
        # -------------------------
        if weapon_detected and anomaly_detected:
            status = "🔴 MENACE CRITIQUE"
            color = "red"
        elif weapon_detected:
            status = "🟠 OBJET DANGEREUX DÉTECTÉ"
            color = "orange"
        elif anomaly_detected:
            status = "🟡 ANOMALIE COMPORTEMENTALE"
            color = "yellow"
        else:
            status = "🟢 SITUATION NORMALE"
            color = "lightgreen"

        # -------------------------
        # AFFICHAGE
        # -------------------------
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, channels="RGB")

        info_placeholder.markdown(
            f"""
            <div class="status-box">
                <h3>📊 État du système</h3>
                <p><b>Statut :</b> <span style="color:{color}; font-weight:bold">{status}</span></p>
                <p><b>Score anomalie :</b> {anomaly_score:.5f}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    cap.release()
    cv2.destroyAllWindows()
