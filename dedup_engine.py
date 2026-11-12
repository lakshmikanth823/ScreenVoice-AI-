"""
dedup_engine.py - Fuzzy text deduplication engine for GameVocalize.
"""

import time
import logging
import threading
from difflib import SequenceMatcher
from typing import List, Tuple

logger = logging.getLogger(__name__)


class DedupEngine:
    """Fuzzy text deduplication engine to prevent re-reading the same text."""

    def __init__(self, ttl: float = 4.0, similarity_threshold: float = 0.85):
        self.ttl = ttl
        self.similarity_threshold = similarity_threshold
        self._cache: List[Tuple[str, float]] = []
        self._lock = threading.Lock()

    def cleanup(self) -> None:
        """Remove expired entries from the cache."""
        now = time.time()
        with self._lock:
            original_len = len(self._cache)
            self._cache = [(text, timestamp) for text, timestamp in self._cache
                           if now - timestamp <= self.ttl]
            removed = original_len - len(self._cache)
            if removed > 0:
                logger.debug(f"DedupEngine cleanup: removed {removed} expired entries.")

    def is_duplicate(self, text: str) -> bool:
        """Check if the text was recently spoken."""
        if not text or not text.strip():
            return True

        self.cleanup()

        with self._lock:
            for cached_text, _ in self._cache:
                ratio = SequenceMatcher(None, text, cached_text).ratio()
                if ratio >= self.similarity_threshold:
                    logger.debug(f"DedupEngine: Match found for '{text}' (ratio: {ratio:.2f})")
                    return True
        return False

    def add(self, text: str) -> None:
        """Add text to the cache with current timestamp."""
        if not text or not text.strip():
            return

        with self._lock:
            self._cache.append((text, time.time()))
            logger.debug("DedupEngine: Added text to cache.")

    def filter_new(self, texts: List[str]) -> List[str]:
        """Return only texts not in the cache, and add the new ones to cache."""
        new_texts = []
        for text in texts:
            if not self.is_duplicate(text):
                new_texts.append(text)
                self.add(text)
        return new_texts

    def clear(self) -> None:
        """Clear the entire cache."""
        with self._lock:
            self._cache.clear()
            logger.info("DedupEngine: Cache cleared.")
