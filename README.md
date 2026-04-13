# Image upscaler - Apache 2.0

PySide6 기반 이미지/실시간 업스케일러입니다.
이미지 로딩, 카메라 캡처, 업스케일 실행, 저장, 실시간 미리보기를 지원합니다.

---

## 주요 기능

- 이미지 파일 불러오기 (`.jpg`, `.png`, `.bmp` 등)
- 카메라 캡처 및 실시간 미리보기
- 얼굴 검출 및 업스케일 표시
- 원본 및 업스케일 이미지 분리 저장
- 전체 저장 (얼굴 감지 On일 때 검출 포함 4종)
- 메뉴바 중심 조작
- 얼굴 감지 On/Off (`D`)
- 카메라 Realtime 시작/중지 (`R`)
- 업스케일러 선택
  - 빠름: OpenCV Lanczos x2
  - 고품질: RealESRGAN x2plus

---

## 성능 정책

- 이미지 모드는 기본값으로 RealESRGAN x2plus를 사용합니다.
- RealESRGAN 가중치가 없으면 OpenCV Lanczos x2로 시작합니다.
- 실시간 모드는 기본값으로 OpenCV Lanczos x2를 사용합니다.
- CPU-only 환경에서 RealESRGAN 실시간 전체 프레임 처리는 느릴 수 있습니다.
- 실시간 모드는 업스케일 worker가 처리 중이면 새 프레임을 쌓지 않고 드롭합니다.
- 실시간 입력 프레임은 기본 640x480 이하로 제한합니다.
- RealESRGAN tile 기본값은 256입니다.

---

## 프로그램 구성

```bash
.
├── main.py # main
├── image_upscaler/
│   ├── upscaler.py        # 공통 업스케일러 래퍼
│   ├── ui.py                  # Main GUI Window
│   ├── image_processor.py     # 얼굴 검출 + 업스케일 처리
│   ├── image_saver.py         # 이미지 저장 모듈
│   ├── image_display.py       # QLabel 기반 이미지 표시 위젯
│   ├── button_panel.py        # 모든 버튼 구성 및 콜백 연결
│   └── face_detector.py   # OpenCV Haar Cascade 기반 얼굴 검출
├── realtime_upscaler/
│   ├── upscaler.py        # 공통 업스케일러 래퍼
│   ├── ui.py              # 실시간 GUI Window
│   ├── camera_worker.py   # 카메라 프레임 처리
│   └── face_detector.py   # OpenCV Haar Cascade 기반 얼굴 검출
├── upscalers/
│   ├── base.py
│   ├── factory.py
│   ├── opencv_resize.py
│   └── realesrgan_backend.py
├── weights/
│   └── RealESRGAN_x2plus.pth  # 업스케일 모델 (별도 다운로드 필요)
```
