from PySide6.QtWidgets import QMainWindow, QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap
from realtime_upscaler.camera_worker import get_camera_frame
from realtime_upscaler.face_detector import detect_faces
from realtime_upscaler.upscaler import Upscaler
import cv2
import numpy as np
from PIL import Image

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Realtime Upscaler - Apache 2.0")
        self.setGeometry(100, 100, 1200, 600)

        self.image_labels = [QLabel(), QLabel()]
        for label in self.image_labels:
            label.setFixedSize(560, 480)

        layout = QHBoxLayout()
        for label in self.image_labels:
            layout.addWidget(label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.upscaler = Upscaler()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(66)  # ~15fps

    def update_frame(self):
        frame = get_camera_frame()
        if frame is None:
            return

        frame_detected = detect_faces(frame.copy())
        qimg_orig = self.convert_to_qimage(frame_detected)
        self.image_labels[0].setPixmap(QPixmap.fromImage(qimg_orig).scaled(self.image_labels[0].size()))

        pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        sr_img = self.upscaler.upscale(pil)
        sr_np = cv2.cvtColor(np.array(sr_img), cv2.COLOR_RGB2BGR)
        sr_detected = detect_faces(sr_np)
        qimg_sr = self.convert_to_qimage(sr_detected)
        self.image_labels[1].setPixmap(QPixmap.fromImage(qimg_sr).scaled(self.image_labels[1].size()))

    def convert_to_qimage(self, img):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)

    def closeEvent(self, event):
        from realtime_upscaler.camera_worker import release_camera
        release_camera()
