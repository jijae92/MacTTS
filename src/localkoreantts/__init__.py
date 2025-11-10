"""
LocalKoreanTTS public package interface.

The package exposes a thin facade over the synthesis engine, filesystem
paths, and entry points so both the CLI and GUI can share the same core
logic regardless of platform.
"""

from .config import describe_environment, get_paths
from .engine import LocalKoreanTTSEngine, VoiceProfile
from .paths import PathConfig, resolve_path_config

__all__ = [
    "LocalKoreanTTSEngine",
    "VoiceProfile",
    "PathConfig",
    "resolve_path_config",
    "get_paths",
    "describe_environment",
]

__version__ = "0.1.0"
