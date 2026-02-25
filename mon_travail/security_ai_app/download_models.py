import os
import shutil
from ultralytics import YOLO

# Créer dossier models
os.makedirs("models", exist_ok=True)

print("Téléchargement de yolov8n...")
YOLO("yolov8n.pt")  # télécharge automatiquement

print("Téléchargement de yolov8s...")
YOLO("yolov8s.pt")  # télécharge automatiquement

# Déplacer les fichiers vers models/
if os.path.exists("yolov8n.pt"):
    shutil.move("yolov8n.pt", "models/yolov8n.pt")

if os.path.exists("yolov8s.pt"):
    shutil.move("yolov8s.pt", "models/yolov8s.pt")

print("✅ Modèles déplacés dans models/")