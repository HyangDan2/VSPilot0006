from dataclasses import dataclass

from upscalers.opencv_resize import OpenCVResizeUpscaler


@dataclass(frozen=True)
class UpscalerOption:
    key: str
    label: str


UPSCALER_OPTIONS = [
    UpscalerOption("opencv_lanczos", "빠름: OpenCV Lanczos x2"),
    UpscalerOption("realesrgan", "고품질: RealESRGAN x2plus"),
]


def default_upscaler_key(mode: str) -> str:
    if mode == "image":
        return "realesrgan"
    return "opencv_lanczos"


def create_upscaler(key: str):
    if key == "realesrgan":
        from upscalers.realesrgan_backend import RealESRGANUpscaler

        return RealESRGANUpscaler()
    return OpenCVResizeUpscaler()


def device_summary() -> str:
    from upscalers.realesrgan_backend import preferred_torch_device

    return preferred_torch_device().type.upper()
