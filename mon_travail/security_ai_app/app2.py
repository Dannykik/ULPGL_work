import gradio as gr
import cv2
import numpy as np
from ultralytics import YOLO
from tensorflow.keras.models import load_model



# =========================
# LOAD MODELS
# =========================
weapon_model = YOLO("models/yolov8_weapon.pt")
anomaly_model = load_model("models/autoencoder_ucsd.h5", compile=False)

# =========================
# ANOMALY SCORE
# =========================
def compute_anomaly_score(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (128, 128))
    norm = resized / 255.0
    inp = norm.reshape(1, 128, 128, 1)
    recon = anomaly_model.predict(inp, verbose=0)
    return np.mean((inp - recon) ** 2)

# =========================
# VIDEO PROCESSING
# =========================
def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # YOLO detection
        results = weapon_model(frame, conf=0.4)
        weapon_detected = len(results[0].boxes) > 0

        # Anomaly detection
        score = compute_anomaly_score(frame)
        anomaly_detected = score > 0.02

        # Fusion
        if weapon_detected and anomaly_detected:
            label = "MENACE CRITIQUE"
            color = (0, 0, 255)
        elif weapon_detected:
            label = "OBJET DANGEREUX"
            color = (0, 165, 255)
        elif anomaly_detected:
            label = "ANOMALIE"
            color = (0, 255, 255)
        else:
            label = "NORMAL"
            color = (0, 255, 0)

        cv2.putText(
            frame, label, (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2
        )

        frames.append(frame)

    cap.release()
    return frames[-1]  # dernière frame annotée

# =========================
# GRADIO UI
# =========================
custom_css = """
body {
    background: linear-gradient(135deg, #0f172a, #020617);
    color: white;
}
h1, h2, h3 {
    color: #e5e7eb;
}
.alert-critical {
    color: #dc2626;
    font-weight: bold;
}
.alert-warning {
    color: #f59e0b;
    font-weight: bold;
}
.alert-normal {
    color: #22c55e;
    font-weight: bold;
}
"""

with gr.Blocks(css=custom_css) as demo:

    gr.HTML("""
    <div style="text-align:center;">
        <h1>🛡️ Intelligent Video Surveillance System</h1>
        <h3>Protection de la region des Grands Lacs (Goma)</h3>
        <p>
            AMANI KWETU<br>
            <b>Goma</b>
        </p>
        <hr>
    </div>
    """)

    with gr.Row():
        with gr.Column():
            video_input = gr.Video(label="📹 Charger une vidéo de surveillance")
            run_btn = gr.Button("▶️ Lancer l’analyse", variant="primary")

        with gr.Column():
            output_image = gr.Image(label="📊 Résultat d’analyse")
            status_box = gr.Markdown()

    def wrapper(video):
        result = process_video(video)
        return result, "Analyse terminée ✅"

    run_btn.click(
        fn=process_video,
        inputs=video_input,
        outputs=output_image
    )

demo.launch()