from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from realtime_upscaler.camera_worker import get_camera_frame
from realtime_upscaler.face_detector import draw_face_boxes, get_face_boxes
from upscalers import UPSCALER_OPTIONS, create_upscaler, default_upscaler_key
from upscalers.base import resize_frame
import cv2


class RealtimeUpscaleWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(self, upscaler, frame, boxes):
        super().__init__()
        self.upscaler = upscaler
        self.frame = frame
        self.boxes = boxes

    def run(self):
        try:
            self.finished.emit(self.upscaler.upscale(self.frame), self.boxes)
        except Exception as exc:
            self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Realtime Upscaler - Apache 2.0")
        self.setGeometry(100, 100, 1200, 600)

        self.image_labels = [QLabel(), QLabel()]
        for label in self.image_labels:
            label.setFixedSize(560, 480)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        image_layout = QHBoxLayout()
        for label in self.image_labels:
            image_layout.addWidget(label)

        self.upscaler_key = default_upscaler_key("realtime")
        self.upscaler = create_upscaler(self.upscaler_key)
        self.is_processing = False
        self.worker_thread = None
        self.worker = None
        self.dropped_frames = 0
        self.input_size = (640, 480)

        self.upscaler_combo = QComboBox()
        for option in UPSCALER_OPTIONS:
            self.upscaler_combo.addItem(option.label, option.key)
        self.upscaler_combo.setCurrentIndex(
            max(0, self.upscaler_combo.findData(self.upscaler_key))
        )
        self.upscaler_combo.currentIndexChanged.connect(self.change_upscaler)
        self.status_label = QLabel()
        self.update_status()

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("업스케일 방식"))
        controls_layout.addWidget(self.upscaler_combo)
        controls_layout.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(image_layout)
        layout.addLayout(controls_layout)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(66)  # ~15fps

    def update_frame(self):
        frame = get_camera_frame()
        if frame is None:
            return

        frame = resize_frame(frame, self.input_size)
        boxes = get_face_boxes(frame)
        frame_detected = draw_face_boxes(frame.copy(), boxes)
        qimg_orig = self.convert_to_qimage(frame_detected)
        self.image_labels[0].setPixmap(QPixmap.fromImage(qimg_orig).scaled(self.image_labels[0].size()))

        if self.is_processing:
            self.dropped_frames += 1
            return

        self.is_processing = True
        self.worker_thread = QThread()
        self.worker = RealtimeUpscaleWorker(self.upscaler, frame.copy(), boxes)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_upscale_finished)
        self.worker.failed.connect(self.on_upscale_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.cleanup_worker)
        self.worker_thread.start()

    def on_upscale_finished(self, result, boxes):
        sr_detected = self.draw_scaled_boxes(result.image.copy(), boxes)
        qimg_sr = self.convert_to_qimage(sr_detected)
        self.image_labels[1].setPixmap(QPixmap.fromImage(qimg_sr).scaled(self.image_labels[1].size()))
        h, w = result.image.shape[:2]
        self.update_status(f"{result.elapsed_ms:.0f} ms | 출력 {w}x{h} | 드롭 {self.dropped_frames}")
        self.dropped_frames = 0

    def on_upscale_failed(self, message):
        self.update_status(f"업스케일 실패: {message}")

    def cleanup_worker(self):
        self.worker = None
        self.worker_thread.deleteLater()
        self.worker_thread = None
        self.is_processing = False

    def convert_to_qimage(self, img):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()

    def draw_scaled_boxes(self, img, boxes):
        return draw_face_boxes(img, boxes, scale=2)

    def change_upscaler(self):
        key = self.upscaler_combo.currentData()
        if key == self.upscaler_key:
            return
        if self.is_processing:
            self.upscaler_combo.setCurrentIndex(
                max(0, self.upscaler_combo.findData(self.upscaler_key))
            )
            return
        previous_key = self.upscaler_key
        try:
            self.upscaler_key = key
            self.upscaler = create_upscaler(key)
            self.update_status("업스케일 방식 변경 완료")
        except Exception as exc:
            self.upscaler_key = previous_key
            self.upscaler_combo.setCurrentIndex(
                max(0, self.upscaler_combo.findData(previous_key))
            )
            self.update_status(f"모델 준비 실패: {exc}")

    def update_status(self, message="대기 중"):
        backend = getattr(self.upscaler, "name", "Unknown")
        device = getattr(self.upscaler, "device_name", "CPU")
        self.status_label.setText(f"{message} | 모델: {backend} | 장치: {device}")

    def closeEvent(self, event):
        from realtime_upscaler.camera_worker import release_camera
        self.timer.stop()
        release_camera()
        event.accept()
