from time import perf_counter

import cv2
import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

from upscalers.base import UpscaleResult, UpscalerBackend


def preferred_torch_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class RealESRGANUpscaler(UpscalerBackend):
    name = "RealESRGAN x2plus"

    def __init__(self, model_path: str = "weights/RealESRGAN_x2plus.pth", tile: int = 256):
        self.device = preferred_torch_device()
        self.device_name = self.device.type.upper()
        self.model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=2,
        )
        self.upscaler = RealESRGANer(
            scale=2,
            model_path=model_path,
            model=self.model,
            tile=tile,
            tile_pad=10,
            pre_pad=0,
            half=self.device.type == "cuda",
            device=self.device,
        )

    def upscale(self, frame: np.ndarray) -> UpscaleResult:
        started_at = perf_counter()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        sr_rgb, _ = self.upscaler.enhance(rgb)
        result = cv2.cvtColor(sr_rgb, cv2.COLOR_RGB2BGR)
        elapsed_ms = (perf_counter() - started_at) * 1000
        return UpscaleResult(result, elapsed_ms, self.name, self.device_name)
