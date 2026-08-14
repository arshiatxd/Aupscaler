# aupscaler - AI Super-Resolution Suite

A high-performance Windows desktop application and Python engine capable of upscaling images up to **40x resolution** (4000% scale) with studio-grade enhancement algorithms, AI background removal, face restoration, HDR tone-mapping, 300 DPI print metadata injection, multilingual support (10 languages), and a zero-neon modern obsidian user interface.

## Quick Start Options

### Option 1: Standalone Windows `.exe` (Recommended)
Double-click **[`aupscaler.exe`](file:///c:/Users/Parsian/Desktop/prj/pr1/aupscaler.exe)** in the project root folder or `dist/aupscaler.exe`.

### Option 2: 1-Click Batch Launcher
Double-click [`run.bat`](file:///c:/Users/Parsian/Desktop/prj/pr1/run.bat).

### Option 3: Python Launcher
Run from terminal:
```bash
python desktop_app.py
```
or
```bash
python run.py
```

---

## Features

- **40x Resolution Scaling**:
  - Quick percentage presets: **`5%`**, **`10%`**, **`15%`**, **`20%`**, **`25%`**, **`30%`**, **`35%`**, **`40%`**
  - Multiplier presets: **`2x`**, **`4x`**, **`8x`**, **`16x`**, **`40x Ultra`**
  - Custom value input: Enter any custom percentage or multiplier.
- **Paid Pro Features (100% Free & Local)**:
  - **AI Background Cutout**: 1-click transparent PNG removal using `rembg`.
  - **Portrait & Face Clarity Booster**: High-frequency texture recovery and skin detail refinement.
  - **Deblock & Denoise**: Removes JPEG compression artifacts and color noise.
  - **Auto HDR & Micro-Contrast**: CLAHE dynamic range expansion in LAB color space.
  - **Commercial Print DPI**: 72, 150, 300 (Print Standard), and 600 DPI (Ultra Fine-Art).
  - **Batch Processing Queue**: Queue multiple images and download individually or as a single ZIP.
- **Interactive UI**:
  - Smooth Before/After split curtain comparison slider.
  - Real-time zoom (up to 800%) and pan navigation.
  - Live ROI (Region of Interest) preview generator.
  - 10-Language instant switcher (English, Spanish, French, German, Japanese, Chinese, Persian, Arabic with RTL, Russian, Portuguese).
  - Zero-neon aesthetic: refined obsidian and frosted dark surfaces with smooth transitions.

---

## Running Tests

To run the automated test suite:
```bash
python -m unittest tests/test_upscaler.py
```
