"""TTS synthesis engine with multiple backend options."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
from array import array
from typing import Iterable, List, Optional
import wave
import os
import asyncio

from .paths import PathConfig, resolve_path_config

# Try importing edge-tts first (best quality for Korean)
edge_tts = None
_edge_tts_available = False

try:
    import edge_tts as EdgeTTS
    edge_tts = EdgeTTS
    _edge_tts_available = True
except ImportError:
    pass

# Fall back to gTTS (simpler, more reliable for Korean)
gTTS = None
_gtts_available = False

try:
    from gtts import gTTS as GoogleTTS
    from pydub import AudioSegment
    gTTS = GoogleTTS
    _gtts_available = True
except ImportError:
    pass

# Fall back to Coqui TTS if others not available
TTS = None
_coqui_available = False

if not _edge_tts_available and not _gtts_available:
    try:
        from TTS.api import TTS as CoquiTTS
        TTS = CoquiTTS
        _coqui_available = True
    except ImportError:
        pass


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    locale: str
    sample_rate: int = 22050
    edge_voice: Optional[str] = None  # edge-tts voice name


# Updated voice profiles with edge-tts support (Natural, high-quality Korean voices)
AVAILABLE_VOICES: List[VoiceProfile] = [
    VoiceProfile(name="standard-female", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-SunHiNeural"),
    VoiceProfile(name="standard-male", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-InJoonNeural"),
    VoiceProfile(name="natural-female", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-JiMinNeural"),
    VoiceProfile(name="natural-male", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-HyunsuNeural"),
    VoiceProfile(name="professional-female", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-SeoHyeonNeural"),
    VoiceProfile(name="professional-male", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-GookMinNeural"),
]


class LocalKoreanTTSEngine:
    """Produces speech synthesis using edge-tts, gTTS, Coqui TTS, or placeholder audio."""

    def __init__(
        self,
        path_config: Optional[PathConfig] = None,
        ffmpeg_path: Optional[Path] = None,
    ) -> None:
        self.path_config = (path_config or resolve_path_config()).ensure()
        self._voice_lookup = {voice.name: voice for voice in AVAILABLE_VOICES}
        self.ffmpeg_path = ffmpeg_path
        self._tts_model = None
        self._use_edge_tts = _edge_tts_available
        self._use_gtts = _gtts_available
        self._use_coqui = False

        # Prefer edge-tts (best quality for Korean with natural prosody)
        if self._use_edge_tts:
            print("Using Microsoft Edge TTS (edge-tts) for natural, high-quality Korean speech synthesis")
        # Fall back to gTTS (good quality, works offline)
        elif self._use_gtts:
            print("Using Google TTS (gTTS) for speech synthesis")
        # Fall back to Coqui TTS as last resort before placeholder
        elif _coqui_available:
            try:
                print("Loading Coqui TTS model...")
                self._tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
                self._use_coqui = True
                print("Coqui TTS model loaded successfully!")
            except Exception as e:
                print(f"Warning: Could not initialize Coqui TTS model: {e}")
                print("Falling back to placeholder audio generation")
        else:
            print("No TTS library available. Using placeholder audio generation.")
            print("Install edge-tts with: pip install edge-tts")
            print("Or install gTTS with: pip install gtts pydub")

    def voices(self) -> Iterable[VoiceProfile]:
        return list(AVAILABLE_VOICES)

    def synthesize_to_file(
        self,
        text: str,
        voice_name: str,
        output_path: Path,
        speed: float = 1.0,
    ) -> Path:
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")
        voice = self.voice_for(voice_name)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try edge-tts first (best quality for Korean)
        if self._use_edge_tts:
            try:
                # Generate speech using Microsoft Edge TTS
                import tempfile

                # edge-tts produces MP3, save to temp first
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                    tmp_path = tmp_file.name

                # Get the edge voice for this profile
                edge_voice = voice.edge_voice or "ko-KR-SunHiNeural"

                # Calculate rate percentage from speed multiplier
                # speed: 1.0 = 0%, 0.5 = -50%, 2.0 = +100%
                rate_percent = int((speed - 1.0) * 100)
                rate_percent = max(-50, min(100, rate_percent))  # Clamp to valid range
                rate_str = f"{rate_percent:+d}%"

                # Run async synthesis with rate adjustment
                async def _synthesize():
                    communicate = edge_tts.Communicate(text, edge_voice, rate=rate_str, volume="+0%")
                    await communicate.save(tmp_path)

                asyncio.run(_synthesize())

                # Convert MP3 to WAV using pydub (requires ffmpeg)
                try:
                    audio = AudioSegment.from_mp3(tmp_path)
                    audio.export(str(output_path), format='wav')
                except Exception as conv_err:
                    # Clean up temp file before raising
                    os.unlink(tmp_path)
                    raise Exception(
                        f"MP3 to WAV conversion failed. ffmpeg is required!\n"
                        f"Install ffmpeg:\n"
                        f"  macOS: brew install ffmpeg\n"
                        f"  Linux: sudo apt install ffmpeg\n"
                        f"  Windows: Download from ffmpeg.org\n"
                        f"Error: {conv_err}"
                    )

                # Clean up temporary MP3 file
                os.unlink(tmp_path)

                print(f"✓ Generated speech using edge-tts ({edge_voice})")
                return output_path
            except Exception as e:
                print(f"✗ edge-tts synthesis failed: {e}")
                print("→ Falling back to next available engine...")
                # Fall through to next engine

        # Try gTTS as fallback (good quality)
        if self._use_gtts:
            try:
                # Generate speech using Google TTS (produces MP3)
                import tempfile
                tts_obj = gTTS(text=text, lang='ko', slow=False)

                # Save to temporary MP3 file first
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    tts_obj.save(tmp_path)

                # Convert MP3 to WAV using pydub (requires ffmpeg)
                try:
                    audio = AudioSegment.from_mp3(tmp_path)
                    audio.export(str(output_path), format='wav')
                except Exception as conv_err:
                    # Clean up temp file before raising
                    os.unlink(tmp_path)
                    raise Exception(
                        f"MP3 to WAV conversion failed. ffmpeg is required!\n"
                        f"Install ffmpeg:\n"
                        f"  macOS: brew install ffmpeg\n"
                        f"  Linux: sudo apt install ffmpeg\n"
                        f"  Windows: Download from ffmpeg.org\n"
                        f"Error: {conv_err}"
                    )

                # Clean up temporary MP3 file
                os.unlink(tmp_path)

                print(f"✓ Generated speech using gTTS")
                return output_path
            except Exception as e:
                print(f"✗ gTTS synthesis failed: {e}")
                print("→ Falling back to next available engine...")
                # Fall through to next engine

        # Try Coqui TTS as fallback
        if self._use_coqui and self._tts_model is not None:
            try:
                # Generate speech using Coqui TTS
                self._tts_model.tts_to_file(
                    text=text,
                    file_path=str(output_path),
                    language="ko"  # Korean language
                )
                print(f"Generated speech using Coqui TTS")
                return output_path
            except Exception as e:
                print(f"Warning: Coqui TTS synthesis failed: {e}")
                print("Falling back to placeholder audio")
                # Fall through to placeholder generation

        # Fallback to placeholder audio
        print("⚠️  WARNING: Generating placeholder audio (sine wave) - NOT real speech!")
        print("⚠️  All TTS engines failed. Please install ffmpeg:")
        print("   macOS: brew install ffmpeg")
        print("   Linux: sudo apt install ffmpeg")
        print("   Windows: Download from ffmpeg.org")
        buffer = _text_to_wave(text, sample_rate=voice.sample_rate)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(voice.sample_rate)
            wav_file.writeframes(buffer)

        return output_path

    def voice_for(self, voice_name: str) -> VoiceProfile:
        return self._voice_lookup.get(voice_name, AVAILABLE_VOICES[0])


def _text_to_wave(text: str, sample_rate: int) -> bytes:
    duration = max(0.35, min(4.0, len(text) * 0.08))
    total_samples = int(sample_rate * duration)
    base_freq = 200 + (sum(map(ord, text)) % 200)
    samples = array("h")
    for n in range(total_samples):
        angle = 2 * math.pi * base_freq * (n / sample_rate)
        amplitude = 0.25 + 0.05 * math.sin(n / 500)
        value = int(32767 * amplitude * math.sin(angle))
        samples.append(value)
    return samples.tobytes()
