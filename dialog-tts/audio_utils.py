"""Audio processing utilities for dialog TTS."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional, List

try:
    from pydub import AudioSegment
    from pydub.effects import normalize as pydub_normalize
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("Warning: pydub not available. Install with: pip install pydub")


class AudioProcessor:
    """Handles audio processing operations like pan, gain, crossfade, and concatenation."""

    def __init__(self, sample_rate: int = 24000):
        """
        Initialize audio processor.

        Args:
            sample_rate: Target sample rate in Hz
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError("pydub is required for audio processing. Install with: pip install pydub")

        self.sample_rate = sample_rate

    def load_audio(self, file_path: Path) -> AudioSegment:
        """Load an audio file and resample to target sample rate."""
        audio = AudioSegment.from_file(str(file_path))

        # Resample if needed
        if audio.frame_rate != self.sample_rate:
            audio = audio.set_frame_rate(self.sample_rate)

        return audio

    def apply_gain(self, audio: AudioSegment, gain_db: float) -> AudioSegment:
        """
        Apply gain adjustment in dB.

        Args:
            audio: Input audio
            gain_db: Gain in decibels (positive = louder, negative = quieter)

        Returns:
            Audio with gain applied
        """
        if abs(gain_db) < 0.01:  # Skip if negligible
            return audio

        return audio + gain_db

    def apply_pan(self, audio: AudioSegment, pan: float) -> AudioSegment:
        """
        Apply stereo panning.

        Args:
            audio: Input audio (will be converted to stereo if mono)
            pan: Pan position from -1.0 (left) to +1.0 (right), 0.0 = center

        Returns:
            Stereo audio with panning applied
        """
        # Clamp pan to valid range
        pan = max(-1.0, min(1.0, pan))

        # Convert to stereo if mono
        if audio.channels == 1:
            audio = audio.set_channels(2)

        # Skip if centered
        if abs(pan) < 0.01:
            return audio

        # Split into left and right channels
        samples = audio.split_to_mono()
        left = samples[0]
        right = samples[1] if len(samples) > 1 else samples[0]

        # Apply panning
        # pan = -1.0: full left (left 0dB, right -inf dB)
        # pan = 0.0: center (left 0dB, right 0dB)
        # pan = +1.0: full right (left -inf dB, right 0dB)

        # Calculate gain adjustments using constant power panning
        # angle = pan * π/4
        angle = pan * math.pi / 4
        left_gain_db = 20 * math.log10(max(0.001, math.cos(angle)))
        right_gain_db = 20 * math.log10(max(0.001, math.sin(angle + math.pi/4)))

        # For negative pan (left), adjust differently
        if pan < 0:
            left_gain_db = 0
            right_gain_db = 20 * math.log10(max(0.001, 1.0 + pan))
        else:
            left_gain_db = 20 * math.log10(max(0.001, 1.0 - pan))
            right_gain_db = 0

        left = left + left_gain_db
        right = right + right_gain_db

        # Merge channels
        return AudioSegment.from_mono_audiosegments(left, right)

    def ensure_stereo(self, audio: AudioSegment) -> AudioSegment:
        """Convert audio to stereo if it's mono."""
        if audio.channels == 1:
            return audio.set_channels(2)
        return audio

    def ensure_mono(self, audio: AudioSegment) -> AudioSegment:
        """Convert audio to mono if it's stereo."""
        if audio.channels > 1:
            return audio.set_channels(1)
        return audio

    def create_silence(self, duration_ms: int) -> AudioSegment:
        """Create silent audio segment."""
        return AudioSegment.silent(
            duration=duration_ms,
            frame_rate=self.sample_rate
        )

    def crossfade(
        self,
        audio1: AudioSegment,
        audio2: AudioSegment,
        duration_ms: int
    ) -> AudioSegment:
        """
        Crossfade between two audio segments.

        Args:
            audio1: First audio segment
            audio2: Second audio segment
            duration_ms: Crossfade duration in milliseconds

        Returns:
            Concatenated audio with crossfade
        """
        if duration_ms <= 0:
            return audio1 + audio2

        # Ensure both have same sample rate and channels
        audio2 = audio2.set_frame_rate(audio1.frame_rate)
        if audio1.channels != audio2.channels:
            if audio1.channels == 2:
                audio2 = audio2.set_channels(2)
            else:
                audio1 = audio1.set_channels(audio2.channels)

        # Limit crossfade to length of shorter segment
        max_crossfade = min(len(audio1), len(audio2))
        actual_duration = min(duration_ms, max_crossfade)

        if actual_duration <= 0:
            return audio1 + audio2

        return audio1.append(audio2, crossfade=actual_duration)

    def concatenate(
        self,
        segments: List[AudioSegment],
        gap_ms: int = 0,
        crossfade_ms: int = 0
    ) -> AudioSegment:
        """
        Concatenate multiple audio segments.

        Args:
            segments: List of audio segments to concatenate
            gap_ms: Gap between segments in milliseconds
            crossfade_ms: Crossfade duration in milliseconds (overrides gap_ms)

        Returns:
            Concatenated audio
        """
        if not segments:
            return self.create_silence(0)

        result = segments[0]

        for segment in segments[1:]:
            if crossfade_ms > 0:
                result = self.crossfade(result, segment, crossfade_ms)
            elif gap_ms > 0:
                result = result + self.create_silence(gap_ms) + segment
            else:
                result = result + segment

        return result

    def normalize(
        self,
        audio: AudioSegment,
        target_dbfs: float = -1.0
    ) -> AudioSegment:
        """
        Normalize audio to target dBFS (peak normalization).

        Args:
            audio: Input audio
            target_dbfs: Target peak level in dBFS (e.g., -1.0 for near-maximum)

        Returns:
            Normalized audio
        """
        # Calculate current peak
        current_peak_dbfs = audio.max_dBFS

        # Calculate gain needed
        gain_needed = target_dbfs - current_peak_dbfs

        return audio + gain_needed

    def export(
        self,
        audio: AudioSegment,
        output_path: Path,
        format: str = "wav",
        bitrate: str = "192k"
    ) -> Path:
        """
        Export audio to file.

        Args:
            audio: Audio to export
            output_path: Output file path
            format: Output format ("wav", "mp3", etc.)
            bitrate: Bitrate for compressed formats

        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "wav":
            audio.export(
                str(output_path),
                format="wav",
                parameters=["-ar", str(self.sample_rate)]
            )
        elif format == "mp3":
            audio.export(
                str(output_path),
                format="mp3",
                bitrate=bitrate,
                parameters=["-ar", str(self.sample_rate)]
            )
        else:
            audio.export(str(output_path), format=format)

        return output_path

    def get_duration_ms(self, audio: AudioSegment) -> int:
        """Get audio duration in milliseconds."""
        return len(audio)

    def get_rms(self, audio: AudioSegment) -> float:
        """Get RMS (root mean square) amplitude."""
        return audio.rms

    def trim_silence(
        self,
        audio: AudioSegment,
        silence_thresh: float = -50.0,
        chunk_size: int = 10
    ) -> AudioSegment:
        """
        Trim silence from beginning and end of audio.

        Args:
            audio: Input audio
            silence_thresh: Silence threshold in dBFS
            chunk_size: Chunk size in milliseconds for detection

        Returns:
            Trimmed audio
        """
        from pydub.silence import detect_nonsilent

        # Detect non-silent chunks
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=chunk_size,
            silence_thresh=silence_thresh
        )

        if not nonsilent_ranges:
            return audio

        # Get start and end of non-silent audio
        start_trim = nonsilent_ranges[0][0]
        end_trim = nonsilent_ranges[-1][1]

        return audio[start_trim:end_trim]


def convert_audio_format(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 24000,
    channels: int = 1
) -> Path:
    """
    Convert audio file to different format/sample rate.

    Args:
        input_path: Input audio file
        output_path: Output audio file
        sample_rate: Target sample rate
        channels: Target number of channels (1=mono, 2=stereo)

    Returns:
        Path to converted file
    """
    if not PYDUB_AVAILABLE:
        raise RuntimeError("pydub is required. Install with: pip install pydub")

    audio = AudioSegment.from_file(str(input_path))
    audio = audio.set_frame_rate(sample_rate)
    audio = audio.set_channels(channels)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(output_path), format=output_path.suffix[1:])

    return output_path
