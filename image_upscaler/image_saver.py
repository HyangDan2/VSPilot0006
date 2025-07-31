import cv2
from realtime_upscaler.face_detector import detect_faces

class ImageSaver:
    def save(self, path, image):
        cv2.imwrite(path, image)

    def save_detected(self, path, image):
        detected = detect_faces(image.copy())
        cv2.imwrite(path, detected)

    def save_all(self, base_path, original, upscaled):
        self.save(base_path + "_original.jpg", original)
        self.save_detected(base_path + "_original_detected.jpg", original)
        self.save(base_path + "_upscaled.jpg", upscaled)
        self.save_detected(base_path + "_upscaled_detected.jpg", upscaled)