"""
tts_engine.py - Windows SAPI5 text-to-speech engine for GameVocalize.
Instant speech purging using SVSFPurgeBeforeSpeak (flag 3) to ensure only
the text currently present on screen is spoken without backlog.
Includes Female (Zira) and Male (David) voice selection and volume control.
"""

import threading
import queue
import logging
from typing import List, Dict, Optional
import pythoncom
import win32com.client

logger = logging.getLogger(__name__)

# SAPI5 Flags
# SVSFlagsAsync = 1
# SVSFPurgeBeforeSpeak = 2
# SVSFlagsAsync | SVSFPurgeBeforeSpeak = 3 (Purge old audio buffer & speak immediately)
SPEAK_PURGE_ASYNC = 3


def get_system_voices() -> List[Dict[str, str]]:
    """Enumerate all available SAPI5 voices on the system."""
    voices_list = []
    try:
        pythoncom.CoInitialize()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        tokens = voice.GetVoices()
        for i in range(tokens.Count):
            token = tokens.Item(i)
            desc = token.GetDescription()
            gender = "Female" if any(k in desc.lower() for k in ["zira", "eva", "female", "hazel", "catherine", "helen"]) else "Male"
            voices_list.append({
                "index": i,
                "name": desc,
                "id": token.Id,
                "gender": gender
            })
    except Exception as e:
        logger.error(f"Error enumerating system voices: {e}")
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    return voices_list


class TtsEngine:
    """Windows SAPI5 text-to-speech engine with instant buffer purge, volume, and voice selection."""

    def __init__(self, default_rate: int = 2, default_volume: int = 100, default_voice: str = "Zira"):
        self._rate = default_rate
        self._volume = max(0, min(100, default_volume))
        self._voice_name = default_voice
        self._current_voice_desc = ""
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._shutdown_event = threading.Event()

        self._thread = threading.Thread(target=self._speech_loop, daemon=True, name="TTS_Engine_Thread")
        self._thread.start()
        logger.info(f"TtsEngine initialized with voice='{self._voice_name}', volume={self._volume}%, rate={self._rate}.")

    def _apply_voice(self, voice_com, target_name: str) -> None:
        """Find and assign voice token matching target_name or gender keyword."""
        try:
            tokens = voice_com.GetVoices()
            target_lower = target_name.lower()

            # 1. Exact or partial name match
            for i in range(tokens.Count):
                token = tokens.Item(i)
                desc = token.GetDescription()
                if target_lower in desc.lower():
                    voice_com.Voice = token
                    self._current_voice_desc = desc
                    logger.info(f"TTS voice set to: {desc}")
                    return

            # 2. Gender keyword match
            if "female" in target_lower:
                for i in range(tokens.Count):
                    token = tokens.Item(i)
                    desc = token.GetDescription().lower()
                    if any(name in desc for name in ["zira", "eva", "hazel", "catherine", "helen"]):
                        voice_com.Voice = token
                        self._current_voice_desc = token.GetDescription()
                        logger.info(f"TTS voice set to female: {self._current_voice_desc}")
                        return

            if tokens.Count > 0:
                voice_com.Voice = tokens.Item(0)
                self._current_voice_desc = tokens.Item(0).GetDescription()

        except Exception as e:
            logger.error(f"Error applying voice '{target_name}': {e}")

    def _speech_loop(self) -> None:
        """Dedicated thread loop for SAPI5 processing."""
        try:
            pythoncom.CoInitialize()
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            logger.debug("SAPI.SpVoice COM object created successfully.")

            applied_voice_name = None

            while not self._shutdown_event.is_set():
                try:
                    if applied_voice_name != self._voice_name:
                        self._apply_voice(voice, self._voice_name)
                        applied_voice_name = self._voice_name

                    text = self._queue.get(timeout=0.05)

                    if text is None:
                        break

                    voice.Rate = self._rate
                    voice.Volume = self._volume

                    if self._stop_event.is_set() or not text.strip():
                        voice.Speak("", SPEAK_PURGE_ASYNC)
                    else:
                        logger.debug(f"Speaking ({self._current_voice_desc}, vol={self._volume}, rate={self._rate}): {text[:40]}...")
                        voice.Speak(text, SPEAK_PURGE_ASYNC)

                    self._queue.task_done()

                except queue.Empty:
                    continue

        except Exception as e:
            logger.error(f"Error in TTS speech loop: {e}")
        finally:
            pythoncom.CoUninitialize()
            logger.info("TTS thread exiting and COM uninitialized.")

    def speak(self, text: str) -> None:
        """Speak text immediately, purging any previously queued speech."""
        if not text or not text.strip():
            self.stop()
            return

        try:
            while not self._queue.empty():
                self._queue.get_nowait()
                self._queue.task_done()
        except queue.Empty:
            pass

        self._stop_event.clear()
        self._queue.put(text)

    def stop(self) -> None:
        """Immediately purge Windows SAPI5 audio buffer and stop speech."""
        self._stop_event.set()

        try:
            while not self._queue.empty():
                self._queue.get_nowait()
                self._queue.task_done()
        except queue.Empty:
            pass

        self._queue.put("")
        logger.info("Instant speech purge dispatched.")

    def set_voice(self, voice_name_or_keyword: str) -> None:
        """Switch speech voice (e.g. 'Zira', 'David', 'Female', 'Male')."""
        self._voice_name = voice_name_or_keyword
        logger.info(f"Requested voice change to: {voice_name_or_keyword}")

    def get_current_voice(self) -> str:
        return self._current_voice_desc or self._voice_name

    def set_rate(self, rate: int) -> None:
        self._rate = max(-10, min(10, rate))
        logger.info(f"TTS rate set to {self._rate}")

    def increase_rate(self) -> None:
        self.set_rate(self._rate + 1)

    def decrease_rate(self) -> None:
        self.set_rate(self._rate - 1)

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, volume))
        logger.info(f"TTS volume set to {self._volume}%")

    def get_volume(self) -> int:
        return self._volume

    def increase_volume(self, delta: int = 10) -> None:
        self.set_volume(self._volume + delta)

    def decrease_volume(self, delta: int = 10) -> None:
        self.set_volume(self._volume - delta)

    def shutdown(self) -> None:
        self.stop()
        self._shutdown_event.set()
        self._queue.put(None)
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("TtsEngine shutdown complete.")
