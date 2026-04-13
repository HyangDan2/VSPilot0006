from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox, QVBoxLayout, QWidget

import cv2

from image_upscaler.face_detector import draw_face_boxes, get_face_boxes
from image_upscaler.image_display import ImageDisplay
from image_upscaler.image_processor import ImageProcessor
from image_upscaler.image_saver import ImageSaver
from upscalers import UPSCALER_OPTIONS, create_upscaler, default_upscaler_key
from upscalers.base import resize_frame


class UpscaleWorker(QObject):
    finished = Signal(object, object, object)
    failed = Signal(str)

    def __init__(self, processor, frame, boxes=None):
        super().__init__()
        self.processor = processor
        self.frame = frame
        self.boxes = boxes

    def run(self):
        try:
            self.finished.emit(self.processor.upscale(self.frame), self.frame, self.boxes)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Upscaler - Apache 2.0")
        self.setGeometry(100, 100, 1200, 740)

        self.upscaler_key = default_upscaler_key("image")
        self.startup_warning = None
        try:
            self.upscaler = create_upscaler(self.upscaler_key)
        except Exception as exc:
            self.startup_warning = f"RealESRGAN 준비 실패, OpenCV로 시작: {exc}"
            self.upscaler_key = "opencv_lanczos"
            self.upscaler = create_upscaler(self.upscaler_key)
        self.processor = ImageProcessor(self.upscaler)
        self.saver = ImageSaver()

        self.last_input_frame = None
        self.last_upscaled_frame = None
        self.camera_index = 0
        self.face_detection_enabled = True
        self.is_processing = False
        self.realtime_running = False
        self.dropped_frames = 0
        self.realtime_input_size = (640, 480)

        self.upscale_thread = None
        self.upscale_worker = None
        self.worker_is_realtime = False
        self.camera_capture = None
        self.realtime_timer = QTimer(self)
        self.realtime_timer.timeout.connect(self.update_realtime_frame)

        self.display = ImageDisplay()
        self.status_label = QLabel()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.display)
        main_layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.create_menus()
        self.update_status(self.startup_warning)
        self.update_action_state()

    def create_menus(self):
        self.actions = {}

        file_menu = self.menuBar().addMenu("파일")
        self.actions["open"] = self.add_menu_action(file_menu, "이미지 열기", self.load_from_file, "Ctrl+O")
        self.actions["save_original"] = self.add_menu_action(file_menu, "원본 저장", self.save_original)
        self.actions["save_upscaled"] = self.add_menu_action(file_menu, "결과 저장", self.save_upscaled)
        self.actions["save_all"] = self.add_menu_action(file_menu, "전체 저장", self.save_all, "Ctrl+S")
        file_menu.addSeparator()
        self.actions["exit"] = self.add_menu_action(file_menu, "종료", self.close, "Ctrl+Q")

        camera_menu = self.menuBar().addMenu("카메라")
        self.actions["capture"] = self.add_menu_action(camera_menu, "카메라 캡처", self.capture_from_camera)
        self.actions["realtime"] = self.add_menu_action(
            camera_menu,
            "Realtime 시작",
            self.toggle_realtime,
            "R",
            checkable=True,
        )
        camera_index_menu = camera_menu.addMenu("카메라 번호 선택")
        self.camera_action_group = QActionGroup(self)
        for index in range(4):
            action = QAction(str(index), self)
            action.setCheckable(True)
            action.setChecked(index == self.camera_index)
            action.triggered.connect(lambda checked=False, value=index: self.update_camera_index(value))
            self.camera_action_group.addAction(action)
            camera_index_menu.addAction(action)

        process_menu = self.menuBar().addMenu("처리")
        self.actions["upscale"] = self.add_menu_action(process_menu, "업스케일 실행", self.run_upscale, "Ctrl+U")
        self.actions["face_detection"] = self.add_menu_action(
            process_menu,
            "얼굴 감지",
            self.toggle_face_detection,
            "D",
            checkable=True,
        )
        self.actions["face_detection"].setChecked(self.face_detection_enabled)
        upscaler_menu = process_menu.addMenu("업스케일 방식")
        self.upscaler_action_group = QActionGroup(self)
        for option in UPSCALER_OPTIONS:
            action = QAction(option.label, self)
            action.setCheckable(True)
            action.setChecked(option.key == self.upscaler_key)
            action.triggered.connect(lambda checked=False, key=option.key: self.change_upscaler(key))
            self.upscaler_action_group.addAction(action)
            upscaler_menu.addAction(action)

        view_menu = self.menuBar().addMenu("보기")
        self.actions["show_status"] = self.add_menu_action(
            view_menu,
            "상태 표시",
            self.toggle_status,
            checkable=True,
        )
        self.actions["show_status"].setChecked(True)
        self.actions["show_compare"] = self.add_menu_action(
            view_menu,
            "원본/결과 비교 보기",
            self.toggle_compare_view,
            checkable=True,
        )
        self.actions["show_compare"].setChecked(True)

    def add_menu_action(self, menu, text, slot, shortcut=None, checkable=False):
        action = QAction(text, self)
        action.setCheckable(checkable)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(lambda checked=False: slot())
        menu.addAction(action)
        return action

    def capture_from_camera(self):
        if self.realtime_running:
            self.stop_realtime()
        self.display.show_message("촬영 중...\n잠깐만 기다려주세요.")
        QTimer.singleShot(800, self._open_and_capture_camera)

    def _open_and_capture_camera(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            QMessageBox.critical(self, "에러", "카메라를 열 수 없습니다!")
            self.update_status("카메라 열기 실패")
            return

        for _ in range(10):
            cap.read()
            cv2.waitKey(60)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            QMessageBox.warning(self, "경고", "프레임 캡처 실패")
            self.update_status("프레임 캡처 실패")
            return

        self.set_original_image(frame)

    def load_from_file(self):
        if self.realtime_running:
            self.stop_realtime()
        file_path, _ = QFileDialog.getOpenFileName(self, "이미지 파일 선택", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            frame = cv2.imread(file_path)
            if frame is None:
                QMessageBox.warning(self, "경고", "이미지를 불러올 수 없습니다.")
                return
            self.set_original_image(frame)

    def set_original_image(self, frame):
        self.last_input_frame = frame.copy()
        self.display.show_original(self.processor.detect_faces(frame, self.face_detection_enabled))
        self.display.clear_upscaled()
        self.last_upscaled_frame = None
        self.update_status("원본 준비 완료")
        self.update_action_state()

    def run_upscale(self):
        if self.realtime_running:
            self.stop_realtime()
        if self.last_input_frame is None:
            QMessageBox.information(self, "실행 불가", "먼저 원본 이미지를 불러오세요!")
            return
        if self.is_processing:
            return

        self.start_worker(self.last_input_frame.copy(), boxes=None, realtime=False)
        self.update_status("처리 중...")

    def start_realtime(self):
        if self.realtime_running:
            return
        if self.is_processing:
            QMessageBox.information(self, "실행 불가", "현재 업스케일 처리가 끝난 뒤 다시 실행하세요.")
            self.actions["realtime"].setChecked(False)
            return

        self.camera_capture = cv2.VideoCapture(self.camera_index)
        if not self.camera_capture.isOpened():
            self.camera_capture.release()
            self.camera_capture = None
            self.actions["realtime"].setChecked(False)
            QMessageBox.critical(self, "에러", "카메라를 열 수 없습니다!")
            self.update_status("카메라 열기 실패")
            return

        self.realtime_running = True
        self.dropped_frames = 0
        self.last_input_frame = None
        self.last_upscaled_frame = None
        self.display.clear_upscaled()
        self.realtime_timer.start(66)
        self.actions["realtime"].setText("Realtime 중지")
        self.actions["realtime"].setChecked(True)
        self.update_status("Realtime 실행 중")
        self.update_action_state()

    def stop_realtime(self):
        if not self.realtime_running:
            return
        self.realtime_timer.stop()
        self.realtime_running = False
        if self.camera_capture is not None:
            self.camera_capture.release()
            self.camera_capture = None
        self.actions["realtime"].setText("Realtime 시작")
        self.actions["realtime"].setChecked(False)
        self.update_status("Realtime 중지")
        self.update_action_state()

    def toggle_realtime(self):
        if self.realtime_running:
            self.stop_realtime()
        else:
            self.start_realtime()

    def update_realtime_frame(self):
        if self.camera_capture is None:
            self.stop_realtime()
            return

        ret, frame = self.camera_capture.read()
        if not ret or frame is None:
            self.update_status("Realtime 프레임 읽기 실패")
            return

        frame = resize_frame(frame, self.realtime_input_size)
        boxes = get_face_boxes(frame) if self.face_detection_enabled else []
        original = draw_face_boxes(frame.copy(), boxes) if self.face_detection_enabled else frame.copy()
        self.display.show_original(original)

        if self.is_processing:
            self.dropped_frames += 1
            return

        self.start_worker(frame.copy(), boxes=boxes, realtime=True)

    def start_worker(self, frame, boxes, realtime):
        self.is_processing = True
        self.worker_is_realtime = realtime
        self.set_processing(True)
        self.upscale_thread = QThread()
        self.upscale_worker = UpscaleWorker(self.processor, frame, boxes)
        self.upscale_worker.moveToThread(self.upscale_thread)
        self.upscale_thread.started.connect(self.upscale_worker.run)
        if realtime:
            self.upscale_worker.finished.connect(self.on_realtime_upscale_finished)
        else:
            self.upscale_worker.finished.connect(self.on_upscale_finished)
        self.upscale_worker.failed.connect(self.on_upscale_failed)
        self.upscale_worker.finished.connect(self.upscale_thread.quit)
        self.upscale_worker.failed.connect(self.upscale_thread.quit)
        self.upscale_thread.finished.connect(self.cleanup_upscale_worker)
        self.upscale_thread.start()

    def on_upscale_finished(self, result, original, boxes):
        self.last_upscaled_frame = result.image.copy()
        self.display.show_upscaled(self.processor.detect_faces(result.image, self.face_detection_enabled))
        in_h, in_w = original.shape[:2]
        out_h, out_w = result.image.shape[:2]
        self.update_status(
            f"{result.backend_name} | {result.device_name} | {result.elapsed_ms:.0f} ms | "
            f"{in_w}x{in_h} -> {out_w}x{out_h}"
        )

    def on_realtime_upscale_finished(self, result, original, boxes):
        output = result.image.copy()
        if self.face_detection_enabled:
            in_h, in_w = original.shape[:2]
            out_h, out_w = output.shape[:2]
            output = draw_face_boxes(output, boxes, scale_x=out_w / in_w, scale_y=out_h / in_h)
        self.display.show_upscaled(output)
        out_h, out_w = result.image.shape[:2]
        self.update_status(f"{result.elapsed_ms:.0f} ms | 출력 {out_w}x{out_h} | 드롭 {self.dropped_frames}")
        self.dropped_frames = 0

    def on_upscale_failed(self, message):
        if self.worker_is_realtime:
            self.stop_realtime()
            self.update_status(f"Realtime 업스케일 실패: {message}")
            return
        QMessageBox.warning(self, "업스케일 실패", message)
        self.update_status("업스케일 실패")

    def cleanup_upscale_worker(self):
        self.upscale_worker = None
        self.upscale_thread.deleteLater()
        self.upscale_thread = None
        self.is_processing = False
        self.worker_is_realtime = False
        self.set_processing(False)

    def save_original(self):
        if self.last_input_frame is None:
            QMessageBox.information(self, "저장 불가", "원본 이미지가 없습니다!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "원본 저장", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        self.saver.save_detected(path, self.last_input_frame, self.face_detection_enabled)
        QMessageBox.information(self, "저장 완료", f"원본 저장 완료: {path}")

    def save_upscaled(self):
        if self.last_upscaled_frame is None:
            QMessageBox.information(self, "저장 불가", "업스케일 이미지가 없습니다!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "업스케일 저장", "", "JPEG Image (*.jpg)")
        if not path:
            return
        if not path.lower().endswith(".jpg"):
            path += ".jpg"

        self.saver.save_detected(path, self.last_upscaled_frame, self.face_detection_enabled)
        QMessageBox.information(self, "저장 완료", f"업스케일 저장 완료: {path}")

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
        self.saver.save_all(base_path, self.last_input_frame, self.last_upscaled_frame, self.face_detection_enabled)
        if self.face_detection_enabled:
            message = (
                f"전체 저장 완료:\n{base_path}_original.jpg\n{base_path}_original_detected.jpg\n"
                f"{base_path}_upscaled.jpg\n{base_path}_upscaled_detected.jpg"
            )
        else:
            message = f"전체 저장 완료:\n{base_path}_original.jpg\n{base_path}_upscaled.jpg"
        QMessageBox.information(self, "저장 완료", message)

    def update_camera_index(self, camera_index):
        if self.realtime_running:
            self.stop_realtime()
        self.camera_index = int(camera_index)
        self.update_status(f"카메라 번호: {self.camera_index}")

    def change_upscaler(self, key):
        if key == self.upscaler_key:
            return
        if self.is_processing:
            self.reset_upscaler_action()
            QMessageBox.information(self, "실행 불가", "현재 업스케일 처리가 끝난 뒤 다시 변경하세요.")
            return
        if self.realtime_running:
            self.stop_realtime()

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
            self.reset_upscaler_action()
            QMessageBox.warning(self, "모델 준비 실패", str(exc))
        finally:
            self.set_processing(False)

    def toggle_face_detection(self):
        self.face_detection_enabled = self.actions["face_detection"].isChecked()
        self.refresh_display()
        state = "On" if self.face_detection_enabled else "Off"
        self.update_status(f"얼굴 감지 {state}")

    def toggle_status(self):
        self.status_label.setVisible(self.actions["show_status"].isChecked())

    def toggle_compare_view(self):
        self.display.setVisible(self.actions["show_compare"].isChecked())

    def refresh_display(self):
        if self.last_input_frame is not None:
            self.display.show_original(self.processor.detect_faces(self.last_input_frame, self.face_detection_enabled))
        if self.last_upscaled_frame is not None:
            self.display.show_upscaled(self.processor.detect_faces(self.last_upscaled_frame, self.face_detection_enabled))

    def update_status(self, message=None):
        backend = getattr(self.upscaler, "name", "Unknown")
        device = getattr(self.upscaler, "device_name", "CPU")
        text = message or "대기 중"
        mode = "Realtime" if self.realtime_running else "Image"
        face_state = "On" if self.face_detection_enabled else "Off"
        self.status_label.setText(f"{text} | 모드: {mode} | 얼굴 감지: {face_state} | 모델: {backend} | 장치: {device}")

    def update_action_state(self):
        has_original = self.last_input_frame is not None
        has_upscaled = self.last_upscaled_frame is not None
        self.actions["save_original"].setEnabled(has_original)
        self.actions["save_upscaled"].setEnabled(has_upscaled)
        self.actions["save_all"].setEnabled(has_original and has_upscaled)
        self.actions["upscale"].setEnabled(has_original and not self.realtime_running)

    def set_processing(self, is_processing):
        for key in ("open", "capture", "upscale"):
            self.actions[key].setEnabled(not is_processing)
        self.actions["realtime"].setEnabled(not is_processing or self.realtime_running)
        for action in self.upscaler_action_group.actions():
            action.setEnabled(not is_processing)
        if not is_processing:
            self.update_action_state()

    def reset_upscaler_action(self):
        for action in self.upscaler_action_group.actions():
            if action.text() == next(option.label for option in UPSCALER_OPTIONS if option.key == self.upscaler_key):
                action.setChecked(True)
                return

    def closeEvent(self, event):
        self.stop_realtime()
        event.accept()
