from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout

class ButtonPanel(QWidget):
    def __init__(self, callbacks):
        super().__init__()
        self.callbacks = callbacks

        btn_camera = QPushButton("📷 카메라 캡처")
        btn_load = QPushButton("🖼 이미지 불러오기")
        btn_upscale = QPushButton("🚀 업스케일 실행")
        btn_save_original = QPushButton("💾 원본 저장")
        btn_save_upscaled = QPushButton("💾 업스케일 저장")
        btn_save_all = QPushButton("📁 전체 저장")

        btn_camera.clicked.connect(callbacks.get('camera'))
        btn_load.clicked.connect(callbacks.get('load'))
        btn_upscale.clicked.connect(callbacks.get('upscale'))
        btn_save_original.clicked.connect(callbacks.get('save_original'))
        btn_save_upscaled.clicked.connect(callbacks.get('save_upscaled'))
        btn_save_all.clicked.connect(callbacks.get('save_all'))

        layout = QHBoxLayout()
        for btn in [btn_camera, btn_load, btn_upscale, btn_save_original, btn_save_upscaled, btn_save_all]:
            layout.addWidget(btn)

        self.setLayout(layout)