"""
Audio processing pipeline using pydub.

Handles concatenation, panning, gain, silence, crossfade, and normalization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

from pydub import AudioSegment
from pydub.effects import normalize


@dataclass
class SpeakerSettings:
    """Settings for a single speaker."""
    voice_name: str
    rate_wpm: int = 180  # Words per minute (150-250 typical)
    gain_db: float = 0.0  # Volume adjustment
    pan: float = 0.0  # Stereo pan: -1.0 (left) to +1.0 (right)


class AudioPipeline:
    """
    Audio processing pipeline for podcast synthesis.

    Combines individual speech segments with silence, SFX, and effects.
    """

    def __init__(
        self,
        sample_rate: int = 24000,
        channels: int = 2,  # 1=mono, 2=stereo
        gap_ms: int = 250,
        xfade_ms: int = 20,
        normalize_peak_dbfs: float = -1.0
    ):
        """
        Initialize pipeline.

        Args:
            sample_rate: Output sample rate (Hz)
            channels: 1 for mono, 2 for stereo
            gap_ms: Default gap between utterances
            xfade_ms: Crossfade duration at sentence boundaries
            normalize_peak_dbfs: Peak normalization target (negative dB)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.gap_ms = gap_ms
        self.xfade_ms = xfade_ms
        self.normalize_peak_dbfs = normalize_peak_dbfs

    def combine_segments(
        self,
        segments: List[AudioSegment],
        speaker_settings: Optional[Dict[str, SpeakerSettings]] = None
    ) -> AudioSegment:
        """
        Combine multiple audio segments into final podcast.

        Args:
            segments: List of AudioSegment objects with metadata
            speaker_settings: Optional speaker-specific settings

        Returns:
            Combined AudioSegment
        """
        if not segments:
            # Return silence
            return AudioSegment.silent(
                duration=1000,
                frame_rate=self.sample_rate
            )

        # Start with first segment
        combined = segments[0]

        # Add remaining segments with gaps
        for seg in segments[1:]:
            # Add gap
            if self.gap_ms > 0:
                silence = AudioSegment.silent(
                    duration=self.gap_ms,
                    frame_rate=self.sample_rate
                )
                combined += silence

            # Add next segment
            combined += seg

        # Convert to target format
        combined = combined.set_frame_rate(self.sample_rate)
        combined = combined.set_channels(self.channels)

        # Normalize
        if self.normalize_peak_dbfs is not None:
            combined = self.normalize_to_peak(combined, self.normalize_peak_dbfs)

        return combined

    def apply_speaker_effects(
        self,
        audio: AudioSegment,
        settings: SpeakerSettings
    ) -> AudioSegment:
        """
        Apply speaker-specific effects (gain, pan).

        Args:
            audio: Input audio
            settings: Speaker settings

        Returns:
            Processed audio
        """
        # Apply gain
        if settings.gain_db != 0.0:
            audio = audio + settings.gain_db

        # Apply stereo pan (only for stereo output)
        if self.channels == 2 and settings.pan != 0.0:
            audio = self.apply_pan(audio, settings.pan)

        return audio

    def apply_pan(self, audio: AudioSegment, pan: float) -> AudioSegment:
        """
        Apply stereo panning.

        Args:
            audio: Input audio (will be converted to stereo if mono)
            pan: Pan position: -1.0 (left) to +1.0 (right)

        Returns:
            Stereo audio with panning applied
        """
        # Ensure stereo
        if audio.channels == 1:
            audio = audio.set_channels(2)

        # Split into left/right channels
        samples = audio.split_to_mono()

        if len(samples) != 2:
            return audio  # Can't pan non-stereo

        left, right = samples

        # Calculate gain adjustments
        # pan = -1.0 → full left (right muted)
        # pan = 0.0 → center (equal)
        # pan = +1.0 → full right (left muted)

        if pan < 0:
            # Reduce right channel
            right_gain_db = pan * 40  # -40dB at pan=-1.0
            right = right + right_gain_db
        elif pan > 0:
            # Reduce left channel
            left_gain_db = -pan * 40
            left = left + left_gain_db

        # Recombine
        return AudioSegment.from_mono_audiosegments(left, right)

    def create_silence(self, duration_ms: int) -> AudioSegment:
        """Create silence segment."""
        return AudioSegment.silent(
            duration=duration_ms,
            frame_rate=self.sample_rate
        ).set_channels(self.channels)

    def load_sfx(
        self,
        path: Path,
        volume_db: float = 0.0,
        pan: float = 0.0
    ) -> AudioSegment:
        """
        Load sound effect file.

        Args:
            path: Path to audio file
            volume_db: Volume adjustment
            pan: Stereo pan

        Returns:
            Loaded and processed audio
        """
        # Load file
        audio = AudioSegment.from_file(str(path))

        # Convert to target format
        audio = audio.set_frame_rate(self.sample_rate)
        audio = audio.set_channels(self.channels)

        # Apply volume
        if volume_db != 0.0:
            audio = audio + volume_db

        # Apply pan
        if self.channels == 2 and pan != 0.0:
            audio = self.apply_pan(audio, pan)

        return audio

    def normalize_to_peak(
        self,
        audio: AudioSegment,
        target_dbfs: float
    ) -> AudioSegment:
        """
        Normalize audio to target peak level.

        Args:
            audio: Input audio
            target_dbfs: Target peak in dBFS (e.g., -1.0)

        Returns:
            Normalized audio
        """
        # pydub normalize() normalizes to -0.1 dBFS by default
        # We need to adjust to our target
        normalized = normalize(audio, headroom=0.1)

        # Calculate additional gain needed
        current_peak_dbfs = normalized.max_dBFS
        gain_needed = target_dbfs - current_peak_dbfs

        if abs(gain_needed) > 0.1:  # Only adjust if significant
            normalized = normalized + gain_needed

        return normalized

    def apply_crossfade_at_sentences(
        self,
        audio: AudioSegment,
        xfade_ms: Optional[int] = None
    ) -> AudioSegment:
        """
        Apply crossfade at sentence boundaries.

        Detects sentence boundaries and applies short crossfades.

        Args:
            audio: Input audio
            xfade_ms: Crossfade duration (uses self.xfade_ms if None)

        Returns:
            Audio with crossfades applied
        """
        if xfade_ms is None:
            xfade_ms = self.xfade_ms

        if xfade_ms <= 0:
            return audio

        # This is a simplified implementation
        # In practice, you'd need silence detection or transcript timing
        # For now, return as-is
        return audio

    def export(
        self,
        audio: AudioSegment,
        output_path: Path,
        format: str = 'wav',
        bitrate: str = '192k'
    ) -> Path:
        """
        Export audio to file.

        Args:
            audio: Audio to export
            output_path: Output file path
            format: 'wav' or 'mp3'
            bitrate: Bitrate for MP3 (e.g., '192k')

        Returns:
            Path to exported file
        """
        if format == 'mp3':
            audio.export(
                str(output_path),
                format='mp3',
                bitrate=bitrate,
                parameters=["-q:a", "2"]  # High quality
            )
        else:
            # WAV
            audio.export(
                str(output_path),
                format='wav'
            )

        return output_path


def detect_ffmpeg() -> Optional[Path]:
    """
    Detect ffmpeg installation.

    Returns:
        Path to ffmpeg binary, or None if not found
    """
    import shutil

    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return Path(ffmpeg_path)

    # Common locations
    common_paths = [
        Path('/usr/local/bin/ffmpeg'),
        Path('/opt/homebrew/bin/ffmpeg'),
        Path('C:/ffmpeg/bin/ffmpeg.exe'),
        Path('C:/Program Files/ffmpeg/bin/ffmpeg.exe'),
    ]

    for path in common_paths:
        if path.exists():
            return path

    return None


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available."""
    return detect_ffmpeg() is not None
