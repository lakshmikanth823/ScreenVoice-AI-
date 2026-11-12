"""
tray_app.py - System tray app integration using pystray.
"""

import logging
from typing import Callable, Dict
from PIL import Image, ImageDraw

try:
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pystray = None
    item = None

logger = logging.getLogger(__name__)


class TrayApp:
    """System tray application for GameVocalize using pystray."""

    def __init__(self, callbacks: Dict[str, Callable]):
        self.callbacks = callbacks
        self.icon = None
        self.active = True

        if pystray is None:
            logger.error("pystray is not installed. System tray icon will not be available.")
            return

        self._setup_icon()

    def _create_image(self, active: bool) -> Image.Image:
        width = 64
        height = 64
        color1 = (30, 30, 30)
        color2 = (0, 255, 0) if active else (128, 128, 128)

        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        margin = 8
        dc.ellipse([margin, margin, width - margin, height - margin], fill=color2)
        return image

    def _setup_icon(self) -> None:
        if pystray is None:
            return

        menu = pystray.Menu(
            item('GameVocalize', lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item('Movie Subtitles (Ctrl+Alt+M)', self._wrap_callback('toggle_movie_mode')),
            item('Toggle Reader (Ctrl+Alt+X)', self._wrap_callback('toggle_reader')),
            item('Read Screen (Ctrl+Alt+F)', self._wrap_callback('full_screen_read')),
            item('Read Regions (Ctrl+Alt+R)', self._wrap_callback('region_read')),
            item('Toggle Auto-Read (Ctrl+Alt+A)', self._wrap_callback('toggle_auto_read')),
            item('Define Regions (Ctrl+Alt+D)', self._wrap_callback('define_roi')),
            pystray.Menu.SEPARATOR,
            item('Quit (Ctrl+Alt+Q)', self._wrap_callback('quit_app'))
        )

        image = self._create_image(self.active)
        self.icon = pystray.Icon("GameVocalize", image, "GameVocalize (Active)", menu)

    def _wrap_callback(self, action_name: str) -> Callable:
        def wrapper(icon, item):
            if action_name in self.callbacks:
                try:
                    self.callbacks[action_name]()
                except Exception as e:
                    logger.error(f"Error executing callback {action_name}: {e}")
            else:
                logger.warning(f"No callback found for {action_name}")
        return wrapper

    def start(self) -> None:
        if self.icon:
            logger.info("Starting system tray icon...")
            self.icon.run()

    def stop(self) -> None:
        if self.icon:
            logger.info("Stopping system tray icon...")
            self.icon.stop()

    def update_status(self, active: bool) -> None:
        self.active = active
        if self.icon:
            try:
                self.icon.icon = self._create_image(self.active)
                self.icon.title = "GameVocalize (Active)" if self.active else "GameVocalize (Paused)"
            except Exception as e:
                logger.error(f"Error updating tray status: {e}")
