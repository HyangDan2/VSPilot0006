# UDIR 업스케일러 - Apache 2.0

PySide6 기반의 초간단 실시간 이미지 업스케일러입니다.  
🖼 이미지 로딩, 📷 카메라 캡처, 🚀 업스케일 실행, 💾 이미지 저장까지 GUI로 쉽게 처리할 수 있어요!

---

## 🧠 주요 기능

- ✅ 이미지 파일 불러오기 (`.jpg`, `.png`, `.bmp` 등)
- ✅ 카메라 실시간 캡처 지원
- ✅ 얼굴 검출 및 업스케일 표시
- ✅ 원본 및 업스케일 이미지 분리 저장
- ✅ 전체 저장 (검출 포함 4종)

---

## 🖼 프로그램 구성

```bash
.
├── main.py # main
├── image_upscaler/
│   ├── upscaler.py        # RealESRGAN 기반 업스케일러
│   ├── ui.py                  # Main GUI Window
│   ├── image_processor.py     # 얼굴 검출 + 업스케일 처리
│   ├── image_saver.py         # 이미지 저장 모듈
│   ├── image_display.py       # QLabel 기반 이미지 표시 위젯
│   ├── button_panel.py        # 모든 버튼 구성 및 콜백 연결
│   └── face_detector.py   # OpenCV Haar Cascade 기반 얼굴 검출
├── weights/
│   └── RealESRGAN_x2plus.pth  # 업스케일 모델 (별도 다운로드 필요)
```
