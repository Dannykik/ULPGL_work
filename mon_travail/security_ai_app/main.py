from fastapi import FastAPI, Request
import cv2
import numpy as np
from ultralytics import YOLO
from tensorflow.keras.models import load_model

app = FastAPI()

weapon_model = YOLO("models/yolov8_weapon.pt")
anomaly_model = load_model("models/autoencoder_ucsd.h5", compile=False)

@app.post("/predict")
async def predict(request: Request):
    data = await request.body()
    np_img = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    # Détection
    weapon = len(weapon_model(frame)[0].boxes) > 0

    # Anomalie
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (128, 128)) / 255.0
    input_img = resized.reshape(1,128,128,1)
    recon = anomaly_model.predict(input_img, verbose=0)
    mse = np.mean((input_img - recon)**2)

    if weapon and mse > 0.02:
        return "ALERTE"
    elif weapon or mse > 0.02:
        return "SUSPECT"
    else:
        return "NORMAL"
