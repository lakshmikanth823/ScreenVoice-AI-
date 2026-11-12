# GameVocalize 🎬🎮

**GameVocalize** is an ultra-fast, low-latency live screen reader designed specifically for **fullscreen video games (RPG story dialogues)** and **movies/streaming videos (rapid foreign subtitles)**.

Powered by **RapidOCR (ONNX Runtime)** and **Windows SAPI5**, GameVocalize continuously detects and vocalizes on-screen text with zero lag, instant speech buffer purging, and natural voice selection.

---

## ✨ Features

- 🎬 **Ultra-Fast Movie Subtitle Mode**: 80ms live OCR loop (~10 FPS) tailored for fast-paced, scrolling foreign film subtitles.
- 🎮 **Story Game Reader Mode**: Seamless dialogue reading for games like *Skyrim, The Witcher, Baldur's Gate, Persona, Genshin Impact*.
- ⚡ **Instant Page Advance Hooks**: Pressing `Space`, `Enter`, `E`, or clicking instantly triggers a 60ms scan to read the next page/dialogue without delay.
- 🚫 **Zero Backlog / Zero Lag**: Employs hardware-level SAPI buffer purge (`SVSFPurgeBeforeSpeak`) so speech never queues up or lags behind fast-moving scenes.
- 🎤 **Sweet Voice Selection**: Instant switching between **👩 Sweet Female Voice (Microsoft Zira)** and **👨 Male Voice (Microsoft David)** with preview test buttons.
- 🔊 **Independent Volume Boost**: Dedicated reader volume slider (0% to 100%) ensuring spoken dialogue is clear above background movie audio or game SFX.
- 📐 **1-Click Subtitle Region Preset**: One click automatically locks onto the standard bottom 20% subtitle area across displays with native DPI scaling.
- 🎯 **Transparent Drag-and-Drop ROI Selector**: Draw custom dialogue/subtitle bounding boxes anytime (`Ctrl+Alt+D`).
- 🧹 **Smart Subtitle Cleaner**: Automatically strips sound tags (`[Music]`, `♪`, `♫`, `(whispering)`, `[Door slams]`).

---

## ⌨️ Global Hotkeys

| Hotkey | Action |
| :--- | :--- |
| `Ctrl + Alt + M` | Start / Stop Movie Subtitle Mode |
| `Ctrl + Alt + A` | Start / Stop Game Story Mode |
| `Ctrl + Alt + D` | Custom Draw Dialogue / Subtitle Box |
| `Ctrl + Alt + F` | Read Full Screen Now |
| `Ctrl + Alt + R` | Read Selected Region Now |
| `Ctrl + Alt + S` | Silence Speech Immediately |
| `Ctrl + Alt + X` | Pause / Resume Reader |
| `Ctrl + Alt + =` | Increase Speech Speed |
| `Ctrl + Alt + -` | Decrease Speech Speed |
| `Ctrl + Alt + Q` | Quit Application |

---

## 🚀 Quick Start

### 1. Requirements
- Windows 10 / 11
- Python 3.10+

### 2. Setup
Run `setup.bat` or install manually:
```bash
pip install dxcam mss opencv-python numpy Pillow keyboard mouse pystray pywin32 customtkinter rapidocr_onnxruntime onnxruntime
```

### 3. Launch
Double-click `Start_GameVocalize.bat` or execute:
```bash
python main.py
```

---

## 🛠️ Architecture

- **Capture Engine**: Multi-tier capture using `dxcam` (DirectX GPU duplication), falling back to `mss` and `PIL ImageGrab`.
- **Image Preprocessor**: LAB color-space contrast enhancement (CLAHE) preserving font colors.
- **OCR Engine**: RapidOCR ONNX Runtime execution (~15ms per inference).
- **Deduplication Engine**: Fuzzy sequence matching preventing duplicate vocalization of static screens.
- **TTS Engine**: Threaded Windows SAPI5 COM handler with instant buffer purge and volume control.
- **Desktop UI**: Modern dark theme built with `CustomTkinter`.

---

## 📄 License
MIT License.
