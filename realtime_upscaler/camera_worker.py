import cv2

cap = cv2.VideoCapture(1)

def get_camera_frame():
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    if not ret:
        return None
    return frame

def release_camera():
    if cap.isOpened():
        cap.release()
