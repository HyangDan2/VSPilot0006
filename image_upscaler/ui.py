from PySide6.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, QMessageBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from PIL import Image
from udir_image_upscaler.upscaler import Upscaler
import numpy as np
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDIR 이미지 업스케일러 - Apache 2.0")
        self.setGeometry(200, 200, 800, 600)

        self.label = QLabel("이미지를 선택하세요", alignment=Qt.AlignCenter)
        self.label.setFixedSize(640, 480)

        self.btn_open = QPushButton("📂 이미지 열기")
        self.btn_upscale = QPushButton("🚀 업스케일")
        self.btn_save = QPushButton("💾 저장")
        self.btn_upscale.setEnabled(False)
        self.btn_save.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.btn_open)
        layout.addWidget(self.btn_upscale)
        layout.addWidget(self.btn_save)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.image_path = None
        self.result_image = None
        self.upscaler = Upscaler()

        self.btn_open.clicked.connect(self.load_image)
        self.btn_upscale.clicked.connect(self.run_upscale)
        self.btn_save.clicked.connect(self.save_image)

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "이미지 선택", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.image_path = file
            pixmap = QPixmap(file)
            self.label.setPixmap(pixmap.scaled(self.label.size(), Qt.KeepAspectRatio))
            self.btn_upscale.setEnabled(True)
            self.btn_save.setEnabled(False)

    def run_upscale(self):
        if not self.image_path:
            return
        try:
            img = Image.open(self.image_path).convert("RGB")
            self.result_image = self.upscaler.upscale(img)
            # 미리보기 표시
            img_np = np.array(self.result_image)
            h, w, ch = img_np.shape
            qimg = QImage(img_np.data, w, h, ch * w, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(qimg).scaled(self.label.size(), Qt.KeepAspectRatio))
            self.btn_save.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"업스케일 실패: {e}")

    def save_image(self):
        if self.result_image is None:
            return
        file, _ = QFileDialog.getSaveFileName(self, "저장 위치", "", "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)")
        if file:
            self.result_image.save(file)
            QMessageBox.information(self, "성공", "이미지가 저장되었습니다.")
