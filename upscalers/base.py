from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class UpscaleResult:
    image: np.ndarray
    elapsed_ms: float
    backend_name: str
    device_name: str


class UpscalerBackend:
    name = "Base"
    device_name = "CPU"

    def upscale(self, frame: np.ndarray) -> UpscaleResult:
        raise NotImplementedError


def resize_frame(
    frame: np.ndarray,
    max_size: Tuple[int, int] | None,
) -> np.ndarray:
    if max_size is None:
        return frame

    max_width, max_height = max_size
    height, width = frame.shape[:2]
    scale = min(max_width / width, max_height / height, 1.0)
    if scale >= 1.0:
        return frame

    target_size = (int(width * scale), int(height * scale))
    return cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
