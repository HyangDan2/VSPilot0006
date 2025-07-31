from PySide6.QtWidgets import (
    QMainWindow, QLabel, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QTimer

from realtime_upscaler.upscaler import Upscaler
from image_upscaler.image_processor import ImageProcessor
from image_upscaler.image_saver import ImageSaver

import cv2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDIR 업스케일러 - Apache 2.0")
        self.setGeometry(100, 100, 1200, 700)

        self.upscaler = Upscaler()
        self.processor = ImageProcessor(self.upscaler)
        self.saver = ImageSaver()
        self.last_input_frame = None
        self.last_upscaled_frame = None

        self.image_labels = [QLabel("원본 이미지"), QLabel("업스케일 이미지")]
        for label in self.image_labels:
            label.setFixedSize(560, 480)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_camera = QPushButton("\ud83d\udcf7 \uce74\uba54\ub77c \uce90\ud150")
        btn_camera.clicked.connect(self.capture_from_camera)

        btn_load = QPushButton("\ud83d\uddbc \uc774\ubbf8\uc9c0 \ubd88\ub7ec\uc624\uae30")
        btn_load.clicked.connect(self.load_from_file)

        btn_save_original = QPushButton("\ud83d\udcc2 \uc6d0\ubcf8 \uc800\uc7a5")
        btn_save_original.clicked.connect(self.save_original)

        btn_save_upscaled = QPushButton("\ud83d\udcc2 \uc5c5\uc2a4\ud398\uc77c \uc800\uc7a5")
        btn_save_upscaled.clicked.connect(self.save_upscaled)

        btn_save_all = QPushButton("\ud83d\udcc1 \uc804\uccb4 \uc800\uc7a5")
        btn_save_all.clicked.connect(self.save_all)

        image_layout = QHBoxLayout()
        for label in self.image_labels:
            image_layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_camera)
        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_save_original)
        btn_layout.addWidget(btn_save_upscaled)
        btn_layout.addWidget(btn_save_all)

        main_layout = QVBoxLayout()
        main_layout.addLayout(image_layout)
        main_layout.addLayout(btn_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def capture_from_camera(self):
        for label in self.image_labels:
            label.setText("\ud83d\udcf8 \uccad\uc0ac \uc911...\n\uc7a0\uac78\ub9b4\uae4c \uae30\ub2e4\ub824\uc8fc세요!")
            label.setStyleSheet("font-size: 20px; color: gray;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.repaint()

        QTimer.singleShot(800, self._open_and_capture_camera)

    def _open_and_capture_camera(self):
        cap = cv2.VideoCapture(1) # 0 for Iphone Camera, 1 for Mac Camera
        if not cap.isOpened():
            QMessageBox.critical(self, "\uc5d0\ub7ec", "\uce74\uba54\ub77c\ub97c \uc5f4 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4!")
            return

        for _ in range(10):
            cap.read()
            cv2.waitKey(60)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            QMessageBox.warning(self, "\uacbd\uace0", "\ud504\ub808\uc784 \uce90\ud150 \uc2e4\ud328")
            return

        self.process_image(frame)

    def load_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "\uc774\ubbf8\uc9c0 \ud30c\uc77c \uc120\ud0dd", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            frame = cv2.imread(file_path)
            if frame is None:
                QMessageBox.warning(self, "\uacbd\uace0", "\uc774\ubbf8\uc9c0\ub97c \ubd88\ub7ec\uc62c \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")
                return
            self.process_image(frame)

    def process_image(self, frame):
        self.last_input_frame = frame.copy()
        detected = self.processor.detect_faces(frame.copy())
        self.image_labels[0].setPixmap(self.convert_to_pixmap(detected))

        upscaled = self.processor.upscale(frame)
        self.last_upscaled_frame = upscaled.copy()
        upscaled_detected = self.processor.detect_faces(upscaled)
        self.image_labels[1].setPixmap(self.convert_to_pixmap(upscaled_detected))

    def save_original(self):
        if self.last_input_frame is None:
            QMessageBox.information(self, "\uc800\uc7a5 \ubd88\uac00", "\uc6d0\ubcf8 \uc774\ubbf8\uc9c0\uac00 \uc5c6\uc2b5\ub2c8\ub2e4!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "\uc6d0\ubcf8 \uc800\uc7a5", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        self.saver.save_detected(path, self.last_input_frame)
        QMessageBox.information(self, "\uc800\uc7a5 \uc644\ub8cc", f"\u2705 \uc6d0\ubcf8 \uc800\uc7a5 \uc644\ub8cc: {path}")

    def save_upscaled(self):
        if self.last_upscaled_frame is None:
            QMessageBox.information(self, "\uc800\uc7a5 \ubd88\uac00", "\uc5c5\uc2a4\ud398\uc77c \uc774\ubbf8\uc9c0\uac00 \uc5c6\uc2b5\ub2c8\ub2e4!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "\uc5c5\uc2a4\ud398\uc77c \uc800\uc7a5", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        self.saver.save_detected(path, self.last_upscaled_frame)
        QMessageBox.information(self, "\uc800\uc7a5 \uc644\ub8cc", f"\u2705 \uc5c5\uc2a4\ud398\uc77c \uc800\uc7a5 \uc644\ub8cc: {path}")

    def save_all(self):
        if self.last_input_frame is None or self.last_upscaled_frame is None:
            QMessageBox.information(self, "\uc800\uc7a5 \ubd88\uac00", "\uc800\uc7a5\ud560 \uc774\ubbf8\uc9c0\uac00 \uc5c6\uc2b5\ub2c8\ub2e4!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "\uc804\uccb4 \uc800\uc7a5", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        base_path = path.rsplit(".", 1)[0]
        self.saver.save_all(base_path, self.last_input_frame, self.last_upscaled_frame)

        QMessageBox.information(
            self,
            "\uc800\uc7a5 \uc644\ub8cc",
            f"\u2705 \uc804\uccb4 \uc800\uc7a5 \uc644\ub8cc:\n{base_path}_original.jpg\n{base_path}_original_detected.jpg\n{base_path}_upscaled.jpg\n{base_path}_upscaled_detected.jpg"
        )

    def convert_to_pixmap(self, img):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg).scaled(560, 480, Qt.AspectRatioMode.KeepAspectRatio)