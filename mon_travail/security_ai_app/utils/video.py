import cv2

def get_webcam():
    cap = cv2.VideoCapture(0)
    return cap
