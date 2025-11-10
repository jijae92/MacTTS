"""macOS 'say' command-line TTS backend (fallback)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List


class MacSayBackend:
    """TTS backend using macOS 'say' command-line tool."""

    def __init__(self):
        """Initialize the say CLI backend."""
        # Verify 'say' command is available
        try:
            # Just check if 'say' exists (no --version flag on macOS say)
            result = subprocess.run(
                ['which', 'say'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("'say' command not found")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise RuntimeError(
                "'say' command not available. This backend requires macOS."
            )

    def get_available_voices(self) -> List[dict]:
        """
        Get list of available system voices.

        Returns:
            List of dicts with voice information
        """
        result = subprocess.run(
            ['say', '-v', '?'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise RuntimeError("Failed to get voice list")

        voices = []
        for line in result.stdout.strip().split('\n'):
            # Parse line format: "VoiceName    language    # description"
            parts = line.split('#', 1)
            if len(parts) < 1:
                continue

            voice_info = parts[0].strip().split(None, 1)
            if len(voice_info) < 2:
                continue

            name = voice_info[0]
            language = voice_info[1].strip()
            description = parts[1].strip() if len(parts) > 1 else ""

            voices.append({
                'name': name,
                'language': language,
                'description': description
            })

        return voices

    def find_voice(
        self,
        voice_hint: Optional[str] = None,
        voice_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Find a suitable voice.

        Args:
            voice_hint: Hint string to search for (e.g., "ko_KR", "en_US")
            voice_name: Specific voice name (e.g., "Yuna", "Samantha")

        Returns:
            Voice name string or None for system default
        """
        voices = self.get_available_voices()

        # If specific name provided, try to find exact match
        if voice_name:
            for voice in voices:
                if voice['name'].lower() == voice_name.lower():
                    return voice['name']
                if voice_name.lower() in voice['name'].lower():
                    return voice['name']

        # If hint provided, try to find matching voice
        if voice_hint:
            for voice in voices:
                if voice_hint.lower() in voice['language'].lower():
                    return voice['name']

        # Return None to use system default
        return None

    def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        rate_wpm: int = 180
    ) -> Path:
        """
        Synthesize text to audio file using 'say' command.

        Args:
            text: Text to synthesize
            output_path: Output file path
            voice: Voice name (from get_available_voices)
            rate_wpm: Speaking rate in words per minute (default: 180)

        Returns:
            Path to generated audio file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 'say' can only output AIFF format directly
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

        # Build command
        cmd = ['say']

        if voice:
            cmd.extend(['-v', voice])

        cmd.extend(['-r', str(rate_wpm)])
        cmd.extend(['-o', str(aiff_path)])
        cmd.append('--')
        cmd.append(text)

        # Run synthesis
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                raise RuntimeError(f"'say' command failed: {error_msg}")

            if not aiff_path.exists():
                raise RuntimeError("Output file was not created")

            # Convert AIFF to target format if needed
            if temp_aiff:
                try:
                    from pydub import AudioSegment

                    audio = AudioSegment.from_file(str(aiff_path), format='aiff')
                    audio.export(str(output_path), format=output_path.suffix[1:])

                    # Clean up temp file
                    Path(temp_aiff).unlink(missing_ok=True)
                except ImportError:
                    # If pydub not available, use ffmpeg directly
                    import shutil
                    ffmpeg_cmd = [
                        'ffmpeg', '-y', '-i', str(aiff_path),
                        str(output_path)
                    ]
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                    Path(temp_aiff).unlink(missing_ok=True)

            return output_path

        except subprocess.TimeoutExpired:
            if temp_aiff:
                Path(temp_aiff).unlink(missing_ok=True)
            raise RuntimeError("Synthesis timeout after 30s")

    def print_available_voices(self):
        """Print available voices with details."""
        print("Available macOS 'say' Voices:")
        print("-" * 70)

        voices = self.get_available_voices()
        for voice in voices:
            print(f"{voice['name']:20s} ({voice['language']:15s})")
            if voice['description']:
                print(f"  {voice['description']}")
            print()


def test_mac_say():
    """Test the MacSay backend."""
    try:
        backend = MacSayBackend()

        print("Testing MacSay Backend")
        print("=" * 70)

        # Print available voices
        backend.print_available_voices()

        # Find Korean voices
        print("\nFinding Korean voices...")
        ko_voice = backend.find_voice(voice_hint="ko_KR")
        if ko_voice:
            print(f"Found Korean voice: {ko_voice}")
        else:
            print("No Korean voice found, will use system default")

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
    test_mac_say()
