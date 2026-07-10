from image_upscaler.image_io import save_image

class ImageSaver:
    def save(self, path, image):
        save_image(path, image)
