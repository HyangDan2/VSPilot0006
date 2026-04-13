import cv2
from image_upscaler.face_detector import detect_faces

class ImageSaver:
    def save(self, path, image):
        cv2.imwrite(path, image)

    def save_detected(self, path, image, face_detection_enabled=True):
        output = detect_faces(image.copy()) if face_detection_enabled else image
        cv2.imwrite(path, output)

    def save_all(self, base_path, original, upscaled, face_detection_enabled=True):
        self.save(base_path + "_original.jpg", original)
        self.save(base_path + "_upscaled.jpg", upscaled)
        if face_detection_enabled:
            self.save_detected(base_path + "_original_detected.jpg", original)
            self.save_detected(base_path + "_upscaled_detected.jpg", upscaled)
