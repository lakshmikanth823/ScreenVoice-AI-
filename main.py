"""
main.py - GameVocalize Desktop GUI Application Entry Point
Main orchestrator that wires together all engines with a modern CustomTkinter GUI:
  Capture -> Preprocess -> OCR -> Dedup -> TTS -> GUI Real-Time Log Box
Includes:
  1. 🎬 Movie & Video Subtitle Mode (Ultra-Fast 80ms Live Subtitle Reader with Volume Boost)
  2. 🎮 Story Game Mode (Page-by-Page Continuous Dialogue Reader with Space/Enter Hooks)
  3. 🎤 Sweet Female Voice (Zira) & Male Voice (David) Selection
  4. 📸 Manual Screen & Region Reader
"""

import sys
import re
import logging
import threading
import time
import ctypes
from difflib import SequenceMatcher
import numpy as np
import keyboard

# Set Windows DPI Awareness so screen capture & ROI overlay coordinates match 1:1 on all displays
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Reconfigure stdout for UTF-8 to avoid Windows encoding errors
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GameVocalize")

from config import get_config, load_config, save_config, AppConfig
from capture_engine import CaptureEngine
from preprocessor import Preprocessor
from ocr_engine import OcrEngine
from dedup_engine import DedupEngine
from tts_engine import TtsEngine
from hotkey_manager import HotkeyManager
from roi_selector import RoiSelector
from app_gui import AppGUI


def clean_subtitle_text(text: str) -> str:
    """Clean subtitle artifacts like music notes, sound cues, and formatting."""
    if not text:
        return ""
    cleaned = re.sub(r'[♪♫#]', '', text)
    cleaned = re.sub(r'\[.*?\]', '', cleaned)
    cleaned = re.sub(r'\(.*?\)', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


class GameVocalize:
    """Main orchestrator for GameVocalize."""

    def __init__(self):
        logger.info("Initializing GameVocalize engines...")

        self.config: AppConfig = load_config()

        logger.info("  [1/5] Capture engine...")
        self.capture = CaptureEngine(try_dxcam=False)

        logger.info("  [2/5] Preprocessor...")
        self.preprocessor = Preprocessor(config={
            "enabled": self.config.preprocess_enabled,
            "upscale_factor": self.config.upscale_factor,
        })

        logger.info("  [3/5] OCR engine (RapidOCR ONNX)...")
        self.ocr = OcrEngine(config={
            "min_confidence": self.config.ocr_confidence_threshold,
        })

        logger.info("  [4/5] Dedup engine...")
        self.dedup = DedupEngine(
            ttl=self.config.dedup_ttl,
            similarity_threshold=self.config.dedup_similarity,
        )

        logger.info("  [5/5] TTS engine (SAPI5)...")
        self.tts = TtsEngine(
            default_volume=self.config.speech_volume,
            default_voice=self.config.voice_name
        )

        self.hotkeys = HotkeyManager()

        self.active: bool = True
        self.auto_read: bool = False
        self.story_mode: bool = False
        self.movie_mode: bool = False
        self.last_frame: np.ndarray | None = None
        self.last_spoken_text: str = ""
        self._auto_read_thread: threading.Thread | None = None
        self._movie_thread: threading.Thread | None = None
        self._stop_auto_event = threading.Event()
        self._stop_movie_event = threading.Event()

        profile = self.config.current_profile
        self.roi_regions: list[tuple[int, int, int, int]] = [
            tuple(r) for r in self.config.roi_profiles.get(profile, [])
        ]

        logger.info("Starting CustomTkinter GUI Window...")
        self.gui = AppGUI(controller=self)

        sapi_rate = int((self.config.speech_rate - 200) / 15)
        self.tts.set_rate(sapi_rate)
        self.tts.set_volume(self.config.speech_volume)

        self._register_hotkeys()
        self._register_story_advance_hooks()

        logger.info("GameVocalize initialized successfully.")

    def _register_hotkeys(self):
        def safe_dispatch(func):
            return lambda: self.gui.after(0, func)

        self.hotkeys.register('toggle_movie_mode', safe_dispatch(self.toggle_movie_mode))
        self.hotkeys.register('toggle_reader', safe_dispatch(self.toggle_reader))
        self.hotkeys.register('full_screen_read', safe_dispatch(self.read_full_screen))
        self.hotkeys.register('region_read', safe_dispatch(self.read_regions))
        self.hotkeys.register('toggle_auto_read', safe_dispatch(self.toggle_story_mode))
        self.hotkeys.register('define_roi', safe_dispatch(self.define_roi))
        self.hotkeys.register('stop_speech', safe_dispatch(self.stop_speech))
        self.hotkeys.register('increase_speed', safe_dispatch(self.increase_speed))
        self.hotkeys.register('decrease_speed', safe_dispatch(self.decrease_speed))
        self.hotkeys.register('quit_app', safe_dispatch(self.quit_app))

        self.hotkeys.start()

    def _register_story_advance_hooks(self):
        def on_advance_key(e):
            if self.story_mode and self.active:
                logger.debug(f"Story advance key pressed ({e.name}). Triggering instant scan...")
                threading.Timer(0.06, self._scan_story_region_now).start()

        try:
            keyboard.on_press_key('space', on_advance_key, suppress=False)
            keyboard.on_press_key('enter', on_advance_key, suppress=False)
            keyboard.on_press_key('e', on_advance_key, suppress=False)
        except Exception as ex:
            logger.warning(f"Could not register story advance key hooks: {ex}")

    # ------------------------------------------------------------------
    # 🎬 Movie & Video Subtitle Mode
    # ------------------------------------------------------------------

    def toggle_movie_mode(self) -> None:
        if not self.movie_mode:
            self.start_movie_mode()
        else:
            self.stop_movie_mode()

    def start_movie_mode(self) -> None:
        if not self.roi_regions:
            self.set_bottom_subtitle_roi()

        if self.story_mode:
            self.stop_story_mode()

        self.movie_mode = True
        self.active = True
        self.last_spoken_text = ""
        self.gui.update_movie_mode_button(True)

        movie_sapi_rate = int((self.config.movie_speech_rate - 200) / 15)
        self.tts.set_rate(movie_sapi_rate)
        self.tts.set_volume(self.config.speech_volume)

        msg = "Movie Subtitle Mode ACTIVE (80ms Live Scan). Ready to read subtitles!"
        logger.info(msg)
        self.tts.speak("Movie subtitle mode active")
        self.gui.append_log(f"[System] 🎬 {msg}")

        self._stop_movie_event.clear()
        self._movie_thread = threading.Thread(
            target=self._movie_subtitle_loop, daemon=True, name="MovieSubtitleLoop"
        )
        self._movie_thread.start()

    def stop_movie_mode(self) -> None:
        self.movie_mode = False
        self._stop_movie_event.set()
        self.gui.update_movie_mode_button(False)
        self.tts.stop()

        msg = "Movie Subtitle Mode stopped."
        logger.info(msg)
        self.tts.speak(msg)
        self.gui.append_log(f"[System] ⏹ {msg}")

    def _movie_subtitle_loop(self) -> None:
        logger.info("Movie Subtitle Loop active (80ms ultra-fast polling)...")
        while not self._stop_movie_event.is_set() and self.movie_mode and self.active:
            interval = min(0.15, max(0.04, self.config.movie_scan_interval))
            try:
                if self.roi_regions:
                    frames = self.capture.grab_regions(self.roi_regions)
                    for frame in frames:
                        self._process_movie_frame(frame)
                else:
                    frame = self.capture.grab_full_screen()
                    if frame is not None:
                        self._process_movie_frame(frame)
            except Exception as e:
                logger.error(f"Movie subtitle loop error: {e}")

            self._stop_movie_event.wait(timeout=interval)

        logger.info("Movie Subtitle Loop stopped.")

    def _process_movie_frame(self, frame: np.ndarray) -> None:
        if frame is None or not self.active:
            return

        try:
            results = self.ocr.recognize(frame)
            if not results:
                return

            texts = [r.text.strip() for r in results if r.text.strip()]
            if not texts:
                return

            combined_raw = " ".join(texts)
            cleaned = clean_subtitle_text(combined_raw)
            if not cleaned or len(cleaned) < 2:
                return

            if cleaned == self.last_spoken_text:
                return

            if self.last_spoken_text and SequenceMatcher(None, cleaned, self.last_spoken_text).ratio() > 0.92:
                return

            self.last_spoken_text = cleaned
            logger.info(f"🎬 New Subtitle Detected: {cleaned}")

            self.tts.speak(cleaned)
            self.gui.append_log(f"[Subtitle] {cleaned}")

        except Exception as e:
            logger.error(f"Error processing movie subtitle frame: {e}")

    def set_bottom_subtitle_roi(self) -> None:
        try:
            screen_w = self.gui.winfo_screenwidth()
            screen_h = self.gui.winfo_screenheight()
        except Exception:
            screen_w = 1920
            screen_h = 1080

        w = int(screen_w * 0.90)
        h = int(screen_h * 0.20)
        x = int(screen_w * 0.05)
        y = int(screen_h * 0.78)

        self.roi_regions = [(x, y, w, h)]
        profile = self.config.current_profile
        self.config.roi_profiles[profile] = [[x, y, w, h]]
        save_config()

        msg = f"Auto-selected Bottom Subtitle Area: ({x}, {y}, {w}x{h})"
        logger.info(msg)
        self.tts.speak("Bottom subtitle area selected")
        self.gui.append_log(f"[System] 🎬 {msg}")
        self.gui.update_status_bar(f"Movie Subtitle Area Set: {w}x{h} at Bottom Screen")

    # ------------------------------------------------------------------
    # 🎮 Story Game Mode
    # ------------------------------------------------------------------

    def toggle_story_mode(self) -> None:
        if not self.story_mode:
            self.start_story_mode()
        else:
            self.stop_story_mode()

    def start_story_mode(self) -> None:
        if not self.roi_regions:
            logger.info("No dialogue box selected. Opening ROI selector first...")
            self.tts.speak("Please select the dialogue box region first.")
            self.gui.append_log("[System] Please select your game's Dialogue Box region.")
            self.define_roi()
            if not self.roi_regions:
                return

        if self.movie_mode:
            self.stop_movie_mode()

        self.story_mode = True
        self.auto_read = True
        self.last_spoken_text = ""
        self.gui.update_story_mode_button(True)

        msg = "Story Mode ACTIVE. Watching dialogue box page by page..."
        logger.info(msg)
        self.tts.speak("Story mode active")
        self.gui.append_log(f"[System] 📖 {msg}")

        self._stop_auto_event.clear()
        self._auto_read_thread = threading.Thread(
            target=self._story_read_loop, daemon=True, name="StoryReadLoop"
        )
        self._auto_read_thread.start()

    def stop_story_mode(self) -> None:
        self.story_mode = False
        self.auto_read = False
        self._stop_auto_event.set()
        self.gui.update_story_mode_button(False)
        self.tts.stop()

        msg = "Story Mode stopped."
        logger.info(msg)
        self.tts.speak(msg)
        self.gui.append_log(f"[System] ⏹ {msg}")

    def _story_read_loop(self) -> None:
        logger.info("Story Read Loop active (0.3s interval)...")
        while not self._stop_auto_event.is_set() and self.story_mode and self.active:
            interval = min(0.4, max(0.2, self.config.auto_read_interval))
            try:
                if self.roi_regions:
                    frames = self.capture.grab_regions(self.roi_regions)
                    for frame in frames:
                        self._process_frame(frame)
                else:
                    frame = self.capture.grab_full_screen()
                    if frame is not None:
                        self._process_frame(frame)
            except Exception as e:
                logger.error(f"Story read loop error: {e}")

            self._stop_auto_event.wait(timeout=interval)

        logger.info("Story Read Loop stopped.")

    def _scan_story_region_now(self) -> None:
        if not self.story_mode or not self.active:
            return
        try:
            if self.roi_regions:
                frames = self.capture.grab_regions(self.roi_regions)
                for frame in frames:
                    self._process_frame(frame)
        except Exception as e:
            logger.error(f"Instant story scan error: {e}")

    # ------------------------------------------------------------------
    # Standard Frame Processing & Actions
    # ------------------------------------------------------------------

    def _process_frame(self, frame: np.ndarray) -> None:
        if frame is None or not self.active:
            return

        try:
            results = self.ocr.recognize_with_preprocess(frame, preprocessor=self.preprocessor)
            if not results:
                return

            texts = [r.text.strip() for r in results if r.text.strip()]
            if not texts:
                return

            combined = " ".join(texts)

            if combined == self.last_spoken_text:
                return

            self.last_spoken_text = combined
            logger.info(f"Detected text on screen ({len(texts)} line(s)): {combined[:60]}...")

            self.tts.speak(combined)
            self.gui.append_log(combined)

        except Exception as e:
            logger.error(f"Error processing frame: {e}")

    def read_full_screen(self) -> None:
        if not self.active:
            logger.info("Reader is paused. Ignoring request.")
            return
        logger.info("Reading full screen...")
        self.tts.stop()
        self.last_spoken_text = ""
        try:
            frame = self.capture.grab_full_screen()
            if frame is not None:
                self._process_frame(frame)
            else:
                logger.warning("Screen capture returned None.")
        except Exception as e:
            logger.error(f"Failed to read full screen: {e}")

    def read_regions(self) -> None:
        if not self.active:
            logger.info("Reader is paused. Ignoring request.")
            return
        if not self.roi_regions:
            logger.warning("No ROI regions defined.")
            self.tts.speak("No regions defined. Click Select Region to define text areas.")
            self.gui.append_log("[System] No regions defined. Click 'Select Region' first.")
            return
        logger.info(f"Reading {len(self.roi_regions)} region(s)...")
        self.tts.stop()
        self.last_spoken_text = ""
        try:
            frames = self.capture.grab_regions(self.roi_regions)
            for frame in frames:
                self._process_frame(frame)
        except Exception as e:
            logger.error(f"Failed to read regions: {e}")

    def define_roi(self) -> None:
        logger.info("Opening ROI region selector...")
        self.tts.speak("Draw text regions on screen. Press Enter to confirm, Escape to cancel.")
        try:
            selector = RoiSelector(parent=self.gui)
            regions = selector.select()
            if regions is not None and len(regions) > 0:
                self.roi_regions = regions
                profile = self.config.current_profile
                self.config.roi_profiles[profile] = [list(r) for r in regions]
                save_config()
                msg = f"Saved {len(regions)} region(s)."
                logger.info(msg)
                self.tts.speak(msg)
                self.gui.append_log(f"[System] {msg}")
                self.gui.update_status_bar(
                    f"Engine Ready | Backend: {self.capture.backend} | Active Regions: {len(regions)}"
                )
            else:
                logger.info("ROI selection cancelled.")
                self.tts.speak("Region selection cancelled.")
                self.gui.append_log("[System] Region selection cancelled.")
        except Exception as e:
            logger.error(f"Failed to define ROI: {e}")

    def toggle_reader(self) -> None:
        self.active = not self.active
        status = "Active" if self.active else "Paused"
        logger.info(f"Reader state: {status}")
        self.gui.update_active_state(self.active)

        if self.active:
            self.tts.speak("Reader activated")
            self.gui.append_log("[System] Reader activated.")
        else:
            self.tts.speak("Reader paused")
            self.gui.append_log("[System] Reader paused.")
            self.stop_speech()

    def stop_speech(self) -> None:
        logger.info("Stopping speech")
        self.last_spoken_text = ""
        self.tts.stop()

    def set_volume(self, volume: int) -> None:
        self.config.speech_volume = volume
        self.tts.set_volume(volume)
        save_config()

    def set_voice(self, voice_name_or_keyword: str) -> None:
        self.config.voice_name = voice_name_or_keyword
        if "david" in voice_name_or_keyword.lower() or "male" in voice_name_or_keyword.lower():
            self.config.voice_gender = "Male"
        else:
            self.config.voice_gender = "Female"
        self.tts.set_voice(voice_name_or_keyword)
        save_config()
        gender = self.config.voice_gender
        logger.info(f"Switched voice to: {voice_name_or_keyword} ({gender})")
        self.gui.append_log(f"[System] 🎤 Switched voice to {gender} ({voice_name_or_keyword}).")

    def test_voice(self) -> None:
        gender = self.config.voice_gender
        sample_text = f"Hello! This is your sweet {gender.lower()} reader voice. I will read your game dialogues and movie subtitles clearly."
        self.tts.speak(sample_text)

    def increase_speed(self) -> None:
        self.config.speech_rate = min(400, self.config.speech_rate + 20)
        sapi_rate = int((self.config.speech_rate - 200) / 15)
        self.tts.set_rate(sapi_rate)
        self.gui.slider_speed.set(self.config.speech_rate)
        self.gui.lbl_speed.configure(text=f"Speech Speed: {self.config.speech_rate} WPM")
        self.tts.speak("Speed up")

    def decrease_speed(self) -> None:
        self.config.speech_rate = max(50, self.config.speech_rate - 20)
        sapi_rate = int((self.config.speech_rate - 200) / 15)
        self.tts.set_rate(sapi_rate)
        self.gui.slider_speed.set(self.config.speech_rate)
        self.gui.lbl_speed.configure(text=f"Speech Speed: {self.config.speech_rate} WPM")
        self.tts.speak("Speed down")

    def quit_app(self) -> None:
        logger.info("Shutting down GameVocalize...")
        self.active = False
        self.auto_read = False
        self.story_mode = False
        self.movie_mode = False
        self._stop_auto_event.set()
        self._stop_movie_event.set()

        try:
            self.hotkeys.stop()
        except Exception as e:
            logger.error(f"Error stopping hotkeys: {e}")

        try:
            self.tts.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down TTS: {e}")

        save_config()
        logger.info("GameVocalize shutdown complete.")

    def run(self) -> None:
        logger.info("GameVocalize Desktop GUI ready. Entering mainloop...")
        self.tts.speak("GameVocalize ready")
        self.gui.append_log("[System] GameVocalize Desktop GUI initialized and ready.")
        self.gui.mainloop()


if __name__ == '__main__':
    app = GameVocalize()
    app.run()
