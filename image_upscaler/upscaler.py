import torch
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
from PIL import Image
import numpy as np

class Upscaler:
    def __init__(self):
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model_path = 'weights/RealESRGAN_x2plus.pth'

        self.model = RRDBNet(
            num_in_ch=3, num_out_ch=3,
            num_feat=64, num_block=23,
            num_grow_ch=32, scale=2
        )

        self.upscaler = RealESRGANer(
            scale=2,
            model_path=model_path,
            model=self.model,
            tile=40,
            tile_pad=10,
            pre_pad=0,
            half=(device.type == 'cuda'),
            device=device
        )

    def upscale(self, pil_img: Image.Image) -> Image.Image:
        try:
            img_np = np.array(pil_img)
            sr_img, _ = self.upscaler.enhance(img_np)
            return Image.fromarray(sr_img)
        except Exception as e:
            print(f"❌ 업스케일 실패: {e}")
            return pil_img  # 실패 시 원본 반환
