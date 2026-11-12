"""
config.py - Dataclass-based configuration hub for GameVocalize.
Thread-safe singleton using RLock to prevent deadlocks.
"""

import json
import logging
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"


@dataclass
class AppConfig:
    ocr_confidence_threshold: float = 0.40
    auto_read_interval: float = 0.4
    speech_rate: int = 240
    speech_volume: int = 100
    movie_scan_interval: float = 0.08
    movie_speech_rate: int = 240
    pixel_diff_threshold: float = 0.02
    dedup_similarity: float = 0.85
    dedup_ttl: float = 4.0
    roi_profiles: dict[str, list[tuple[int, int, int, int]]] = field(default_factory=dict)
    current_profile: str = 'default'
    ocr_language: str = 'en'
    preprocess_enabled: bool = True
    upscale_factor: float = 2.0
    voice_name: str = "Microsoft Zira Desktop - English (United States)"
    voice_gender: str = "Female"


class ConfigManager:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance.config = AppConfig()
                cls._instance.config_path = CONFIG_PATH
        return cls._instance

    def load(self):
        with self._lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    for k, v in data.items():
                        if hasattr(self.config, k):
                            setattr(self.config, k, v)
                    logger.info(f"Loaded config from {self.config_path}")
                except Exception as e:
                    logger.error(f"Failed to load config: {e}. Using defaults.")
            else:
                logger.info(f"Config file {self.config_path} not found. Creating with defaults.")
                self.save()

    def save(self):
        with self._lock:
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(asdict(self.config), f, indent=4)
                logger.info(f"Saved config to {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to save config: {e}")


# Global singleton instance
_config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Return the singleton AppConfig object."""
    return _config_manager.config


def load_config() -> AppConfig:
    """Load configuration from disk and return the config object."""
    _config_manager.load()
    return _config_manager.config


def save_config() -> None:
    """Save the current configuration to disk."""
    _config_manager.save()


# Initialize on import
load_config()
