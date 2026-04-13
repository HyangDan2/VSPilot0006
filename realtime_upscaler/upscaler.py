from upscalers import create_upscaler, default_upscaler_key

class Upscaler:
    def __init__(self, key=None):
        self.backend = create_upscaler(key or default_upscaler_key("realtime"))
        self.name = self.backend.name
        self.device_name = self.backend.device_name

    def upscale(self, frame):
        return self.backend.upscale(frame)
