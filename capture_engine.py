"""
capture_engine.py - Screen capture engine for GameVocalize.
Supports DXCam (DirectX GPU capture), MSS (GDI fallback), and PIL ImageGrab.
Exception-safe initialization and frame grabbing.
"""

import logging
import threading
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# DXCam (DirectX Desktop Duplication)
DXCAM_AVAILABLE = False
try:
    import dxcam
    DXCAM_AVAILABLE = True
except (Exception, SystemExit, BaseException) as e:
    logger.warning(f"dxcam import failed: {e}")

# MSS (Fast GDI Screen Capture)
MSS_AVAILABLE = False
try:
    import mss
    MSS_AVAILABLE = True
except (Exception, SystemExit, BaseException) as e:
    logger.warning(f"mss import failed: {e}")

# PIL ImageGrab Fallback
PIL_GRAB_AVAILABLE = False
try:
    from PIL import ImageGrab
    PIL_GRAB_AVAILABLE = True
except (Exception, SystemExit, BaseException) as e:
    logger.warning(f"PIL ImageGrab import failed: {e}")

from config import get_config


class CaptureEngine:
    """High-performance screen capture engine with pixel-diff detection."""

    def __init__(self, try_dxcam: bool = True):
        self._lock = threading.Lock()
        self.backend = None
        self.camera = None
        self.sct = None
        self._try_dxcam = try_dxcam

        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the best available capture backend."""
        with self._lock:
            if DXCAM_AVAILABLE and self._try_dxcam:
                try:
                    self.camera = dxcam.create(output_idx=0, output_color='BGR')
                    if self.camera is not None:
                        self.backend = 'dxcam'
                        logger.info("Initialized CaptureEngine with dxcam backend.")
                        return
                except (Exception, SystemExit, BaseException) as e:
                    logger.warning(f"Failed to initialize dxcam ({e}). Falling back to mss/PIL...")
                    self.camera = None

            if MSS_AVAILABLE:
                try:
                    if hasattr(mss, 'MSS'):
                        self.sct = mss.MSS()
                    else:
                        self.sct = mss.mss()
                    self.backend = 'mss'
                    logger.info("Initialized CaptureEngine with mss fallback backend.")
                    return
                except (Exception, SystemExit, BaseException) as e:
                    logger.warning(f"Failed to initialize mss ({e}). Falling back to PIL...")
                    self.sct = None

            if PIL_GRAB_AVAILABLE:
                self.backend = 'pil'
                logger.info("Initialized CaptureEngine with PIL ImageGrab fallback backend.")
                return

            logger.error("No valid screen capture backend could be initialized.")

    def grab_full_screen(self) -> np.ndarray | None:
        """Capture the entire screen."""
        with self._lock:
            if self.backend == 'dxcam' and self.camera:
                try:
                    frame = self.camera.grab()
                    if frame is not None:
                        return frame
                except (Exception, SystemExit, BaseException) as e:
                    logger.error(f"dxcam grab failed: {e}")

            if self.sct:
                try:
                    monitor = self.sct.monitors[1]
                    sct_img = self.sct.grab(monitor)
                    frame = np.array(sct_img)
                    if frame.shape[2] == 4:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    return frame
                except (Exception, SystemExit, BaseException) as e:
                    logger.error(f"mss grab failed: {e}")

            if PIL_GRAB_AVAILABLE:
                try:
                    img = ImageGrab.grab()
                    if img is not None:
                        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                        return frame
                except (Exception, SystemExit, BaseException) as e:
                    logger.error(f"PIL ImageGrab failed: {e}")

        return None

    def grab_region(self, x: int, y: int, w: int, h: int) -> np.ndarray | None:
        """Capture a specific region of the screen (x, y, width, height)."""
        left, top, right, bottom = x, y, x + w, y + h

        with self._lock:
            if self.backend == 'dxcam' and self.camera:
                try:
                    frame = self.camera.grab(region=(left, top, right, bottom))
                    if frame is not None:
                        return frame
                except (Exception, SystemExit, BaseException) as e:
                    logger.error(f"dxcam grab_region failed: {e}")

            if self.sct:
                try:
                    monitor = {"top": top, "left": left, "width": w, "height": h}
                    sct_img = self.sct.grab(monitor)
                    frame = np.array(sct_img)
                    if frame.shape[2] == 4:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    return frame
                except (Exception, SystemExit, BaseException) as e:
                    logger.error(f"mss grab_region failed: {e}")

            if PIL_GRAB_AVAILABLE:
                try:
                    img = ImageGrab.grab(bbox=(left, top, right, bottom))
                    if img is not None:
                        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                        return frame
                except (Exception, SystemExit, BaseException) as e:
                    logger.error(f"PIL grab_region failed: {e}")

        return None

    def grab_regions(self, regions: list[tuple[int, int, int, int]]) -> list[np.ndarray]:
        """Capture multiple specific regions of the screen."""
        frames = []
        for (x, y, w, h) in regions:
            frame = self.grab_region(x, y, w, h)
            if frame is not None:
                frames.append(frame)
        return frames

    def has_changed(self, current_frame: np.ndarray, previous_frame: np.ndarray, threshold: float = None) -> bool:
        """
        Check if current frame differs from previous frame by more than threshold.
        Downscales both frames to 1/4 size and converts to grayscale for fast comparison.
        """
        if current_frame is None or previous_frame is None:
            return True

        if current_frame.shape != previous_frame.shape:
            return True

        if threshold is None:
            config = get_config()
            threshold = config.pixel_diff_threshold

        try:
            h, w = current_frame.shape[:2]
            new_dim = (w // 4, h // 4)

            if new_dim[0] > 0 and new_dim[1] > 0:
                curr_small = cv2.resize(current_frame, new_dim, interpolation=cv2.INTER_AREA)
                prev_small = cv2.resize(previous_frame, new_dim, interpolation=cv2.INTER_AREA)
            else:
                curr_small = current_frame
                prev_small = previous_frame

            curr_gray = cv2.cvtColor(curr_small, cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.cvtColor(prev_small, cv2.COLOR_BGR2GRAY)

            diff = cv2.absdiff(curr_gray, prev_gray)
            mean_diff = np.mean(diff) / 255.0

            return mean_diff > threshold

        except (Exception, SystemExit, BaseException) as e:
            logger.error(f"Error computing frame diff: {e}")
            return True
