from ultralytics import YOLO

model = YOLO(r"C:\Windows\System32\ULPGL_work\mon_travail\security_ai_app\models\yolov8n.pt")
metrics = model.val()

print(metrics)