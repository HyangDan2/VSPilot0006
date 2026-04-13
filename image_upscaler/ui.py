from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from image_upscaler.image_display import ImageDisplay
from image_upscaler.image_processor import ImageProcessor
from image_upscaler.image_saver import ImageSaver
from image_upscaler.button_panel import ButtonPanel
from upscalers import UPSCALER_OPTIONS, create_upscaler, default_upscaler_key
import cv2


class UpscaleWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(self, processor, frame):
        super().__init__()
        self.processor = processor
        self.frame = frame

    def run(self):
        try:
            self.finished.emit(self.processor.upscale(self.frame), self.frame)
        except Exception as exc:
            self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Upscaler - Apache 2.0")
        self.setGeometry(100, 100, 1200, 740)

        self.upscaler_key = default_upscaler_key("image")
        self.upscaler = create_upscaler(self.upscaler_key)
        self.processor = ImageProcessor(self.upscaler)
        self.saver = ImageSaver()
        self.last_input_frame = None
        self.last_upscaled_frame = None
        self.camera_index = 0
        self.upscale_thread = None
        self.upscale_worker = None

        self.display = ImageDisplay()
        self.buttons = ButtonPanel({
            'camera': self.capture_from_camera,
            'load': self.load_from_file,
            'upscale': self.run_upscale,
            'save_original': self.save_original,
            'save_upscaled': self.save_upscaled,
            'save_all': self.save_all
        })

        self.format_label = QLabel("카메라 번호 : 0")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["0", "1", "2", "3"]) 
        self.format_combo.currentTextChanged.connect(self.update_camera_index)
        self.upscaler_label = QLabel("업스케일 방식")
        self.upscaler_combo = QComboBox()
        for option in UPSCALER_OPTIONS:
            self.upscaler_combo.addItem(option.label, option.key)
        self.upscaler_combo.setCurrentIndex(
            max(0, self.upscaler_combo.findData(self.upscaler_key))
        )
        self.upscaler_combo.currentIndexChanged.connect(self.change_upscaler)
        self.status_label = QLabel()
        self.update_status()

        index_layout = QHBoxLayout()
        index_layout.addWidget(self.format_label)
        index_layout.addWidget(self.format_combo)
        index_layout.addWidget(self.upscaler_label)
        index_layout.addWidget(self.upscaler_combo)
        index_layout.addStretch(1)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.display)
        main_layout.addWidget(self.buttons)
        main_layout.addLayout(index_layout)
        main_layout.addWidget(self.status_label)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.update_button_state()

    def capture_from_camera(self):
        self.display.show_message("촬영 중...\n잠깐만 기다려주세요.")
        QTimer.singleShot(800, self._open_and_capture_camera)

    def _open_and_capture_camera(self):
        cap = cv2.VideoCapture(self.camera_index)
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
        self.update_status("원본 준비 완료")
        self.update_button_state()

    def run_upscale(self):
        if self.last_input_frame is None:
            QMessageBox.information(self, "실행 불가", "먼저 원본 이미지를 불러오세요!")
            return
        if self.upscale_thread is not None:
            return

        self.set_processing(True)
        self.update_status("처리 중...")
        self.upscale_thread = QThread()
        self.upscale_worker = UpscaleWorker(self.processor, self.last_input_frame.copy())
        self.upscale_worker.moveToThread(self.upscale_thread)
        self.upscale_thread.started.connect(self.upscale_worker.run)
        self.upscale_worker.finished.connect(self.on_upscale_finished)
        self.upscale_worker.failed.connect(self.on_upscale_failed)
        self.upscale_worker.finished.connect(self.upscale_thread.quit)
        self.upscale_worker.failed.connect(self.upscale_thread.quit)
        self.upscale_thread.finished.connect(self.cleanup_upscale_worker)
        self.upscale_thread.start()

    def on_upscale_finished(self, result, original):
        self.last_upscaled_frame = result.image.copy()
        upscaled_detected = self.processor.detect_faces(result.image)
        self.display.show_upscaled(upscaled_detected)
        in_h, in_w = original.shape[:2]
        out_h, out_w = result.image.shape[:2]
        self.update_status(
            f"{result.backend_name} | {result.device_name} | {result.elapsed_ms:.0f} ms | "
            f"{in_w}x{in_h} -> {out_w}x{out_h}"
        )
        self.set_processing(False)

    def on_upscale_failed(self, message):
        QMessageBox.warning(self, "업스케일 실패", message)
        self.update_status("업스케일 실패")
        self.set_processing(False)

    def cleanup_upscale_worker(self):
        self.upscale_worker = None
        self.upscale_thread.deleteLater()
        self.upscale_thread = None
        self.update_button_state()

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

    def update_camera_index(self, camera_index):
        self.camera_index = int(camera_index)
        self.format_label.setText(f"카메라 번호 : {self.camera_index}")

    def change_upscaler(self):
        key = self.upscaler_combo.currentData()
        if key == self.upscaler_key:
            return
        self.set_processing(True)
        self.update_status("모델 준비 중...")
        previous_key = self.upscaler_key
        previous_upscaler = self.upscaler
        try:
            self.upscaler_key = key
            self.upscaler = create_upscaler(key)
            self.processor = ImageProcessor(self.upscaler)
            self.update_status("업스케일 방식 변경 완료")
        except Exception as exc:
            self.upscaler_key = previous_key
            self.upscaler = previous_upscaler
            self.processor = ImageProcessor(self.upscaler)
            QMessageBox.warning(self, "모델 준비 실패", str(exc))
            self.upscaler_combo.setCurrentIndex(
                max(0, self.upscaler_combo.findData(self.upscaler_key))
            )
        finally:
            self.set_processing(False)

    def update_status(self, message=None):
        backend = getattr(self.upscaler, "name", "Unknown")
        device = getattr(self.upscaler, "device_name", "CPU")
        text = message or "대기 중"
        self.status_label.setText(f"{text} | 모델: {backend} | 장치: {device}")

    def update_button_state(self):
        self.buttons.set_save_enabled(
            self.last_input_frame is not None,
            self.last_upscaled_frame is not None,
        )

    def set_processing(self, is_processing):
        self.buttons.set_processing(is_processing)
        self.upscaler_combo.setEnabled(not is_processing)
        self.format_combo.setEnabled(not is_processing)
        if not is_processing:
            self.update_button_state()
