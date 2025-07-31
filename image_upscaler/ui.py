from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QFileDialog, QMessageBox
from PySide6.QtCore import QTimer
from image_upscaler.image_display import ImageDisplay
from image_upscaler.image_processor import ImageProcessor
from image_upscaler.image_saver import ImageSaver
from image_upscaler.button_panel import ButtonPanel
from image_upscaler.upscaler import Upscaler
import cv2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Upscaler - Apache 2.0")
        self.setGeometry(100, 100, 1200, 740)

        self.upscaler = Upscaler()
        self.processor = ImageProcessor(self.upscaler)
        self.saver = ImageSaver()
        self.last_input_frame = None
        self.last_upscaled_frame = None

        self.display = ImageDisplay()
        self.buttons = ButtonPanel({
            'camera': self.capture_from_camera,
            'load': self.load_from_file,
            'upscale': self.run_upscale,
            'save_original': self.save_original,
            'save_upscaled': self.save_upscaled,
            'save_all': self.save_all
        })

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.display)
        main_layout.addWidget(self.buttons)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def capture_from_camera(self):
        self.display.show_message("📸 촬영 중...\n잠깐만 기다려주세요!")
        QTimer.singleShot(800, self._open_and_capture_camera)

    def _open_and_capture_camera(self):
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            QMessageBox.critical(self, "에러", "카메라를 열 수 없습니다!")
            return

        for _ in range(10):
            cap.read()
            cv2.waitKey(60)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            QMessageBox.warning(self, "경고", "프레임 캡처 실패")
            return

        self.set_original_image(frame)

    def load_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "이미지 파일 선택", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            frame = cv2.imread(file_path)
            if frame is None:
                QMessageBox.warning(self, "경고", "이미지를 불러올 수 없습니다.")
                return
            self.set_original_image(frame)

    def set_original_image(self, frame):
        self.last_input_frame = frame.copy()
        detected = self.processor.detect_faces(frame.copy())
        self.display.show_original(detected)
        self.display.clear_upscaled()
        self.last_upscaled_frame = None

    def run_upscale(self):
        if self.last_input_frame is None:
            QMessageBox.information(self, "실행 불가", "먼저 원본 이미지를 불러오세요!")
            return

        upscaled = self.processor.upscale(self.last_input_frame)
        self.last_upscaled_frame = upscaled.copy()
        upscaled_detected = self.processor.detect_faces(upscaled)
        self.display.show_upscaled(upscaled_detected)

    def save_original(self):
        if self.last_input_frame is None:
            QMessageBox.information(self, "저장 불가", "원본 이미지가 없습니다!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "원본 저장", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        self.saver.save_detected(path, self.last_input_frame)
        QMessageBox.information(self, "저장 완료", f"✅ 원본 저장 완료: {path}")

    def save_upscaled(self):
        if self.last_upscaled_frame is None:
            QMessageBox.information(self, "저장 불가", "업스케일 이미지가 없습니다!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "업스케일 저장", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        self.saver.save_detected(path, self.last_upscaled_frame)
        QMessageBox.information(self, "저장 완료", f"✅ 업스케일 저장 완료: {path}")

    def save_all(self):
        if self.last_input_frame is None or self.last_upscaled_frame is None:
            QMessageBox.information(self, "저장 불가", "저장할 이미지가 없습니다!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "전체 저장", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        base_path = path.rsplit(".", 1)[0]
        self.saver.save_all(base_path, self.last_input_frame, self.last_upscaled_frame)

        QMessageBox.information(
            self,
            "저장 완료",
            f"✅ 전체 저장 완료:\n{base_path}_original.jpg\n{base_path}_original_detected.jpg\n{base_path}_upscaled.jpg\n{base_path}_upscaled_detected.jpg"
        )
