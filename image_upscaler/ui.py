import time
from datetime import datetime
from pathlib import Path
import re
import sys

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSplitter,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_upscaler.config import AppConfig
from image_upscaler.image_display import ImageDisplay
from image_upscaler.image_io import (
    SUPPORTED_FORMATS,
    extension_for_path,
    image_filter,
    load_image,
    normalize_output_path,
)
from image_upscaler.image_processor import ImageProcessor
from image_upscaler.image_saver import ImageSaver
from image_upscaler.upscaler import Upscaler, detect_model_scale


APP_NAME = "HD2 Real ESRGAN Image Upscaler"
TILE_PROGRESS_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")


class ProgressOutputCapture:
    def __init__(self, progress_callback, stdout, stderr):
        self.progress_callback = progress_callback
        self.stdout = stdout
        self.stderr = stderr
        self.buffer = ""
        self.last_progress = None

    def write(self, text):
        self.stderr.write(text)
        self.stderr.flush()
        self.buffer = (self.buffer + text)[-4000:]
        matches = TILE_PROGRESS_PATTERN.findall(self.buffer)
        if not matches:
            return

        current, total = matches[-1]
        current = int(current)
        total = int(total)
        progress = (current, total)
        if total > 0 and progress != self.last_progress:
            self.last_progress = progress
            self.progress_callback(current, total)

    def flush(self):
        self.stderr.flush()

    def isatty(self):
        return False


class CaptureProgressOutput:
    def __init__(self, progress_callback):
        self.progress_callback = progress_callback
        self.stdout = None
        self.stderr = None
        self.capture = None

    def __enter__(self):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.capture = ProgressOutputCapture(self.progress_callback, self.stdout, self.stderr)
        sys.stdout = self.capture
        sys.stderr = self.capture
        return self.capture

    def __exit__(self, exc_type, exc, tb):
        sys.stdout = self.stdout
        sys.stderr = self.stderr


class UpscaleWorker(QObject):
    finished = Signal(object, float)
    failed = Signal(str)
    log = Signal(str)
    progress = Signal(int, int, float)

    def __init__(self, processor, image):
        super().__init__()
        self.processor = processor
        self.image = image

    @Slot()
    def run(self):
        started = time.perf_counter()
        try:
            self.log.emit("Upscale started")
            with CaptureProgressOutput(self._emit_progress):
                upscaled = self.processor.upscale(self.image, progress=self.log.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.finished.emit(upscaled, time.perf_counter() - started)

    def _emit_progress(self, current, total):
        percent = current / total * 100
        self.progress.emit(current, total, percent)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1280, 760)

        self.config = AppConfig()
        self.upscaler = Upscaler(self.config)
        self.processor = ImageProcessor(self.upscaler)
        self.saver = ImageSaver()
        self.original_image = None
        self.upscaled_image = None
        self.original_path = None
        self.upscale_thread = None
        self.upscale_worker = None
        self.last_progress_log_time = 0

        self.display = ImageDisplay()
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)
        self.log_view.setPlaceholderText("Upscale log")
        self.log_view.setVisible(bool(self.config.get("show_log", True)))

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.display)
        splitter.addWidget(self.log_view)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([620, 140])

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._build_menu()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("Ready")
        self._set_busy(False)
        self.append_log(f"{APP_NAME} ready")

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        view_menu = self.menuBar().addMenu("&View")
        model_menu = self.menuBar().addMenu("&Model")
        process_menu = self.menuBar().addMenu("&Process")

        load_action = QAction("&Load Image", self)
        load_action.setShortcuts([QKeySequence("L"), QKeySequence.StandardKey.Open])
        load_action.triggered.connect(self.load_from_file)
        file_menu.addAction(load_action)
        self.load_action = load_action

        save_original_action = QAction("Save &Original", self)
        save_original_action.triggered.connect(self.save_original)
        file_menu.addAction(save_original_action)
        self.save_original_action = save_original_action

        save_upscaled_action = QAction("&Save Upscaled", self)
        save_upscaled_action.setShortcuts([QKeySequence("S"), QKeySequence.StandardKey.Save])
        save_upscaled_action.triggered.connect(self.save_upscaled)
        file_menu.addAction(save_upscaled_action)
        self.save_upscaled_action = save_upscaled_action

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        show_log_action = QAction("Show &Log", self)
        show_log_action.setCheckable(True)
        show_log_action.setChecked(bool(self.config.get("show_log", True)))
        show_log_action.toggled.connect(self.toggle_log)
        view_menu.addAction(show_log_action)
        self.show_log_action = show_log_action

        clear_log_action = QAction("&Clear Log", self)
        clear_log_action.triggered.connect(self.clear_log)
        view_menu.addAction(clear_log_action)
        self.clear_log_action = clear_log_action

        model_action = QAction("Select .&pth Model", self)
        model_action.setShortcut(QKeySequence("O"))
        model_action.triggered.connect(self.select_model)
        model_menu.addAction(model_action)
        self.model_action = model_action

        run_action = QAction("&Run Upscale", self)
        run_action.setShortcut(QKeySequence("R"))
        run_action.triggered.connect(self.run_upscale)
        process_menu.addAction(run_action)
        self.run_action = run_action

        settings_action = QAction("Upscale &Settings", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        process_menu.addAction(settings_action)
        self.settings_action = settings_action

    def load_from_file(self):
        if self._is_upscaling():
            self.statusBar().showMessage("Wait for the current upscale to finish")
            return

        start_dir = self.config.get("last_open_dir") or str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Image",
            start_dir,
            image_filter(),
        )
        if not file_path:
            return

        try:
            image = load_image(file_path)
        except Exception as exc:
            self._show_error("Load failed", str(exc))
            return

        self.original_image = image
        self.upscaled_image = None
        self.original_path = Path(file_path)
        input_format = extension_for_path(file_path)
        self.config.update(
            last_open_dir=str(self.original_path.parent),
            input_format=input_format,
        )

        self.display.show_original(image)
        self.display.clear_upscaled()
        self.save_upscaled_action.setEnabled(False)
        self.statusBar().showMessage(f"Image loaded: {self.original_path.name}")
        self.append_log(f"Image loaded: {self.original_path.name}")

    def save_original(self):
        if self._is_upscaling():
            self.statusBar().showMessage("Wait for the current upscale to finish")
            return

        if self.original_image is None:
            self.statusBar().showMessage("No original image to save")
            QMessageBox.information(self, "Save Original", "Load an image first.")
            return

        self._save_image(self.original_image, "Save Original", self._default_save_name("_original"))

    def save_upscaled(self):
        if self._is_upscaling():
            self.statusBar().showMessage("Wait for the current upscale to finish")
            return

        if self.upscaled_image is None:
            self.statusBar().showMessage("No upscaled image to save")
            QMessageBox.information(self, "Save Upscaled", "Run upscale first.")
            return

        self._save_image(self.upscaled_image, "Save Upscaled", self._default_save_name("_upscaled"))

    def _save_image(self, image, title, default_name):
        path, _ = QFileDialog.getSaveFileName(
            self,
            title,
            default_name,
            image_filter("Image Files"),
        )
        if not path:
            return

        output_path, output_format = normalize_output_path(path, self.config.get("output_format"))
        try:
            self.saver.save(output_path, image)
        except Exception as exc:
            self._show_error("Save failed", str(exc))
            return

        self.config.update(
            last_save_dir=str(output_path.parent),
            output_format=output_format,
        )
        self.statusBar().showMessage(f"Saved: {output_path.name}")
        self.append_log(f"Saved: {output_path}")

    def _default_save_name(self, suffix):
        output_format = self.config.get("output_format", "png")
        save_dir = Path(self.config.get("last_save_dir") or self.config.get("last_open_dir") or Path.home())
        stem = self.original_path.stem if self.original_path else "image"
        return str(save_dir / f"{stem}{suffix}.{output_format}")

    def select_model(self):
        if self._is_upscaling():
            self.statusBar().showMessage("Wait for the current upscale to finish")
            return

        current_model = Path(self.config.get("model_path") or "weights").expanduser()
        start_dir = str(current_model.parent if current_model.parent.exists() else Path.home())
        model_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select RealESRGAN Model",
            start_dir,
            "PyTorch Model (*.pth);;All Files (*)",
        )
        if not model_path:
            return

        detected_scale = detect_model_scale(model_path, default=None)
        if detected_scale is None:
            scale = int(self.config.get("scale", 2))
            self.config.set("model_path", model_path)
            self.append_log(f"Model selected: {Path(model_path).name}")
            self.append_log(f"Model scale not detected; using configured default: x{scale}")
        else:
            self.config.update(model_path=model_path, scale=detected_scale)
            self.append_log(f"Model selected: {Path(model_path).name}")
            self.append_log(f"Detected model scale: x{detected_scale}")

        self.statusBar().showMessage(f"Model selected: {Path(model_path).name}")

    def run_upscale(self):
        if self._is_upscaling():
            self.statusBar().showMessage("Upscaling is already running")
            return

        if self.original_image is None:
            self.statusBar().showMessage("No image loaded")
            QMessageBox.information(self, "Run Upscale", "Load an image first.")
            return

        source_image, source_label = self._upscale_source()
        self.statusBar().showMessage("Upscaling...")
        self.append_log(f"Input source: {source_label}")
        self._set_busy(True)

        self.upscale_thread = QThread(self)
        self.upscale_worker = UpscaleWorker(self.processor, source_image.copy())
        self.upscale_worker.moveToThread(self.upscale_thread)
        self.upscale_thread.started.connect(self.upscale_worker.run)
        self.upscale_worker.log.connect(self.append_log)
        self.upscale_worker.progress.connect(self._on_upscale_progress)
        self.upscale_worker.finished.connect(self._on_upscale_finished)
        self.upscale_worker.failed.connect(self._on_upscale_failed)
        self.upscale_worker.finished.connect(self.upscale_thread.quit)
        self.upscale_worker.failed.connect(self.upscale_thread.quit)
        self.upscale_thread.finished.connect(self.upscale_worker.deleteLater)
        self.upscale_thread.finished.connect(self.upscale_thread.deleteLater)
        self.upscale_thread.finished.connect(self._clear_upscale_thread)
        self.upscale_thread.start()

    @Slot(object, float)
    def _on_upscale_finished(self, upscaled, elapsed):
        self.upscaled_image = upscaled
        self.display.show_upscaled(upscaled)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.statusBar().showMessage(f"Upscale complete: {elapsed:.2f}s")
        self.append_log(f"Upscale complete: {elapsed:.2f}s")
        self._set_busy(False)

    @Slot(str)
    def _on_upscale_failed(self, message):
        self._set_busy(False)
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.append_log(f"Upscale failed: {message}")
        self._show_error("Upscale failed", message)

    @Slot(int, int, float)
    def _on_upscale_progress(self, current, total, percent):
        value = max(0, min(100, int(percent)))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        self.statusBar().showMessage(f"Upscaling... {current}/{total} ({percent:.1f}%)")

        now = time.monotonic()
        if now - self.last_progress_log_time >= 0.5 or current >= total:
            self.last_progress_log_time = now
            self.append_log(f"Tile progress: {current}/{total} ({percent:.1f}%)")

    @Slot()
    def _clear_upscale_thread(self):
        self.upscale_thread = None
        self.upscale_worker = None

    def _is_upscaling(self):
        return self.upscale_thread is not None and self.upscale_thread.isRunning()

    def _set_busy(self, busy):
        self.run_action.setEnabled(not busy)
        self.load_action.setEnabled(not busy)
        self.save_original_action.setEnabled(not busy)
        self.save_upscaled_action.setEnabled(not busy and self.upscaled_image is not None)
        self.model_action.setEnabled(not busy)
        self.settings_action.setEnabled(not busy)
        if busy:
            self.last_progress_log_time = 0
            self.progress_bar.setRange(0, 0)
            self.progress_bar.show()
        else:
            self.progress_bar.setRange(0, 100)

    def _upscale_source(self):
        if self.config.get("chain_upscale", False) and self.upscaled_image is not None:
            return self.upscaled_image, "previous upscaled result"
        return self.original_image, "original image"

    def show_settings_dialog(self):
        if self._is_upscaling():
            self.statusBar().showMessage("Wait for the current upscale to finish")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Upscale Settings")

        model_path = self.config.get("model_path")
        configured_scale = int(self.config.get("scale", 2))
        model_scale = detect_model_scale(model_path, configured_scale)
        scale_label = QLabel(f"x{model_scale}")
        scale_label.setToolTip("Model scale is detected from the model filename when possible.")

        tile_input = QSpinBox()
        tile_input.setRange(0, 2048)
        tile_input.setSingleStep(16)
        tile_input.setValue(int(self.config.get("tile", 0)))

        tile_pad_input = QSpinBox()
        tile_pad_input.setRange(0, 256)
        tile_pad_input.setValue(int(self.config.get("tile_pad", 10)))

        pre_pad_input = QSpinBox()
        pre_pad_input.setRange(0, 256)
        pre_pad_input.setValue(int(self.config.get("pre_pad", 0)))

        half_input = QComboBox()
        half_input.addItems(["auto", "true", "false"])
        half_input.setCurrentText(str(self.config.get("use_half", "auto")).lower())

        format_input = QComboBox()
        format_input.addItems(SUPPORTED_FORMATS)
        format_input.setCurrentText(str(self.config.get("output_format", "png")).lower())

        chain_input = QCheckBox("Use upscaled result as next input")
        chain_input.setChecked(bool(self.config.get("chain_upscale", False)))
        chain_input.setToolTip("When enabled, each Run Upscale uses the previous result as its input.")

        form = QFormLayout()
        form.addRow("Model scale", scale_label)
        form.addRow("Tile", tile_input)
        form.addRow("Tile padding", tile_pad_input)
        form.addRow("Pre padding", pre_pad_input)
        form.addRow("Half precision", half_input)
        form.addRow("Default output format", format_input)
        form.addRow("Chain upscale", chain_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.config.update(
            scale=model_scale,
            tile=tile_input.value(),
            tile_pad=tile_pad_input.value(),
            pre_pad=pre_pad_input.value(),
            use_half=half_input.currentText(),
            output_format=format_input.currentText(),
            chain_upscale=chain_input.isChecked(),
        )
        self.statusBar().showMessage("Settings saved")
        self.append_log(
            "Settings saved: "
            f"model scale x{model_scale}, tile {tile_input.value()}, "
            f"chain upscale {'on' if chain_input.isChecked() else 'off'}"
        )

    def _show_error(self, title, message):
        self.statusBar().showMessage(message)
        QMessageBox.critical(self, title, message)

    @Slot(bool)
    def toggle_log(self, visible):
        self.log_view.setVisible(visible)
        self.config.set("show_log", visible)
        self.statusBar().showMessage("Log shown" if visible else "Log hidden")

    def clear_log(self):
        self.log_view.clear()
        self.statusBar().showMessage("Log cleared")

    @Slot(str)
    def append_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{timestamp}] {message}")

    def closeEvent(self, event):
        if self._is_upscaling():
            self.statusBar().showMessage("Wait for the current upscale to finish before closing")
            QMessageBox.information(
                self,
                "Upscale Running",
                "Wait for the current upscale to finish before closing the app.",
            )
            event.ignore()
            return

        super().closeEvent(event)
