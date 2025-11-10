"""
Bridge to MacTTS (LocalKoreanTTS) engine.

Tries import first, falls back to CLI subprocess if needed.
"""

from __future__ import annotations

import subprocess
import tempfile
import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class Voice:
    """TTS voice information."""
    name: str
    engine: str  # 'edge', 'gtts', 'coqui'
    language: str = 'ko'

    def __repr__(self) -> str:
        return f"{self.name} ({self.engine})"


class MacTTSBridge:
    """
    Bridge to MacTTS engine.

    Attempts to use the library directly, falls back to CLI.
    """

    def __init__(self):
        self.use_import = False
        self.engine = None
        self._voices_cache: Optional[List[Voice]] = None

        # Try to import LocalKoreanTTS
        try:
            from localkoreantts.engine import LocalKoreanTTSEngine
            from localkoreantts.paths import resolve_path_config

            config = resolve_path_config().ensure()
            self.engine = LocalKoreanTTSEngine(path_config=config)
            self.use_import = True
            print("✓ MacTTS engine loaded via import")
        except Exception as e:
            print(f"⚠️  MacTTS import failed, will use CLI: {e}")
            self.use_import = False

    def get_voices(self) -> List[Voice]:
        """
        Get available TTS voices.

        Returns:
            List of Voice objects
        """
        if self._voices_cache:
            return self._voices_cache

        if self.use_import:
            voices = self._get_voices_import()
        else:
            voices = self._get_voices_cli()

        self._voices_cache = voices
        return voices

    def _get_voices_import(self) -> List[Voice]:
        """Get voices via direct import."""
        voices = []

        try:
            voice_objs = self.engine.voices()
            for v in voice_objs:
                voices.append(Voice(
                    name=v.name,
                    engine=v.engine_name if hasattr(v, 'engine_name') else 'unknown',
                    language='ko'
                ))
        except Exception as e:
            print(f"Error getting voices via import: {e}")

        return voices

    def _get_voices_cli(self) -> List[Voice]:
        """Get voices via CLI command."""
        voices = []

        try:
            # Try: localkoreantts --list-voices
            result = subprocess.run(
                ['localkoreantts', '--list-voices'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                voices = self._parse_voice_list(result.stdout)
            else:
                # Try: python -m localkoreantts.cli --list-voices
                result = subprocess.run(
                    ['python', '-m', 'localkoreantts.cli', '--list-voices'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    voices = self._parse_voice_list(result.stdout)

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Error getting voices via CLI: {e}")

        # Fallback: common Edge TTS Korean voices
        if not voices:
            print("Using fallback voice list")
            voices = self._get_fallback_voices()

        return voices

    def _parse_voice_list(self, output: str) -> List[Voice]:
        """Parse output from --list-voices command."""
        voices = []

        # Look for lines like:
        # - SunHi (edge/ko-KR)
        # - ko-KR-SunHiNeural (edge)
        pattern = re.compile(r'^\s*-?\s*(\S+)\s*\((\w+)[/,]?.*\)', re.MULTILINE)

        for match in pattern.finditer(output):
            name = match.group(1)
            engine = match.group(2).lower()

            voices.append(Voice(
                name=name,
                engine=engine,
                language='ko'
            ))

        return voices

    def _get_fallback_voices(self) -> List[Voice]:
        """Return hardcoded fallback Korean voices."""
        return [
            Voice('SunHi', 'edge', 'ko'),
            Voice('JiMin', 'edge', 'ko'),
            Voice('SeoHyeon', 'edge', 'ko'),
            Voice('InJoon', 'edge', 'ko'),
            Voice('Hyunsu', 'edge', 'ko'),
            Voice('GookMin', 'edge', 'ko'),
        ]

    def synthesize(
        self,
        text: str,
        voice_name: str,
        output_path: Path,
        speed: float = 1.0
    ) -> Path:
        """
        Synthesize text to audio file.

        Args:
            text: Text to synthesize
            voice_name: Voice name to use
            output_path: Where to save the audio
            speed: Speech rate multiplier (0.5 - 2.0)

        Returns:
            Path to generated audio file

        Raises:
            RuntimeError: If synthesis fails
        """
        if self.use_import:
            return self._synthesize_import(text, voice_name, output_path, speed)
        else:
            return self._synthesize_cli(text, voice_name, output_path, speed)

    def _synthesize_import(
        self,
        text: str,
        voice_name: str,
        output_path: Path,
        speed: float
    ) -> Path:
        """Synthesize via direct import."""
        try:
            result = self.engine.synthesize_to_file(
                text=text,
                voice_name=voice_name,
                output_path=output_path,
                speed=speed
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Synthesis failed: {e}")

    def _synthesize_cli(
        self,
        text: str,
        voice_name: str,
        output_path: Path,
        speed: float
    ) -> Path:
        """Synthesize via CLI subprocess."""

        # Save text to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(text)
            text_file = Path(f.name)

        try:
            # Build command
            cmd = [
                'localkoreantts',
                '--voice', voice_name,
                '--output', str(output_path),
                '--text-file', str(text_file)
            ]

            if speed != 1.0:
                cmd.extend(['--speed', str(speed)])

            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # Try python -m fallback
                cmd[0:1] = ['python', '-m', 'localkoreantts.cli']
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            if result.returncode != 0:
                raise RuntimeError(f"CLI synthesis failed: {result.stderr}")

            if not output_path.exists():
                raise RuntimeError(f"Output file not created: {output_path}")

            return output_path

        finally:
            # Clean up temp file
            text_file.unlink(missing_ok=True)


# Global singleton instance
_bridge_instance: Optional[MacTTSBridge] = None


def get_bridge() -> MacTTSBridge:
    """Get or create the global MacTTS bridge instance."""
    global _bridge_instance

    if _bridge_instance is None:
        _bridge_instance = MacTTSBridge()

    return _bridge_instance
