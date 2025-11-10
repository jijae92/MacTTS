"""macOS NSSpeechSynthesizer backend using PyObjC."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, List
import time

try:
    import objc
    from Foundation import NSURL
    from AppKit import NSSpeechSynthesizer
    PYOBJC_AVAILABLE = True
except ImportError:
    PYOBJC_AVAILABLE = False


class MacNSSpeechBackend:
    """TTS backend using macOS NSSpeechSynthesizer via PyObjC."""

    def __init__(self):
        """Initialize the NSSpeech backend."""
        if not PYOBJC_AVAILABLE:
            raise RuntimeError(
                "PyObjC is not available. Install with: pip install pyobjc-framework-Cocoa"
            )

        self.synthesizer = NSSpeechSynthesizer.alloc().init()
        self._is_speaking = False

    def get_available_voices(self) -> List[str]:
        """Get list of available system voices."""
        voices = NSSpeechSynthesizer.availableVoices()
        return [str(voice) for voice in voices]

    def find_voice(
        self,
        voice_hint: Optional[str] = None,
        voice_name: Optional[str] = None
    ) -> str:
        """
        Find a suitable voice.

        Args:
            voice_hint: Hint string to search for (e.g., "ko_KR", "en_US")
            voice_name: Specific voice name (e.g., "Yuna", "Samantha")

        Returns:
            Voice identifier string
        """
        available_voices = self.get_available_voices()

        # If specific name provided, try to find exact match
        if voice_name:
            for voice in available_voices:
                if voice_name.lower() in voice.lower():
                    return voice

        # If hint provided, try to find matching voice
        if voice_hint:
            for voice in available_voices:
                if voice_hint.lower() in voice.lower():
                    return voice

        # Return default voice
        default_voice = self.synthesizer.defaultVoice()
        return str(default_voice) if default_voice else available_voices[0]

    def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        rate_wpm: int = 180
    ) -> Path:
        """
        Synthesize text to audio file.

        Args:
            text: Text to synthesize
            output_path: Output file path (must be .aiff or .wav)
            voice: Voice identifier (from get_available_voices)
            rate_wpm: Speaking rate in words per minute (default: 180)

        Returns:
            Path to generated audio file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # NSSpeechSynthesizer only saves to AIFF format
        # We'll save to AIFF first, then convert if needed
        temp_aiff = None
        final_path = output_path

        if output_path.suffix.lower() != '.aiff':
            # Create temporary AIFF file
            temp_fd, temp_aiff = tempfile.mkstemp(suffix='.aiff')
            import os
            os.close(temp_fd)
            aiff_path = Path(temp_aiff)
        else:
            aiff_path = output_path

        # Set voice if provided
        if voice:
            self.synthesizer.setVoice_(voice)

        # Set speaking rate (words per minute)
        # NSSpeechSynthesizer uses words per minute
        self.synthesizer.setRate_(rate_wpm)

        # Start synthesis to file
        url = NSURL.fileURLWithPath_(str(aiff_path))
        success = self.synthesizer.startSpeakingString_toURL_(text, url)

        if not success:
            if temp_aiff:
                Path(temp_aiff).unlink(missing_ok=True)
            raise RuntimeError(f"Failed to synthesize speech for text: {text[:50]}")

        # Wait for synthesis to complete
        # NSSpeechSynthesizer is asynchronous
        timeout = 30  # seconds
        start_time = time.time()

        while self.synthesizer.isSpeaking():
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                self.synthesizer.stopSpeaking()
                if temp_aiff:
                    Path(temp_aiff).unlink(missing_ok=True)
                raise RuntimeError(f"Synthesis timeout after {timeout}s")

        # Give a small delay for file to be fully written
        time.sleep(0.2)

        # Convert AIFF to target format if needed
        if temp_aiff:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(str(aiff_path), format='aiff')
            audio.export(str(output_path), format=output_path.suffix[1:])

            # Clean up temp file
            Path(temp_aiff).unlink(missing_ok=True)

        return output_path

    def list_voices_with_info(self) -> List[dict]:
        """
        Get detailed information about available voices.

        Returns:
            List of dicts with voice information
        """
        voices = []
        for voice_id in self.get_available_voices():
            # Get voice attributes
            attrs = NSSpeechSynthesizer.attributesForVoice_(voice_id)

            # Extract useful information
            info = {
                'id': voice_id,
                'name': str(attrs.get('VoiceName', 'Unknown')),
                'language': str(attrs.get('VoiceLanguage', 'Unknown')),
                'gender': str(attrs.get('VoiceGender', 'Unknown')),
                'age': str(attrs.get('VoiceAge', 'Unknown')),
            }
            voices.append(info)

        return voices

    def print_available_voices(self):
        """Print available voices with details."""
        print("Available macOS System Voices:")
        print("-" * 70)

        voices = self.list_voices_with_info()
        for voice in voices:
            print(f"{voice['name']:20s} ({voice['language']:10s}) - {voice['gender']}, Age: {voice['age']}")
            print(f"  ID: {voice['id']}")
            print()


def test_mac_nsspeech():
    """Test the MacNSSpeech backend."""
    try:
        backend = MacNSSpeechBackend()

        print("Testing MacNSSpeech Backend")
        print("=" * 70)

        # Print available voices
        backend.print_available_voices()

        # Find Korean voices
        print("\nFinding Korean voices...")
        ko_voice = backend.find_voice(voice_hint="ko_KR")
        print(f"Found Korean voice: {ko_voice}")

        # Test synthesis
        print("\nTesting synthesis...")
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.wav"
            backend.synthesize_to_file(
                text="안녕하세요. 테스트 음성입니다.",
                output_path=output,
                voice=ko_voice,
                rate_wpm=180
            )

            if output.exists():
                print(f"✓ Successfully created audio file: {output}")
                print(f"  File size: {output.stat().st_size} bytes")
            else:
                print("✗ Failed to create audio file")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_mac_nsspeech()
