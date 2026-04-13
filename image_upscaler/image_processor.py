from image_upscaler.face_detector import detect_faces

class ImageProcessor:
    def __init__(self, upscaler):
        self.upscaler = upscaler

    def detect_faces(self, frame):
        return detect_faces(frame.copy())

    def upscale(self, frame):
        return self.upscaler.upscale(frame.copy())
