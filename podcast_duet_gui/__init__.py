"""
Podcast Duet GUI - Two-speaker podcast synthesis application.

Parses A:/B: dialog scripts and synthesizes them using MacTTS.
"""

__version__ = "0.1.0"

from .app import main, PodcastDuetWindow
from .parser_rules import parse_script, ScriptParser, TimelineEvent
from .engine_bridge import get_bridge, MacTTSBridge, Voice
from .audio_pipeline import AudioPipeline, SpeakerSettings

__all__ = [
    'main',
    'PodcastDuetWindow',
    'parse_script',
    'ScriptParser',
    'TimelineEvent',
    'get_bridge',
    'MacTTSBridge',
    'Voice',
    'AudioPipeline',
    'SpeakerSettings',
]
