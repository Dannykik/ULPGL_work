# ===============================
# Fix OpenMP conflict
# ===============================
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ===============================
# Imports de base
# ===============================
import streamlit as st
import numpy as np
import base64
import tempfile
from tensorflow.keras.models import load_model

# ===============================
# Détection Streamlit Cloud
# ===============================
IS_CLOUD = os.environ.get("STREAMLIT_SERVER_RUNNING") == "true"

# ===============================
# Imports conditionnels
# ===============================
cv2 = None
YOLO = None

if not IS_CLOUD:
    import cv2
    from ultralytics import YOLO

# ===============================
# CONFIGURATION PAGE
# ===============================
st.set_page_config(
    page_title="Intelligent Video Surveillance System",
    page_icon="🛡️",
    layout="wide"
)

# ===============================
# BACKGROUND IMAGE
# ===============================
def get_base64_image(path):
    try:
        with open(path, "rb") as img:
            return base64.b64encode(img.read()).decode()
    except:
        return ""

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
    }}

    .main-container {{
        padding: 4rem;
        max-width: 900px;
        margin: auto;
    }}

    .title {{
        font-size: 42px;
        font-weight: 800;
        color: white;
    }}

    .subtitle {{
        font-size: 18px;
        color: #d1d5db;
    }}

    .badge {{
        background-color: rgba(59,130,246,0.2);
        color: #93c5fd;
        padding: 6px 16px;
        border-radius: 20px;
        margin-bottom: 20px;
        display: inline-block;
    }}

    .status-box {{
        background: rgba(0,0,0,0.55);
        padding: 20px;
        border-radius: 12px;
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
    anomaly_model = load_model("models/autoencoder_ucsd.h5", compile=False)

    weapon_model = None
    if not IS_CLOUD:
        weapon_model = YOLO("models/yolov8_weapon.pt")

    return weapon_model, anomaly_model

weapon_model, anomaly_model = load_models()

# ===============================
# SCORE D'ANOMALIE
# ===============================
def compute_anomaly_score(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (128, 128))
    norm = resized / 255.0
    inp = norm.reshape(1, 128, 128, 1)
    recon = anomaly_model.predict(inp, verbose=0)
    return np.mean((inp - recon) ** 2)

# ===============================
# INTERFACE
# ===============================
st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.markdown('<div class="badge">🛡️ Vidéosurveillance intelligente</div>', unsafe_allow_html=True)
st.markdown('<div class="title">AMANI KWETU – Intelligent Video Surveillance</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Sécurité – Région des Grands Lacs (Goma)</div>', unsafe_allow_html=True)

st.markdown("---")

# ===============================
# CHOIX SOURCE VIDÉO
# ===============================
video_source = st.selectbox(
    "🎥 Choisir la source vidéo",
    ["📁 Vidéo enregistrée", "📷 Webcam (temps réel)", "🌐 Caméra IP (RTSP)"]
)

uploaded_video = None
camera_url = None

if video_source == "📁 Vidéo enregistrée":
    uploaded_video = st.file_uploader(
        "Charger une vidéo",
        type=["mp4", "avi", "mov"]
    )

elif video_source == "🌐 Caméra IP (RTSP)":
    camera_url = st.text_input(
        "URL caméra IP",
        placeholder="rtsp://user:password@ip:port/stream"
    )

frame_placeholder = st.empty()
info_placeholder = st.empty()
stop_button = st.button("⛔ Arrêter la surveillance")

st.markdown('</div>', unsafe_allow_html=True)

# ===============================
# OUVERTURE SOURCE VIDÉO
# ===============================
cap = None

if video_source == "📁 Vidéo enregistrée" and uploaded_video:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_video.read())
    cap = cv2.VideoCapture(tfile.name)

elif video_source == "📷 Webcam (temps réel)":
    if IS_CLOUD:
        st.error("Webcam indisponible sur Streamlit Cloud.")
        st.stop()
    cap = cv2.VideoCapture(0)

elif video_source == "🌐 Caméra IP (RTSP)" and camera_url:
    cap = cv2.VideoCapture(camera_url)

if cap is None or not cap.isOpened():
    st.warning("Veuillez sélectionner une source vidéo valide.")
    st.stop()

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ===============================
# TRAITEMENT VIDÉO
# ===============================
while cap.isOpened():
    if stop_button:
        break

    ret, frame = cap.read()
    if not ret:
        break

    weapon_detected = False

    # ---------------------------
    # YOLO – Détection arme
    # ---------------------------
    if weapon_model:
        results = weapon_model(frame, conf=0.4)
        for r in results:
            for box in r.boxes:
                weapon_detected = True
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

    # ---------------------------
    # Anomalie
    # ---------------------------
    anomaly_score = compute_anomaly_score(frame)
    anomaly_detected = anomaly_score > 0.02

    # ---------------------------
    # Décision
    # ---------------------------
    if weapon_detected and anomaly_detected:
        status, color = "🔴 MENACE CRITIQUE", "red"
    elif weapon_detected:
        status, color = "🟠 OBJET DANGEREUX", "orange"
    elif anomaly_detected:
        status, color = "🟡 ANOMALIE", "yellow"
    else:
        status, color = "🟢 NORMAL", "lightgreen"

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_placeholder.image(frame_rgb, channels="RGB")

    info_placeholder.markdown(
        f"""
        <div class="status-box">
            <h3>📊 État du système</h3>
            <p><b>Statut :</b> <span style="color:{color}">{status}</span></p>
            <p><b>Score anomalie :</b> {anomaly_score:.5f}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

cap.release()
