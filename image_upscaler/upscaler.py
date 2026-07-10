from pathlib import Path
import re

from PIL import Image
import numpy as np


def detect_model_scale(model_path, default=2):
    if not model_path:
        return default

    match = re.search(r"x([234])(?=\D|$)", Path(model_path).name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return default


class Upscaler:
    def __init__(self, config):
        self.config = config
        self.upscaler = None
        self.loaded_signature = None

    def upscale(self, pil_img: Image.Image, progress=None) -> Image.Image:
        self._emit(progress, "Preparing model")
        self._ensure_loaded(progress=progress)
        self._emit(progress, "Running inference")
        img_np = np.array(pil_img.convert("RGB"))
        sr_img, _ = self.upscaler.enhance(img_np)
        self._emit(progress, "Inference complete")
        return Image.fromarray(sr_img)

    def _ensure_loaded(self, progress=None):
        signature = self._signature()
        if self.upscaler is not None and self.loaded_signature == signature:
            self._emit(progress, f"Model ready: {Path(signature['model_path']).name} (cached)")
            return

        model_path = Path(signature["model_path"]).expanduser()
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self._emit(progress, f"Loading model: {model_path.name}")
        import torch
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        use_half = signature["use_half"]
        half = device.type == "cuda" if use_half == "auto" else bool(use_half)

        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=signature["scale"],
        )

        self.upscaler = RealESRGANer(
            scale=signature["scale"],
            model_path=str(model_path),
            model=model,
            tile=signature["tile"],
            tile_pad=signature["tile_pad"],
            pre_pad=signature["pre_pad"],
            half=half,
            device=device,
        )
        self.loaded_signature = signature
        self._emit(progress, f"Model ready: {model_path.name} on {device.type}, scale x{signature['scale']}")

    def _signature(self):
        use_half = self.config.get("use_half", "auto")
        if isinstance(use_half, str):
            use_half = use_half.lower()
            if use_half not in {"auto", "true", "false"}:
                use_half = "auto"
            if use_half == "true":
                use_half = True
            elif use_half == "false":
                use_half = False

        configured_scale = int(self.config.get("scale", 2))
        model_path = self.config.get("model_path")
        return {
            "model_path": model_path,
            "scale": detect_model_scale(model_path, configured_scale),
            "tile": int(self.config.get("tile", 0)),
            "tile_pad": int(self.config.get("tile_pad", 10)),
            "pre_pad": int(self.config.get("pre_pad", 0)),
            "use_half": use_half,
        }

    def _emit(self, progress, message):
        if progress is not None:
            progress(message)
