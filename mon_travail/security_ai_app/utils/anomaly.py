import numpy as np
from tensorflow.keras.models import load_model

def load_anomaly_model(path):
    return load_model(path)

def preprocess_sequence(frames):
    frames = np.array(frames) / 255.0
    return np.expand_dims(frames, axis=0)  # (1, T, H, W, C)

def predict_anomaly(model, frames):
    x = preprocess_sequence(frames)
    recon = model.predict(x, verbose=0)
    mse = np.mean(np.square(x - recon))
    return float(mse)
