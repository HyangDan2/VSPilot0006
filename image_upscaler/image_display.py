from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt
import cv2

class ImageDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.labels = [QLabel("원본 이미지"), QLabel("업스케일 이미지")]
        layout = QHBoxLayout()
        for label in self.labels:
            label.setFixedSize(560, 480)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        self.setLayout(layout)

    def show_original(self, image):
        self.labels[0].setPixmap(self.to_pixmap(image))

    def show_upscaled(self, image):
        self.labels[1].setPixmap(self.to_pixmap(image))

    def clear_upscaled(self):
        self.labels[1].clear()

    def show_message(self, message):
        for label in self.labels:
            label.setText(message)
            label.setStyleSheet("font-size: 20px; color: gray;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.repaint()

    def to_pixmap(self, img):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg).scaled(560, 480, Qt.AspectRatioMode.KeepAspectRatio)
