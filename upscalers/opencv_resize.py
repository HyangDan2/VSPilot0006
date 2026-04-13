from time import perf_counter

import cv2
import numpy as np

from upscalers.base import UpscaleResult, UpscalerBackend


class OpenCVResizeUpscaler(UpscalerBackend):
    device_name = "CPU"

    def __init__(self, scale: int = 2, interpolation: int = cv2.INTER_LANCZOS4):
        self.scale = scale
        self.interpolation = interpolation
        self.name = "OpenCV Lanczos x2" if interpolation == cv2.INTER_LANCZOS4 else "OpenCV Resize x2"

    def upscale(self, frame: np.ndarray) -> UpscaleResult:
        started_at = perf_counter()
        height, width = frame.shape[:2]
        result = cv2.resize(
            frame,
            (width * self.scale, height * self.scale),
            interpolation=self.interpolation,
        )
        elapsed_ms = (perf_counter() - started_at) * 1000
        return UpscaleResult(result, elapsed_ms, self.name, self.device_name)
