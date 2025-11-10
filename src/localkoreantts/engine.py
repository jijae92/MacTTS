"""TTS synthesis engine with multiple backend options."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
from array import array
from typing import Iterable, List, Optional
import wave
import os
import sys
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
AudioSegment = None
_gtts_available = False

try:
    from gtts import gTTS as GoogleTTS
    from pydub import AudioSegment as AudioSegmentClass
    import shutil

    gTTS = GoogleTTS
    AudioSegment = AudioSegmentClass
    _gtts_available = True

    # Configure pydub to find ffmpeg - CRITICAL for TTS to work!
    # Try multiple locations in order of likelihood
    ffmpeg_candidates = [
        shutil.which('ffmpeg'),  # System PATH
        '/opt/homebrew/bin/ffmpeg',  # Homebrew Apple Silicon (most common)
        '/usr/local/bin/ffmpeg',  # Homebrew Intel
        '/opt/local/bin/ffmpeg',  # MacPorts
        '/usr/bin/ffmpeg',  # Linux/macOS system
    ]

    # Also check if running from a bundled app
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)
        ffmpeg_candidates.insert(0, str(bundle_dir / 'ffmpeg'))

    ffmpeg_found = None
    for candidate in ffmpeg_candidates:
        if candidate and Path(candidate).exists():
            ffmpeg_found = candidate
            break

    if ffmpeg_found:
        # Set all possible pydub ffmpeg paths
        AudioSegment.converter = ffmpeg_found
        AudioSegment.ffmpeg = ffmpeg_found

        # Also try to set ffprobe
        ffprobe_path = ffmpeg_found.replace('ffmpeg', 'ffprobe')
        if Path(ffprobe_path).exists():
            AudioSegment.ffprobe = ffprobe_path
            # Set environment variable for ffprobe (needed by dialog-tts)
            os.environ['FFPROBE_BINARY'] = ffprobe_path
            print(f"✓ Configured pydub to use ffmpeg: {ffmpeg_found}")
            print(f"✓ Configured ffprobe: {ffprobe_path}")
        else:
            print(f"✓ Configured pydub to use ffmpeg: {ffmpeg_found}")
            print(f"⚠️  Warning: ffprobe not found at {ffprobe_path}")

        # Set environment variables as backup (for subprocess calls)
        os.environ['FFMPEG_BINARY'] = ffmpeg_found

        # Also add directory to PATH for subprocess commands
        ffmpeg_dir = str(Path(ffmpeg_found).parent)
        if ffmpeg_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
            print(f"✓ Added {ffmpeg_dir} to PATH")
    else:
        print("=" * 60)
        print("⚠️  WARNING: ffmpeg NOT FOUND!")
        print("=" * 60)
        print("Checked locations:")
        for candidate in ffmpeg_candidates:
            if candidate:
                print(f"  ✗ {candidate}")
        print()
        print("TTS will generate sine wave test tones instead of speech!")
        print()
        print("Install ffmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        print("=" * 60)

except ImportError as e:
    print(f"Note: gTTS not available: {e}")

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
# Using Microsoft Edge TTS Neural voices for the most natural Korean speech
AVAILABLE_VOICES: List[VoiceProfile] = [
    # Female voices - natural and expressive
    VoiceProfile(name="SunHi (여성, 밝고 친근함)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-SunHiNeural"),
    VoiceProfile(name="JiMin (여성, 차분하고 자연스러움)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-JiMinNeural"),
    VoiceProfile(name="SeoHyeon (여성, 전문적이고 명료함)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-SeoHyeonNeural"),
    VoiceProfile(name="SoonBok (여성, 따뜻하고 부드러움)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-SoonBokNeural"),
    VoiceProfile(name="YuJin (여성, 활기차고 생동감)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-YuJinNeural"),

    # Male voices - clear and professional
    VoiceProfile(name="InJoon (남성, 안정적이고 신뢰감)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-InJoonNeural"),
    VoiceProfile(name="Hyunsu (남성, 젊고 활력있음)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-HyunsuNeural"),
    VoiceProfile(name="GookMin (남성, 권위있고 전문적)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-GookMinNeural"),
    VoiceProfile(name="BongJin (남성, 명료하고 차분함)", locale="ko-KR", sample_rate=24000, edge_voice="ko-KR-BongJinNeural"),
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
