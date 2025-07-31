from PySide6.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QFileDialog, QMessageBox
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
        self.setGeometry(200, 200, 1200, 600)

        # QLabel 2개 (좌: 원본, 우: 업스케일 결과)
        self.label_orig = QLabel("원본 이미지", alignment=Qt.AlignCenter)
        self.label_upscaled = QLabel("업스케일 이미지", alignment=Qt.AlignCenter)
        for label in [self.label_orig, self.label_upscaled]:
            label.setFixedSize(540, 400)

        # 버튼
        self.btn_open = QPushButton("📂 이미지 열기")
        self.btn_upscale = QPushButton("🚀 업스케일")
        self.btn_save = QPushButton("💾 저장")
        self.btn_upscale.setEnabled(False)
        self.btn_save.setEnabled(False)

        # 레이아웃 구성
        image_layout = QHBoxLayout()
        image_layout.addWidget(self.label_orig)
        image_layout.addWidget(self.label_upscaled)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_open)
        button_layout.addWidget(self.btn_upscale)
        button_layout.addWidget(self.btn_save)

        main_layout = QVBoxLayout()
        main_layout.addLayout(image_layout)
        main_layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # 상태 변수
        self.image_path = None
        self.result_image = None
        self.upscaler = Upscaler()

        # 이벤트 연결
        self.btn_open.clicked.connect(self.load_image)
        self.btn_upscale.clicked.connect(self.run_upscale)
        self.btn_save.clicked.connect(self.save_image)

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "이미지 선택", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.image_path = file
            pixmap = QPixmap(file)
            self.label_orig.setPixmap(pixmap.scaled(self.label_orig.size(), Qt.KeepAspectRatio))
            self.label_upscaled.clear()
            self.btn_upscale.setEnabled(True)
            self.btn_save.setEnabled(False)

    def run_upscale(self):
        if not self.image_path:
            return
        try:
            img = Image.open(self.image_path).convert("RGB")
            self.result_image = self.upscaler.upscale(img)

            # 결과를 QPixmap으로 변환해서 표시
            img_np = np.array(self.result_image)
            h, w, ch = img_np.shape
            qimg = QImage(img_np.data, w, h, ch * w, QImage.Format_RGB888)
            self.label_upscaled.setPixmap(QPixmap.fromImage(qimg).scaled(
                self.label_upscaled.size(), Qt.KeepAspectRatio))
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
