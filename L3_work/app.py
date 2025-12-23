import streamlit as st
import cv2
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image

# -------------------------------
# Configuration
# -------------------------------
IMG_SIZE = 128
model_path = "autoencoder_ucsd.keras"
autoencoder = load_model(model_path)

# -------------------------------
# Fonction de détection
# -------------------------------
def preprocess_image(image):
    img = image.convert('L')  # grayscale
    img = img.resize((IMG_SIZE, IMG_SIZE))
    img = np.array(img) / 255.0
    img = img.reshape(1, IMG_SIZE, IMG_SIZE, 1)
    return img

def predict_anomaly(img):
    recon = autoencoder.predict(img)
    mse = np.mean((img - recon)**2)
    threshold = 0.01  # Ajustable, ou utiliser la valeur de ton entraînement
    if mse > threshold:
        return "ANOMALIE", mse
    else:
        return "Normal", mse

# -------------------------------
# Interface Streamlit
# -------------------------------
st.title("Détection d'anomalies en temps réel")
st.write("Uploader une image ou utilisez la webcam (local).")

# Choix utilisateur
option = st.selectbox("Mode", ["Upload Image", "Webcam (Local)"])

if option == "Upload Image":
    uploaded_file = st.file_uploader("Choisissez une image...", type=["jpg","png","jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='Image chargée', use_column_width=True)
        
        img_input = preprocess_image(image)
        label, mse = predict_anomaly(img_input)
        st.write(f"Résultat: {label} | Erreur: {mse:.4f}")

elif option == "Webcam (Local)":
    st.write("Cliquez sur 'Start Webcam' pour capturer une image (local).")
    if st.button("Start Webcam"):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            # Convertir pour PIL
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            st.image(image, caption="Image capturée", use_column_width=True)
            
            img_input = preprocess_image(image)
            label, mse = predict_anomaly(img_input)
            st.write(f"Résultat: {label} | Erreur: {mse:.4f}")
