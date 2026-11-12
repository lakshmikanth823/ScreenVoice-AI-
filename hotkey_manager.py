"""
hotkey_manager.py - Global keyboard hook manager for GameVocalize.
Thread-safe and works inside fullscreen games and media players.
"""

import logging
import threading
from typing import Callable, Dict
import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Manages global keyboard hooks for the application."""

    def __init__(self):
        self._callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._running = False

        self.bindings = {
            'ctrl+alt+m': 'toggle_movie_mode',
            'ctrl+alt+f': 'full_screen_read',
            'ctrl+alt+r': 'region_read',
            'ctrl+alt+d': 'define_roi',
            'ctrl+alt+a': 'toggle_auto_read',
            'ctrl+alt+s': 'stop_speech',
            'ctrl+alt+x': 'toggle_reader',
            'ctrl+alt+q': 'quit_app',
            'ctrl+alt+=': 'increase_speed',
            'ctrl+alt+-': 'decrease_speed',
        }

    def register(self, action: str, callback: Callable) -> None:
        with self._lock:
            self._callbacks[action] = callback

    def _execute_callback(self, action: str, hotkey: str) -> None:
        logger.info(f"Hotkey pressed: {hotkey} (Action: {action})")
        with self._lock:
            callback = self._callbacks.get(action)

        if callback:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error executing callback for {action}: {e}")
        else:
            logger.warning(f"No callback registered for action: {action}")

    def start(self) -> None:
        with self._lock:
            if self._running:
                return

            try:
                for hotkey, action in self.bindings.items():
                    keyboard.add_hotkey(
                        hotkey,
                        lambda a=action, h=hotkey: self._execute_callback(a, h),
                        suppress=False
                    )
                self._running = True
                logger.info("HotkeyManager started and hotkeys registered.")
            except Exception as e:
                logger.error(f"Failed to register hotkeys: {e}")

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return

            try:
                keyboard.unhook_all()
                self._running = False
                logger.info("HotkeyManager stopped and all hotkeys unhooked.")
            except Exception as e:
                logger.error(f"Failed to unhook hotkeys: {e}")
