"""
preprocessor.py - OpenCV Image Enhancement for Game & Video Text Recognition
Enhances resolution and contrast without destroying color text channels.
"""

import logging
import cv2
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Preprocessor:
    """OpenCV image preprocessing pipeline to enhance game screenshots and video subtitles for OCR accuracy."""

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        self.enabled = config.get("enabled", True)
        self.upscale_factor = config.get("upscale_factor", 2.0)

    def process(self, image: np.ndarray) -> np.ndarray:
        """
        Run preprocessing pipeline on image:
        1. Upscale if small or resolution is low
        2. Enhance contrast using CLAHE on L-channel of LAB color space
        """
        if not self.enabled or image is None or image.size == 0:
            return image

        try:
            processed = image.copy()

            # Ensure 3 channels
            if len(processed.shape) == 2:
                processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
            elif processed.shape[2] == 4:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGRA2BGR)

            h, w = processed.shape[:2]

            # 1. Upscale if image is small (either dimension < 300px)
            if h < 300 or w < 300:
                processed = self.upscale(processed, self.upscale_factor)

            # 2. Enhance contrast in LAB color space
            lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            processed = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

            return processed

        except Exception as e:
            logger.error(f"Error during preprocessing: {e}")
            return image

    def upscale(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Upscale the image by the given factor."""
        h, w = image.shape[:2]
        new_w = int(w * factor)
        new_h = int(h * factor)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
