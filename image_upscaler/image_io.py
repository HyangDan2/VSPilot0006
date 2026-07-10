from pathlib import Path

from PIL import Image


SUPPORTED_FORMATS = ("png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff")
DISPLAY_FORMATS = " ".join(f"*.{fmt}" for fmt in SUPPORTED_FORMATS)


def image_filter(label="Images"):
    return f"{label} ({DISPLAY_FORMATS});;All Files (*)"


def extension_for_path(path):
    suffix = Path(path).suffix.lower().lstrip(".")
    return suffix if suffix in SUPPORTED_FORMATS else ""


def normalize_output_path(path, fallback_format):
    output_path = Path(path)
    suffix = output_path.suffix.lower().lstrip(".")
    output_format = suffix if suffix in SUPPORTED_FORMATS else str(fallback_format or "png").lower()

    if output_format not in SUPPORTED_FORMATS:
        output_format = "png"

    if suffix not in SUPPORTED_FORMATS:
        output_path = output_path.with_suffix(f".{output_format}")

    return output_path, output_format


def load_image(path):
    image = Image.open(path)
    image.load()
    return image


def save_image(path, image):
    output_path = Path(path)
    fmt = output_path.suffix.lower().lstrip(".")
    if fmt == "jpg":
        fmt = "jpeg"

    save_image = image
    if fmt in {"jpeg", "bmp"} and image.mode in {"RGBA", "LA", "P"}:
        save_image = image.convert("RGB")
    elif fmt not in {"png", "webp", "tiff", "tif"} and image.mode not in {"RGB", "L"}:
        save_image = image.convert("RGB")

    save_image.save(output_path)
