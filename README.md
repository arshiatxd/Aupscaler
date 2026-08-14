# Aupscaler 🚀

> **State-of-the-Art Deep Learning Super-Resolution & Image Enhancement**

Aupscaler is a high-performance, studio-grade desktop application for upscaling, deblurring, denoising, and extracting backgrounds from images up to **40× native resolution** using pre-trained convolutional neural networks (CNNs).

---

## ✨ Features

- **⚡ Deep Learning Super-Resolution Models:**
  - **FSRCNN** (*Fast Super-Resolution CNN*): Fast 8-layer deep neural network for high-frequency edge and texture synthesis.
  - **ESPCN** (*Efficient Sub-Pixel Convolutional Neural Network*): Real-time sub-pixel feature reconstruction.
  - **LapSRN** (*Deep Laplacian Pyramid Network*): Multi-stage progressive residual reconstruction.
  - **Multi-Scale Frequency Decomposition**: Custom high-ratio resolution scaling up to 40×.
- **🎨 Studio Enhancement Suite:**
  - **Focus Deblur**: Recovers sharp edge contours from camera and motion blur.
  - **Fast Non-Local Means Denoising**: Removes sensor grain and JPEG block artifacts.
  - **Natural Studio HDR**: CLAHE luminance balancing with natural color saturation.
  - **Deep Background Cutout**: Neural foreground segmentation with real-time alpha checkerboard canvas.
- **🌓 Dynamic Studio Theme:**
  - Full Light Mode and Dark Mode support with smooth theme transitions.
  - 10-language internationalization (English, فارسی, العربية, Español, Français, Deutsch, 日本語, 中文, Русский, Português).
  - Integrated `A Nafis` typography for Arabic and Farsi scripts.
- **⚡ Interactive Studio Canvas:**
  - 60 FPS split-slider before/after comparison divider.
  - Hold **Spacebar** to toggle between low-res source and upscaled output.
  - 2D panning, mouse wheel zoom, 1:1 pixel inspection, and multi-threaded background preview debouncing.
- **📦 Batch Processing Queue:**
  - Upscale entire folders or multi-file queues in background worker threads.

---

## 🛠️ Architecture

```
Aupscaler/
├── aupscaler_gui.py      # CustomTkinter GUI & 60 FPS comparison canvas
├── installer_wizard.py   # Windows Setup Wizard & Shortcut Generator
├── build_exe.py          # PyInstaller standalone distribution compiler
├── backend/
│   ├── __init__.py
│   └── upscaler.py       # OpenCV DNN inference, tiling, CLAHE & NLM pipeline
├── assets/
│   ├── logo.png          # Transparent vector diamond emblem
│   ├── icon.ico          # Windows multi-size application icon
│   └── fonts/
│       └── A Nafis.ttf   # Persian/Arabic high-legibility typography
├── models/               # Pre-trained deep learning neural network weights (.pb)
│   ├── FSRCNN_x2.pb
│   ├── FSRCNN_x3.pb
│   ├── FSRCNN_x4.pb
│   ├── ESPCN_x2.pb
│   ├── ESPCN_x3.pb
│   ├── ESPCN_x4.pb
│   └── LapSRN_x4.pb
├── tests/
│   └── test_upscaler.py  # Unit test suite
└── requirements.txt
```

---

## 🚀 Quickstart

### Option 1: Run via Python
```bash
git clone https://github.com/your-username/Aupscaler.git
cd Aupscaler
pip install -r requirements.txt
python aupscaler_gui.py
```

### Option 2: Run via Batch File (Windows)
Double-click `run.bat` or `aupscaler.bat`.

### Option 3: Compile Standalone Windows Executable
```bash
python build_exe.py
```
The compiled standalone binary will be generated at `dist/aupscaler/aupscaler.exe`.

### Option 4: Launch Setup Wizard
```bash
python installer_wizard.py
```

---

## 🧪 Testing

Run the automated test suite:
```bash
python -m unittest tests/test_upscaler.py
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
