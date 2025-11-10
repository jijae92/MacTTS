"""Coqui XTTS v2 backend for high-quality multi-speaker synthesis."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import tempfile

try:
    from TTS.api import TTS
    XTTS_AVAILABLE = True
except ImportError:
    XTTS_AVAILABLE = False


class XTTSBackend:
    """TTS backend using Coqui XTTS v2 for voice cloning."""

    def __init__(self, model_dir: Optional[Path] = None):
        """
        Initialize XTTS backend.

        Args:
            model_dir: Directory containing XTTS model files (optional)
        """
        if not XTTS_AVAILABLE:
            raise RuntimeError(
                "Coqui TTS is not available. Install with: pip install TTS"
            )

        print("Loading XTTS v2 model...")
        self.model_dir = Path(model_dir) if model_dir else None

        # Initialize TTS model
        # XTTS v2 is a multi-speaker model that supports voice cloning
        try:
            if self.model_dir and self.model_dir.exists():
                self.tts = TTS(model_path=str(self.model_dir))
            else:
                # Download pre-trained model
                self.tts = TTS(
                    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                    progress_bar=True
                )
            print("✓ XTTS v2 model loaded successfully")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize XTTS model: {e}")

    def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Path,
        language: str = "ko",
        speed: float = 1.0
    ) -> Path:
        """
        Synthesize text to audio file using voice cloning.

        Args:
            text: Text to synthesize
            output_path: Output file path
            speaker_wav: Reference audio file for voice cloning (6-24 seconds recommended)
            language: Language code ("ko" for Korean, "en" for English, etc.)
            speed: Speaking speed multiplier (1.0 = normal)

        Returns:
            Path to generated audio file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        speaker_wav = Path(speaker_wav)
        if not speaker_wav.exists():
            raise FileNotFoundError(f"Speaker reference file not found: {speaker_wav}")

        try:
            # Synthesize using XTTS v2
            self.tts.tts_to_file(
                text=text,
                file_path=str(output_path),
                speaker_wav=str(speaker_wav),
                language=language,
                speed=speed
            )

            if not output_path.exists():
                raise RuntimeError("Output file was not created")

            return output_path

        except Exception as e:
            raise RuntimeError(f"XTTS synthesis failed: {e}")

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages."""
        try:
            # XTTS v2 supports multiple languages
            return ["ko", "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja"]
        except:
            return ["ko", "en"]

    def validate_reference_audio(self, audio_path: Path) -> dict:
        """
        Validate and analyze reference audio for voice cloning.

        Args:
            audio_path: Path to reference audio file

        Returns:
            Dict with validation results and recommendations
        """
        if not audio_path.exists():
            return {
                'valid': False,
                'error': f"File not found: {audio_path}"
            }

        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(str(audio_path))
            duration_sec = len(audio) / 1000.0
            sample_rate = audio.frame_rate
            channels = audio.channels

            # Check duration (6-24 seconds recommended)
            duration_ok = 6.0 <= duration_sec <= 24.0
            duration_warning = None
            if duration_sec < 6.0:
                duration_warning = "Too short. 6-24 seconds recommended for best results."
            elif duration_sec > 24.0:
                duration_warning = "Longer than recommended. First 24 seconds will be used."

            # Check sample rate (22050 Hz is standard for XTTS)
            sr_ok = sample_rate >= 16000
            sr_warning = None
            if sample_rate < 16000:
                sr_warning = f"Sample rate {sample_rate} Hz is too low. 22050 Hz recommended."

            # Check channels (mono is preferred)
            channels_ok = channels == 1
            channels_warning = None
            if channels > 1:
                channels_warning = "Stereo audio will be converted to mono."

            return {
                'valid': duration_ok and sr_ok,
                'duration_sec': duration_sec,
                'sample_rate': sample_rate,
                'channels': channels,
                'duration_ok': duration_ok,
                'duration_warning': duration_warning,
                'sr_ok': sr_ok,
                'sr_warning': sr_warning,
                'channels_ok': channels_ok,
                'channels_warning': channels_warning
            }

        except Exception as e:
            return {
                'valid': False,
                'error': f"Failed to analyze audio: {e}"
            }


def test_xtts():
    """Test the XTTS backend."""
    try:
        backend = XTTSBackend()

        print("Testing XTTS Backend")
        print("=" * 70)

        # Print supported languages
        print("\nSupported languages:")
        print(", ".join(backend.get_supported_languages()))

        print("\nNote: XTTS requires a reference audio file for voice cloning.")
        print("To test synthesis, provide a 6-24 second reference audio file.")

        # Example validation
        print("\nTo validate a reference audio file:")
        print(">>> result = backend.validate_reference_audio(Path('reference.wav'))")
        print(">>> print(result)")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_xtts()
