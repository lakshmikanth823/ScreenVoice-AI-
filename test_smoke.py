"""Automated test suite for GameVocalize engines."""
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

def test_config():
    print("[TEST] config.py...", end=" ", flush=True)
    from config import get_config, AppConfig
    c = get_config()
    assert isinstance(c, AppConfig)
    print(f"OK (lang={c.ocr_language}, confidence={c.ocr_confidence_threshold})", flush=True)

def test_capture():
    print("[TEST] capture_engine.py...", end=" ", flush=True)
    from capture_engine import CaptureEngine
    ce = CaptureEngine(try_dxcam=False)
    assert ce.backend in ('dxcam', 'mss', 'pil', None)
    frame = ce.grab_full_screen()
    print(f"OK (backend={ce.backend}, frame={'captured' if frame is not None else 'None (headless)'})", flush=True)

def test_preprocessor():
    print("[TEST] preprocessor.py...", end=" ", flush=True)
    import numpy as np
    from preprocessor import Preprocessor
    p = Preprocessor()
    img = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
    result = p.process(img)
    assert result is not None
    print(f"OK (input={img.shape}, output={result.shape})", flush=True)

def test_ocr():
    print("[TEST] ocr_engine.py...", end=" ", flush=True)
    from ocr_engine import OcrEngine, RAPIDOCR_AVAILABLE
    if not RAPIDOCR_AVAILABLE:
        print("SKIP (RapidOCR not installed)", flush=True)
        return
    oe = OcrEngine()
    print("OK (RapidOCR initialized)", flush=True)

def test_dedup():
    print("[TEST] dedup_engine.py...", end=" ", flush=True)
    from dedup_engine import DedupEngine
    d = DedupEngine()
    d.add("Hello world test")
    assert d.is_duplicate("Hello world test") == True
    assert d.is_duplicate("Completely different") == False
    new = d.filter_new(["Hello world test", "Brand new text"])
    assert len(new) == 1
    print("OK", flush=True)

def test_tts():
    print("[TEST] tts_engine.py...", end=" ", flush=True)
    from tts_engine import TtsEngine
    tts = TtsEngine(default_volume=100)
    assert tts.get_volume() == 100
    tts.set_volume(80)
    assert tts.get_volume() == 80
    tts.speak("Test speech")
    time.sleep(0.3)
    tts.stop()
    tts.shutdown()
    print("OK (speech queued, volume tested, stopped)", flush=True)

def test_subtitle_cleaner():
    print("[TEST] subtitle cleaner...", end=" ", flush=True)
    from main import clean_subtitle_text
    raw = "♪ [Dramatic Music] Hello, is anybody there? (whispering) ♪"
    cleaned = clean_subtitle_text(raw)
    assert cleaned == "Hello, is anybody there?"
    print(f"OK (cleaned='{cleaned}')", flush=True)

def test_hotkeys():
    print("[TEST] hotkey_manager.py...", end=" ", flush=True)
    from hotkey_manager import HotkeyManager
    hm = HotkeyManager()
    called = []
    hm.register("full_screen_read", lambda: called.append(True))
    print("OK (callbacks registered)", flush=True)

def test_tray():
    print("[TEST] tray_app.py...", end=" ", flush=True)
    from tray_app import TrayApp
    ta = TrayApp({"toggle_reader": lambda: None, "full_screen_read": lambda: None,
                   "region_read": lambda: None, "toggle_auto_read": lambda: None,
                   "define_roi": lambda: None, "quit_app": lambda: None})
    print("OK (tray icon created)", flush=True)

if __name__ == "__main__":
    print("=" * 50, flush=True)
    print("  GameVocalize - Engine Smoke Tests", flush=True)
    print("=" * 50, flush=True)

    tests = [test_config, test_capture, test_preprocessor, test_ocr,
             test_dedup, test_tts, test_subtitle_cleaner, test_hotkeys, test_tray]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}", flush=True)
            failed += 1

    print("=" * 50, flush=True)
    print(f"  Results: {passed} passed, {failed} failed", flush=True)
    print("=" * 50, flush=True)
