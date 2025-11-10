"""
Podcast Duet GUI - Two-speaker podcast synthesis application.

Parses A:/B: dialog scripts and synthesizes them using MacTTS.
"""

__version__ = "0.1.0"

# Core modules (no GUI dependency)
from .parser_rules import parse_script, ScriptParser, TimelineEvent
from .engine_bridge import get_bridge, MacTTSBridge, Voice
from .audio_pipeline import AudioPipeline, SpeakerSettings

# GUI modules (lazy import to avoid Qt dependencies in tests)
def get_app():
    """Lazy import of GUI application."""
    from .app import main, PodcastDuetWindow
    return main, PodcastDuetWindow

__all__ = [
    'parse_script',
    'ScriptParser',
    'TimelineEvent',
    'get_bridge',
    'MacTTSBridge',
    'Voice',
    'AudioPipeline',
    'SpeakerSettings',
    'get_app',
]
