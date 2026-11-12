"""
ocr_engine.py - RapidOCR ONNX Engine for GameVocalize
High-accuracy PP-OCR text recognition running on ONNX Runtime.
Fast, lightweight, and 100% reliable for gaming UIs and video subtitles.
"""

import logging
import threading
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# RapidOCR (ONNX Runtime PaddleOCR engine)
try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False
    logger.warning("RapidOCR is not installed.")


@dataclass
class OcrResult:
    """Dataclass to hold OCR result information."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)


class OcrEngine:
    """RapidOCR text recognition engine powered by ONNX Runtime."""

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}

        self.min_confidence = config.get("min_confidence", 0.3)
        self.lock = threading.Lock()
        self.engine_type = None
        self.ocr = None

        if RAPIDOCR_AVAILABLE:
            try:
                self.ocr = RapidOCR()
                self.engine_type = "RapidOCR (ONNX)"
                logger.info("Initialized OcrEngine with RapidOCR ONNX backend.")
            except Exception as e:
                logger.error(f"Failed to initialize RapidOCR: {e}")
                self.ocr = None

        if self.ocr is None:
            logger.error("No valid OCR engine available.")

    def recognize(self, image: np.ndarray) -> List[OcrResult]:
        """
        Run OCR on the provided BGR image.
        Returns List of OcrResult sorted top-to-bottom, then left-to-right.
        """
        if image is None or image.size == 0:
            return []

        if self.ocr is None:
            return []

        try:
            with self.lock:
                raw_result, _ = self.ocr(image)

            if not raw_result:
                return []

            results = []
            for item in raw_result:
                if not item or len(item) < 3:
                    continue

                box = item[0]
                text = str(item[1]).strip()
                confidence = float(item[2])

                if not text or confidence < self.min_confidence:
                    continue

                xs = [point[0] for point in box]
                ys = [point[1] for point in box]
                x_min = int(min(xs))
                y_min = int(min(ys))
                x_max = int(max(xs))
                y_max = int(max(ys))
                w = max(1, x_max - x_min)
                h = max(1, y_max - y_min)

                results.append(OcrResult(text=text, confidence=confidence, bbox=(x_min, y_min, w, h)))

            def sort_key(res: OcrResult):
                y = res.bbox[1]
                x = res.bbox[0]
                return (y // 12, x)

            results.sort(key=sort_key)

            total_chars = sum(len(r.text) for r in results)
            if results:
                logger.info(f"OCR found {len(results)} text region(s), {total_chars} total char(s).")

            return results

        except Exception as e:
            logger.error(f"Error during OCR recognition: {e}")
            return []

    def recognize_with_preprocess(self, image: np.ndarray, preprocessor) -> List[OcrResult]:
        """
        Run OCR on image, trying raw image first, then preprocessed if needed.
        """
        if image is None or image.size == 0:
            return []

        results = self.recognize(image)
        if results:
            return results

        if preprocessor is not None:
            prep_image = preprocessor.process(image)
            return self.recognize(prep_image)

        return []
