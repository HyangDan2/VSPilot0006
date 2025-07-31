import torch
from realesrgan import RealESRGAN
from PIL import Image

class Upscaler:
    def __init__(self):
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = RealESRGAN(device, scale=2)
        self.model.load_weights('RealESRGAN_x2.pth')

    def upscale(self, pil_img: Image.Image) -> Image.Image:
        return self.model.predict(pil_img)
