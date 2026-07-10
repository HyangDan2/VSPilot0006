# HD2 Real ESRGAN Image Upscaler

A compact PySide6 desktop app for still-image upscaling with Real-ESRGAN.

The app focuses on image files only. Realtime camera processing is intentionally not included, because frame-by-frame Real-ESRGAN processing is too slow for a responsive realtime pipeline unless a separate optimized backend is used.

## Features

- Load still images from common formats: PNG, JPG, JPEG, BMP, WebP, TIFF, and TIF.
- Select a `.pth` Real-ESRGAN model from the menu bar.
- Run image upscaling from a large two-pane preview.
- Save the original image or the upscaled result.
- Read user settings from a local `config.yaml`, with `config.example.yaml` tracked as the reference template.
- Display load, save, model, and upscaling status in the status bar and optional log panel.
- Show tile inference progress in a status-bar progress bar when the backend emits `current/total` progress output.
- Optionally use the previous upscaled result as the next upscale input.

## Keyboard Shortcuts

- `L`: Load image
- `R`: Run upscale
- `S`: Save upscaled image
- `O`: Select `.pth` model
- `Ctrl/Cmd+O`: Load image
- `Ctrl/Cmd+S`: Save upscaled image
- `Ctrl/Cmd+Q`: Quit

## Project Structure

```text
.
├── main.py
├── config.example.yaml
├── Requirements.txt
├── image_upscaler/
│   ├── config.py
│   ├── image_display.py
│   ├── image_io.py
│   ├── image_processor.py
│   ├── image_saver.py
│   ├── ui.py
│   └── upscaler.py
└── weights/
    └── RealESRGAN_x2plus.pth
```

## Configuration

Settings are stored in a local `config.yaml`. This file is user-owned and ignored by Git because it can contain machine-specific paths.

Start from the tracked example file:

```bash
cp config.example.yaml config.yaml
```

If `config.yaml` is missing, the app falls back to built-in defaults. Menu changes such as selecting a model or changing upscale settings will write the local `config.yaml`.

```yaml
model_path: weights/RealESRGAN_x2plus.pth
last_open_dir: ''
last_save_dir: ''
input_format: ''
output_format: png
scale: 2
tile: 0
tile_pad: 10
pre_pad: 0
use_half: auto
show_log: true
chain_upscale: false
```

`tile: 0` disables tiled processing. This is usually faster for images that fit in GPU memory. Increase `tile` only when large images fail because of memory limits.

`scale` is the model scale, not an arbitrary resize factor. The app detects scale from the selected model filename when possible:

- `RealESRGAN_x2plus.pth` -> `scale: 2`
- `RealESRGAN_x4plus.pth` -> `scale: 4`
- Unknown filename -> configured/default `scale`

`chain_upscale: false` keeps every run based on the original loaded image. When set to `true`, each new run uses the previous upscaled result as the next input. This can grow image dimensions, memory use, and processing time very quickly.

`show_log` controls whether the lower log panel is visible at startup.

## Model File

Download a compatible Real-ESRGAN `.pth` model and either place it at:

```text
weights/RealESRGAN_x2plus.pth
```

or select it from:

```text
Model > Select .pth Model
```

When a model is selected, the app tries to detect the scale from the filename. If no scale is detected, it keeps the configured/default scale.

## Log Panel

The lower log panel shows timestamped activity such as image loading, model loading, inference start, completion time, and errors.

Use:

```text
View > Show Log
View > Clear Log
```

## Progress Bar

The status-bar progress bar reads tile inference progress from backend output such as `1/825`, `124/825`, or `825/825`. The total tile count is detected dynamically for each image and tile configuration.

Progress updates represent tile inference progress, not the full end-to-end job. Model loading and setup can still take time before tile progress appears. If tiled inference is disabled with `tile: 0`, or if the backend does not emit `current/total` output, the progress bar stays indeterminate until the upscale completes.

Log output for tile progress is throttled to roughly once every 0.5 seconds to keep the log readable.

## Install

```bash
pip install -r Requirements.txt
```

## Run

```bash
python main.py
```

## License

MIT License. See `LICENSE.txt`.

## Notes On Realtime Video

This app does not process realtime video. Real-ESRGAN is expensive when applied to every frame, and tiled inference adds extra overhead. For realtime video, consider an optimized pipeline using a smaller model, lower input resolution, frame skipping, async processing, or an inference backend such as NCNN/Vulkan, ONNX Runtime, TensorRT, or OpenVINO.
