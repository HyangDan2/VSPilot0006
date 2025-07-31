from image_upscaler.face_detector import detect_faces
from PIL import Image
import cv2
import numpy as np

class ImageProcessor:
    def __init__(self, upscaler):
        self.upscaler = upscaler

    def detect_faces(self, frame):
        return detect_faces(frame.copy())

    def upscale(self, frame):
        pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        sr_img = self.upscaler.upscale(pil)
        return cv2.cvtColor(np.array(sr_img), cv2.COLOR_RGB2BGR)