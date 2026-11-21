# Aupscaler

A fast, offline Windows image upscaler and enhancer built with Python, OpenCV, and Pillow.

## Quick Start

### Windows Installer
Run `Aupscaler_Setup.exe` and pick an install folder. Once installed, open **Aupscaler** from the Desktop or Start Menu shortcut.

### Running from Source
```bash
python aupscaler_gui.py
```

## Features

- **1× to 8× Scaling**: Quick presets (`1×`, `2×`, `3×`, `4×`) and custom scaling up to `8×` with live target dimensions and memory estimates.
- **Four Quality Modes**:
  - `Balanced (Fast Neural)`: Fast neural upscaling for photos and illustrations.
  - `High Detail (Deep Neural)`: Richer texture synthesis for portraits and detailed scenes.
  - `Photo & Art (Lanczos)`: Crisp mathematical scaling with minimal sharpening.
  - `Pixel Art (No Blur)`: Nearest-neighbor scaling that keeps pixel edges sharp.
- **Opt-In Enhancements**:
  - `Sharpen & Deblur`: Edge-aware luminance sharpening that leaves flat backgrounds clean.
  - `Reduce Noise`: Fast compression cleanup that preserves fine textures like freckles and line art.
  - `Balance Tone & Color`: Subtle local contrast and saturation adjustment.
  - `Remove Background`: Automated foreground segmentation with edge refinement, automatic letterbox removal, and solid-color chroma keying.
- **Smart Cutout & Manual Mask Brushes**:
  - `Smart Cut`: Circle or draw across any person or object (with a bit of surrounding area) to isolate just that subject. Hold `Shift` and draw again to add another subject cleanly.
  - `Erase` & `Restore` Brushes: Paint directly on the preview to remove unwanted fragments or restore missing details with adjustable brush size (`[` / `]`), optional `Soft Edge` feathering, and `Ctrl+Z` / `Ctrl+Y` undo & redo history.
- **Interactive Workspace**:
  - Light and Dark themes switchable anytime from the header.
  - Before/After split slider with live preview, zoom controls (`1:1`, `Fit`, scroll wheel), right-click panning, Spacebar/button comparison toggle, and mid-job cancellation.
  - Batch processing queue supporting multiple files or whole folders.
  - PNG, JPG, and WEBP export, clipboard paste/copy, drag-and-drop, and 10 UI languages.

## Running Tests

```bash
python -m unittest tests/test_upscaler.py
```
