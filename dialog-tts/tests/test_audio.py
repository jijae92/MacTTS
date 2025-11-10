"""Tests for audio processing."""

import pytest
from pathlib import Path
import tempfile
import sys
import math

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_utils import AudioProcessor

# Check if pydub is available
try:
    from pydub import AudioSegment
    from pydub.generators import Sine
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


@pytest.mark.skipif(not PYDUB_AVAILABLE, reason="pydub not available")
class TestAudioProcessor:
    """Test audio processing utilities."""

    @pytest.fixture
    def processor(self):
        """Create audio processor."""
        return AudioProcessor(sample_rate=24000)

    @pytest.fixture
    def sample_audio(self):
        """Create sample audio segment (1 second, 440 Hz sine wave)."""
        return Sine(440).to_audio_segment(duration=1000, volume=-20.0)

    def test_create_silence(self, processor):
        """Test silence generation."""
        silence = processor.create_silence(500)

        assert len(silence) == 500
        assert silence.frame_rate == 24000
        assert silence.rms < 10  # Should be very quiet

    def test_apply_gain(self, processor, sample_audio):
        """Test gain adjustment."""
        original_dbfs = sample_audio.dBFS

        # Increase volume
        louder = processor.apply_gain(sample_audio, 6.0)
        assert louder.dBFS > original_dbfs

        # Decrease volume
        quieter = processor.apply_gain(sample_audio, -6.0)
        assert quieter.dBFS < original_dbfs

    def test_apply_pan(self, processor, sample_audio):
        """Test stereo panning."""
        # Pan left
        left_panned = processor.apply_pan(sample_audio, -0.8)
        assert left_panned.channels == 2

        # Get left and right channels
        left_channel = left_panned.split_to_mono()[0]
        right_channel = left_panned.split_to_mono()[1]

        # Left should be louder than right
        assert left_channel.rms > right_channel.rms

        # Pan right
        right_panned = processor.apply_pan(sample_audio, 0.8)
        left_channel = right_panned.split_to_mono()[0]
        right_channel = right_panned.split_to_mono()[1]

        # Right should be louder than left
        assert right_channel.rms > left_channel.rms

    def test_ensure_stereo(self, processor, sample_audio):
        """Test mono to stereo conversion."""
        # Convert to mono first
        mono = sample_audio.set_channels(1)
        assert mono.channels == 1

        # Convert to stereo
        stereo = processor.ensure_stereo(mono)
        assert stereo.channels == 2

    def test_ensure_mono(self, processor, sample_audio):
        """Test stereo to mono conversion."""
        # Convert to stereo first
        stereo = sample_audio.set_channels(2)
        assert stereo.channels == 2

        # Convert to mono
        mono = processor.ensure_mono(stereo)
        assert mono.channels == 1

    def test_crossfade(self, processor):
        """Test crossfading between segments."""
        audio1 = Sine(440).to_audio_segment(duration=1000)
        audio2 = Sine(880).to_audio_segment(duration=1000)

        # Crossfade
        result = processor.crossfade(audio1, audio2, 100)

        # Result should be longer than either segment alone
        assert len(result) > len(audio1)
        assert len(result) < len(audio1) + len(audio2)

    def test_concatenate(self, processor, sample_audio):
        """Test concatenating multiple segments."""
        segments = [sample_audio for _ in range(3)]

        # Without gap
        result = processor.concatenate(segments, gap_ms=0)
        assert len(result) == len(sample_audio) * 3

        # With gap
        result = processor.concatenate(segments, gap_ms=500)
        expected_duration = len(sample_audio) * 3 + 500 * 2  # 2 gaps
        assert abs(len(result) - expected_duration) < 50  # Allow small tolerance

    def test_normalize(self, processor, sample_audio):
        """Test audio normalization."""
        # Normalize to -3.0 dBFS
        normalized = processor.normalize(sample_audio, -3.0)

        # Check peak is close to target
        assert abs(normalized.max_dBFS - (-3.0)) < 0.5

    def test_export_wav(self, processor, sample_audio):
        """Test exporting to WAV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.wav"
            processor.export(sample_audio, output_path, format="wav")

            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_load_audio(self, processor, sample_audio):
        """Test loading audio file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save audio
            temp_path = Path(tmpdir) / "test.wav"
            sample_audio.export(str(temp_path), format="wav")

            # Load audio
            loaded = processor.load_audio(temp_path)

            assert loaded.frame_rate == processor.sample_rate
            assert abs(len(loaded) - len(sample_audio)) < 50  # Allow small tolerance

    def test_trim_silence(self, processor, sample_audio):
        """Test silence trimming."""
        # Add silence to beginning and end
        silence = processor.create_silence(500)
        audio_with_silence = silence + sample_audio + silence

        # Trim
        trimmed = processor.trim_silence(audio_with_silence)

        # Should be shorter than original
        assert len(trimmed) < len(audio_with_silence)
        # Should be close to original sample length
        assert abs(len(trimmed) - len(sample_audio)) < 200


@pytest.mark.skipif(not PYDUB_AVAILABLE, reason="pydub not available")
class TestDialogAudioGeneration:
    """Integration tests for dialog audio generation."""

    def test_generate_simple_dialog(self):
        """Test generating a simple 2-line dialog."""
        # This test requires actual TTS, so we'll just verify the flow works
        # In a real test, you'd use mock TTS or test fixtures

        processor = AudioProcessor(sample_rate=24000)

        # Create mock audio segments (sine waves instead of TTS)
        line1 = Sine(440).to_audio_segment(duration=2000, volume=-20.0)
        line2 = Sine(880).to_audio_segment(duration=2000, volume=-20.0)

        # Apply pan (simulate different speakers)
        line1 = processor.apply_pan(line1, -0.3)
        line2 = processor.apply_pan(line2, +0.3)

        # Concatenate with gap
        result = processor.concatenate([line1, line2], gap_ms=250)

        # Normalize
        result = processor.normalize(result, -1.0)

        # Check result
        assert len(result) >= 4000  # At least 4 seconds
        assert result.channels == 2  # Stereo
        assert abs(result.max_dBFS - (-1.0)) < 0.5  # Normalized

        # Verify panning worked (check left/right RMS difference)
        left, right = result.split_to_mono()
        # This is a rough check - in real dialog, one channel should be louder at certain times
        assert left.rms > 0
        assert right.rms > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
