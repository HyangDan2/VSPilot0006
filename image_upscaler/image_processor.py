class ImageProcessor:
    def __init__(self, upscaler):
        self.upscaler = upscaler

    def upscale(self, image, progress=None):
        return self.upscaler.upscale(image, progress=progress)
