#!/usr/bin/env python3
"""
Edge TTS backend for natural, high-quality Korean speech synthesis.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

try:
    import edge_tts
    from pydub import AudioSegment
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class EdgeTTSBackend:
    """Edge TTS backend using Microsoft Edge Neural voices."""

    # Korean voice mappings
    VOICE_MAP = {
        'Yuna': 'ko-KR-SunHiNeural',       # Female, clear and professional
        'Jinho': 'ko-KR-InJoonNeural',      # Male, natural and warm
        'Default': 'ko-KR-SunHiNeural',     # Default to SunHi
        'Female': 'ko-KR-SunHiNeural',
        'Male': 'ko-KR-InJoonNeural',
        'SunHi': 'ko-KR-SunHiNeural',
        'InJoon': 'ko-KR-InJoonNeural',
        'JiMin': 'ko-KR-JiMinNeural',       # Female, young and energetic
        'BongJin': 'ko-KR-BongJinNeural',   # Male, mature and authoritative
        'GookMin': 'ko-KR-GookMinNeural',   # Male, friendly
        'Hyunsu': 'ko-KR-HyunsuNeural',     # Male, professional
        'SeoHyeon': 'ko-KR-SeoHyeonNeural', # Female, gentle
        'SoonBok': 'ko-KR-SoonBokNeural',   # Female, warm and soft
        'YuJin': 'ko-KR-YuJinNeural',       # Female, lively and energetic
    }

    def __init__(self):
        """Initialize Edge TTS backend."""
        if not EDGE_TTS_AVAILABLE:
            raise ImportError(
                "edge-tts is required. Install with: pip install edge-tts pydub"
            )

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice_name: str = "Yuna",
        rate_wpm: int = 180,
        **kwargs
    ) -> Path:
        """
        Synthesize speech using Edge TTS.

        Args:
            text: Text to synthesize
            output_path: Output WAV file path
            voice_name: Voice name (Yuna, Jinho, etc.)
            rate_wpm: Speech rate in words per minute (120-250)
            **kwargs: Additional parameters (ignored for compatibility)

        Returns:
            Path to generated audio file
        """
        # Get edge voice ID
        edge_voice = self.VOICE_MAP.get(voice_name, 'ko-KR-SunHiNeural')

        # Convert WPM to rate percentage
        # Average Korean reading speed is ~180 WPM
        # Edge TTS rate: -50% to +100%
        rate_percent = int(((rate_wpm - 180) / 180) * 100)
        rate_percent = max(-50, min(100, rate_percent))  # Clamp to valid range
        rate_str = f"{rate_percent:+d}%"

        # Create temp file for MP3 output
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Synthesize with edge-tts
            async def _synthesize():
                communicate = edge_tts.Communicate(
                    text,
                    edge_voice,
                    rate=rate_str,
                    volume="+0%"  # Keep volume at 0% (default)
                )
                await communicate.save(tmp_path)

            # Run async synthesis
            asyncio.run(_synthesize())

            # Convert MP3 to WAV
            audio = AudioSegment.from_mp3(tmp_path)
            audio.export(str(output_path), format='wav')

            return output_path

        finally:
            # Clean up temp MP3 file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        voice_name: str = "Yuna",
        rate_wpm: int = 180,
        **kwargs,
    ) -> Path:
        """
        Compatibility wrapper used by dialog-tts. Ensures directories exist and
        delegates to synthesize().
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return self.synthesize(
            text=text,
            output_path=output_path,
            voice_name=voice_name,
            rate_wpm=rate_wpm,
            **kwargs,
        )

    def list_voices(self) -> list[str]:
        """List available voices."""
        return list(self.VOICE_MAP.keys())

    def get_voice_info(self, voice_name: str) -> dict:
        """Get voice information."""
        edge_voice = self.VOICE_MAP.get(voice_name, 'ko-KR-SunHiNeural')
        return {
            'name': voice_name,
            'edge_voice': edge_voice,
            'language': 'ko-KR',
            'gender': 'Female' if 'Female' in voice_name or voice_name in ['Yuna', 'SunHi', 'JiMin', 'SeoHyeon'] else 'Male'
        }
