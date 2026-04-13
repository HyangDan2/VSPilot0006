import cv2
import os

haar_path = os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(haar_path)

def get_face_boxes(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

def draw_face_boxes(image, faces, scale_x=1.0, scale_y=1.0):
    for (x, y, w, h) in faces:
        start = (round(x * scale_x), round(y * scale_y))
        end = (round((x + w) * scale_x), round((y + h) * scale_y))
        cv2.rectangle(image, start, end, (0, 255, 0), 2)
    return image

def detect_faces(image):
    return draw_face_boxes(image, get_face_boxes(image))
