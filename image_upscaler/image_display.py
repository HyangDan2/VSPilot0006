from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt


class ImageDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.labels = [QLabel("Original Image"), QLabel("Upscaled Image")]
        self.images = [None, None]

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        for label in self.labels:
            label.setMinimumSize(360, 360)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("border: 1px solid #444; background: #181818; color: #bbbbbb;")
            layout.addWidget(label)
        self.setLayout(layout)

    def show_original(self, image):
        self.images[0] = image.copy()
        self._refresh_label(0)

    def show_upscaled(self, image):
        self.images[1] = image.copy()
        self._refresh_label(1)

    def clear_upscaled(self):
        self.images[1] = None
        self.labels[1].clear()
        self.labels[1].setText("Upscaled Image")

    def show_message(self, message):
        for label in self.labels:
            label.setText(message)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.repaint()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_label(0)
        self._refresh_label(1)

    def _refresh_label(self, index):
        image = self.images[index]
        if image is None:
            return

        pixmap = self._to_pixmap(image)
        scaled = pixmap.scaled(
            self.labels[index].size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.labels[index].setPixmap(scaled)

    def _to_pixmap(self, image):
        if image.mode == "RGBA":
            qimage_format = QImage.Format.Format_RGBA8888
            converted = image
        else:
            qimage_format = QImage.Format.Format_RGB888
            converted = image.convert("RGB")

        data = converted.tobytes("raw", converted.mode)
        qimage = QImage(data, converted.width, converted.height, qimage_format)
        qimage.ndarray = data
        return QPixmap.fromImage(qimage)
