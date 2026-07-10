from pathlib import Path

import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

DEFAULT_CONFIG = {
    "model_path": "weights/RealESRGAN_x2plus.pth",
    "last_open_dir": "",
    "last_save_dir": "",
    "input_format": "",
    "output_format": "png",
    "scale": 2,
    "tile": 0,
    "tile_pad": 10,
    "pre_pad": 0,
    "use_half": "auto",
    "show_log": True,
    "chain_upscale": False,
}


class AppConfig:
    def __init__(self, path=CONFIG_PATH):
        self.path = Path(path)
        self.data = self.load()

    def load(self):
        if not self.path.exists():
            return DEFAULT_CONFIG.copy()

        with self.path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}

        config = DEFAULT_CONFIG.copy()
        config.update({k: v for k, v in loaded.items() if v is not None})
        return config

    def save(self, data=None):
        if data is not None:
            self.data = data
        self.path.write_text(yaml.safe_dump(self.data, sort_keys=False), encoding="utf-8")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def update(self, **kwargs):
        self.data.update(kwargs)
        self.save()
