from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout

class ButtonPanel(QWidget):
    def __init__(self, callbacks):
        super().__init__()
        self.callbacks = callbacks

        self.buttons = {
            "camera": QPushButton("카메라 캡처"),
            "load": QPushButton("파일 열기"),
            "upscale": QPushButton("업스케일"),
            "save_original": QPushButton("원본 저장"),
            "save_upscaled": QPushButton("결과 저장"),
            "save_all": QPushButton("전체 저장"),
        }

        for name, button in self.buttons.items():
            button.clicked.connect(callbacks.get(name))

        layout = QHBoxLayout()
        for btn in self.buttons.values():
            layout.addWidget(btn)

        self.setLayout(layout)

    def set_processing(self, is_processing):
        for name, button in self.buttons.items():
            button.setEnabled(not is_processing)

    def set_save_enabled(self, has_original, has_upscaled):
        self.buttons["save_original"].setEnabled(has_original)
        self.buttons["save_upscaled"].setEnabled(has_upscaled)
        self.buttons["save_all"].setEnabled(has_original and has_upscaled)
