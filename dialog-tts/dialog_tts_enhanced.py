#!/usr/bin/env python3
"""
Enhanced Dialog TTS with performance improvements:
- Parallel synthesis for faster processing
- LUFS normalization for professional audio quality
- Caching to avoid re-generating same text
- Retry logic for network failures
- Progress callbacks for real-time updates
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional, List, Callable
import tempfile

from dialog_tts import DialogTTSEngine, SpeakerConfig
from parser_utils import DialogParser, DialogLine, Directive
from audio_utils import AudioProcessor

try:
    from pydub import AudioSegment
    import pyloudnorm as pyln
    LOUDNORM_AVAILABLE = True
except ImportError:
    LOUDNORM_AVAILABLE = False
    print("Note: pyloudnorm not available. Install with: pip install pyloudnorm")


class CachedDialogTTSEngine(DialogTTSEngine):
    """Enhanced Dialog TTS Engine with caching and parallel processing."""

    def __init__(
        self,
        engine: str = "edge",
        sample_rate: int = 24000,
        stereo: bool = False,
        model_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        max_workers: int = 3,
    ):
        """
        Initialize enhanced dialog TTS engine.

        Args:
            engine: TTS engine to use ("edge", "mac", "xtts")
            sample_rate: Audio sample rate in Hz
            stereo: Whether to output stereo audio
            model_dir: XTTS model directory (optional)
            cache_dir: Directory for caching synthesized audio
            max_workers: Maximum parallel synthesis workers
        """
        super().__init__(engine, sample_rate, stereo, model_dir)

        # Setup cache
        self.cache_dir = cache_dir or Path.home() / ".cache" / "dialog-tts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_enabled = True

        # Parallel processing
        self.max_workers = max_workers

        # Statistics
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'retries': 0,
            'failures': 0,
        }

    def _get_cache_key(self, text: str, config: SpeakerConfig) -> str:
        """Generate cache key for text + speaker config."""
        # Include relevant config in cache key
        cache_data = {
            'text': text,
            'engine': self.engine,
            'voice_name': config.voice_name if hasattr(config, 'voice_name') else '',
            'rate_wpm': config.rate_wpm if hasattr(config, 'rate_wpm') else 180,
            'sample_rate': self.sample_rate,
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for cache key."""
        return self.cache_dir / f"{cache_key}.wav"

    def _synthesize_with_retry(
        self,
        text: str,
        output_path: Path,
        config: SpeakerConfig,
        max_retries: int = 2,
    ) -> Path:
        """
        Synthesize with automatic retry on failure.

        Args:
            text: Text to synthesize
            output_path: Output file path
            config: Speaker configuration
            max_retries: Maximum retry attempts

        Returns:
            Path to synthesized audio
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Check cache first
                if self.cache_enabled:
                    cache_key = self._get_cache_key(text, config)
                    cache_path = self._get_cache_path(cache_key)

                    if cache_path.exists():
                        # Cache hit - copy cached file
                        import shutil
                        shutil.copy(cache_path, output_path)
                        self.stats['cache_hits'] += 1
                        return output_path

                # Cache miss - synthesize
                self.stats['cache_misses'] += 1
                self._synthesize_line(text, output_path, config)

                # Save to cache
                if self.cache_enabled and output_path.exists():
                    cache_key = self._get_cache_key(text, config)
                    cache_path = self._get_cache_path(cache_key)
                    import shutil
                    shutil.copy(output_path, cache_path)

                return output_path

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    self.stats['retries'] += 1
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    self.stats['failures'] += 1
                    raise Exception(f"Failed after {max_retries + 1} attempts: {last_error}")

    def synthesize_dialog_parallel(
        self,
        script_path: Path,
        speaker_map: Dict[str, SpeakerConfig],
        output_path: Path,
        gap_ms: int = 250,
        xfade_ms: int = 20,
        breath_ms: int = 80,
        normalize_dbfs: float = -1.0,
        lufs_target: Optional[float] = None,
        default_speaker: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Path:
        """
        Synthesize dialog with parallel processing and enhanced features.

        Args:
            script_path: Path to dialog script file
            speaker_map: Mapping of speaker names to configurations
            output_path: Output audio file path
            gap_ms: Gap between lines in milliseconds
            xfade_ms: Crossfade duration between sentences in milliseconds
            breath_ms: Short breath pause at sentence boundaries
            normalize_dbfs: Final normalization target in dBFS
            lufs_target: Target LUFS loudness (e.g., -16.0 for podcasts)
            default_speaker: Default speaker for unmapped speakers
            progress_callback: Callback for progress updates (current, total, message)

        Returns:
            Path to output audio file
        """
        start_time = time.time()

        # Build speaker aliases for parser
        speaker_aliases = {}
        for speaker, config in speaker_map.items():
            if config.aliases:
                speaker_aliases[speaker] = config.aliases

        # Parse script
        parser = DialogParser(speaker_aliases=speaker_aliases)
        elements = parser.parse_file(script_path)

        # Check for unknown speakers
        script_speakers = parser.get_speakers(elements)
        unknown_speakers = script_speakers - set(speaker_map.keys())

        if unknown_speakers:
            if default_speaker and default_speaker in speaker_map:
                print(f"Warning: Unknown speakers will use default '{default_speaker}': {unknown_speakers}")
            else:
                raise ValueError(
                    f"Unknown speakers in script: {unknown_speakers}\n"
                    f"Available speakers: {set(speaker_map.keys())}\n"
                    f"Use --default-speaker to specify fallback."
                )

        # Count dialog lines for progress
        dialog_lines = [e for e in elements if isinstance(e, DialogLine)]
        total_lines = len(dialog_lines)

        if progress_callback:
            progress_callback(0, total_lines, "Preparing synthesis...")

        print(f"\nSynthesizing {total_lines} dialog lines with {self.max_workers} parallel workers...")

        # Prepare synthesis tasks
        temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(temp_dir.name)

        synthesis_tasks = []
        for i, element in enumerate(elements):
            if isinstance(element, DialogLine):
                speaker = element.speaker
                text = element.text

                # Get speaker config (or use default)
                if speaker in speaker_map:
                    config = speaker_map[speaker]
                elif default_speaker:
                    config = speaker_map[default_speaker]
                    speaker = default_speaker
                else:
                    raise ValueError(f"No config for speaker '{speaker}' at line {element.line_number}")

                # Split into sentences for better prosody
                from parser_utils import split_sentences
                sentences = split_sentences(text)

                for j, sentence in enumerate(sentences):
                    temp_file = temp_path / f"line_{i:04d}_sent_{j:02d}.wav"
                    synthesis_tasks.append({
                        'index': i,
                        'sentence_index': j,
                        'text': sentence,
                        'config': config,
                        'output_path': temp_file,
                        'speaker': speaker,
                    })

        # Parallel synthesis with progress tracking
        completed_tasks = 0
        audio_segments = []
        sentence_map = {}  # Map (line_index, sentence_index) to audio

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for task in synthesis_tasks:
                    future = executor.submit(
                        self._synthesize_with_retry,
                        task['text'],
                        task['output_path'],
                        task['config'],
                    )
                    future_to_task[future] = task

                # Process completed tasks
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    completed_tasks += 1

                    try:
                        result_path = future.result()

                        # Load and process audio
                        audio = self.audio_processor.load_audio(result_path)
                        audio = self.audio_processor.apply_gain(audio, task['config'].gain_db)

                        if self.stereo:
                            audio = self.audio_processor.apply_pan(audio, task['config'].pan)

                        # Store in sentence map
                        key = (task['index'], task['sentence_index'])
                        sentence_map[key] = audio

                        # Progress callback
                        if progress_callback:
                            progress = int((completed_tasks / len(synthesis_tasks)) * 80)  # 0-80%
                            progress_callback(
                                progress,
                                100,
                                f"Synthesized {completed_tasks}/{len(synthesis_tasks)} segments"
                            )

                        print(f"  [{completed_tasks}/{len(synthesis_tasks)}] {task['speaker']}: {task['text'][:50]}...")

                    except Exception as e:
                        print(f"  ✗ Failed: {task['text'][:50]}... - {e}")

            # Reconstruct dialog in correct order
            if progress_callback:
                progress_callback(85, 100, "Assembling audio segments...")

            print("\nAssembling audio segments...")

            current_line = -1
            for i, element in enumerate(elements):
                if isinstance(element, DialogLine):
                    # Collect all sentences for this line
                    line_sentences = []
                    j = 0
                    while (i, j) in sentence_map:
                        line_sentences.append(sentence_map[(i, j)])
                        j += 1

                    # Concatenate sentences with breath pauses
                    if line_sentences:
                        if len(line_sentences) > 1:
                            breath = self.audio_processor.create_silence(breath_ms)
                            line_audio = line_sentences[0]
                            for seg in line_sentences[1:]:
                                line_audio = self.audio_processor.crossfade(
                                    line_audio + breath, seg, xfade_ms
                                )
                        else:
                            line_audio = line_sentences[0]

                        audio_segments.append(line_audio)

                    current_line = i

                elif isinstance(element, Directive):
                    # Handle directives
                    if element.type == "silence":
                        duration_ms = int(element.params.get('value', 500))
                        silence = self.audio_processor.create_silence(duration_ms)
                        audio_segments.append(silence)
                        print(f"  [silence: {duration_ms}ms]")

                    elif element.type == "sfx":
                        # Load sound effect
                        sfx_path = Path(element.params.get('value', ''))
                        if sfx_path.exists():
                            sfx_audio = self.audio_processor.load_audio(sfx_path)

                            # Apply volume and pan if specified
                            vol = float(element.params.get('vol', 0.0))
                            pan = float(element.params.get('pan', 0.0))

                            sfx_audio = self.audio_processor.apply_gain(sfx_audio, vol)
                            if self.stereo:
                                sfx_audio = self.audio_processor.apply_pan(sfx_audio, pan)

                            audio_segments.append(sfx_audio)
                            print(f"  [sfx: {sfx_path.name}]")
                        else:
                            print(f"  Warning: SFX file not found: {sfx_path}")

            # Concatenate all segments with gaps
            if progress_callback:
                progress_callback(90, 100, "Merging audio...")

            print("\nMerging audio segments...")
            final_audio = self.audio_processor.concatenate(
                audio_segments,
                gap_ms=gap_ms,
                crossfade_ms=0  # Already applied crossfade between sentences
            )

            # Ensure correct format (mono/stereo)
            if self.stereo:
                final_audio = self.audio_processor.ensure_stereo(final_audio)
            else:
                final_audio = self.audio_processor.ensure_mono(final_audio)

            # Normalize
            if progress_callback:
                progress_callback(95, 100, "Normalizing audio...")

            print(f"Normalizing to {normalize_dbfs} dBFS...")
            final_audio = self.audio_processor.normalize(final_audio, normalize_dbfs)

            # LUFS normalization (professional loudness standard)
            if lufs_target and LOUDNORM_AVAILABLE:
                if progress_callback:
                    progress_callback(97, 100, f"Applying LUFS normalization ({lufs_target} LUFS)...")

                print(f"Applying LUFS normalization to {lufs_target} LUFS...")
                final_audio = self._normalize_lufs(final_audio, lufs_target)

            # Export
            if progress_callback:
                progress_callback(98, 100, "Exporting audio...")

            print(f"Exporting to {output_path}...")
            output_format = output_path.suffix[1:] if output_path.suffix else "wav"
            self.audio_processor.export(final_audio, output_path, format=output_format)

            # Statistics
            elapsed = time.time() - start_time
            duration_sec = len(final_audio) / 1000.0

            print(f"\n✓ Successfully created dialog audio: {output_path}")
            print(f"  Duration: {duration_sec:.1f}s")
            print(f"  Processing time: {elapsed:.1f}s ({duration_sec/elapsed:.1f}x realtime)")
            print(f"  Sample rate: {self.sample_rate} Hz")
            print(f"  Channels: {'Stereo' if self.stereo else 'Mono'}")
            print(f"  Cache: {self.stats['cache_hits']} hits, {self.stats['cache_misses']} misses")
            if self.stats['retries'] > 0:
                print(f"  Retries: {self.stats['retries']}")
            if self.stats['failures'] > 0:
                print(f"  ⚠ Failures: {self.stats['failures']}")

            if progress_callback:
                progress_callback(100, 100, "Complete!")

            return output_path

        finally:
            temp_dir.cleanup()

    def _normalize_lufs(self, audio: AudioSegment, target_lufs: float) -> AudioSegment:
        """
        Normalize audio to target LUFS (Loudness Units relative to Full Scale).

        LUFS is a standardized loudness measurement used in broadcasting:
        - -16 LUFS: Podcast/streaming standard
        - -23 LUFS: Broadcast TV standard
        - -14 LUFS: Music streaming (Spotify, YouTube)

        Args:
            audio: Input audio segment
            target_lufs: Target LUFS level (e.g., -16.0)

        Returns:
            Normalized audio segment
        """
        if not LOUDNORM_AVAILABLE:
            print("Warning: pyloudnorm not available, skipping LUFS normalization")
            return audio

        try:
            import numpy as np

            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples())

            # Reshape for stereo
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            else:
                samples = samples.reshape((-1, 1))

            # Normalize to [-1, 1]
            samples = samples.astype(np.float64) / (2 ** (audio.sample_width * 8 - 1))

            # Measure current loudness
            meter = pyln.Meter(audio.frame_rate)
            current_lufs = meter.integrated_loudness(samples)

            # Calculate gain needed
            gain_db = target_lufs - current_lufs

            print(f"  Current: {current_lufs:.1f} LUFS → Target: {target_lufs:.1f} LUFS (gain: {gain_db:+.1f} dB)")

            # Apply gain
            return audio + gain_db

        except Exception as e:
            print(f"Warning: LUFS normalization failed: {e}")
            return audio

    def clear_cache(self):
        """Clear the synthesis cache."""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"Cache cleared: {self.cache_dir}")

    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total = 0
        for file in self.cache_dir.glob("*.wav"):
            total += file.stat().st_size
        return total


def main():
    """CLI entry point with enhanced features."""
    import argparse
    from dialog_tts import load_speaker_map, apply_speaker_name_mapping

    parser = argparse.ArgumentParser(
        description="Enhanced Dialog TTS with parallel synthesis and caching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--script', type=Path, required=True,
                        help='Dialog script file')
    parser.add_argument('--out', type=Path, required=True,
                        help='Output audio file (WAV or MP3)')

    # Engine selection
    parser.add_argument('--engine', choices=['mac', 'xtts', 'edge'], default='edge',
                        help='TTS engine to use (default: edge)')
    parser.add_argument('--model-dir', type=Path,
                        help='XTTS model directory (optional)')

    # Speaker mapping
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--speaker-map', type=Path,
                       help='YAML file with speaker configurations')
    group.add_argument('--voices', nargs='+',
                       help='Speaker voice specs: A="SunHi,rate=180,pan=-0.3"')

    # Custom speaker names
    parser.add_argument('--speaker-names', nargs='+',
                        help='Custom speaker names (e.g., "학생 전문가")')

    # Audio parameters
    parser.add_argument('--sr', '--sample-rate', type=int, default=24000,
                        dest='sample_rate', help='Sample rate in Hz')
    parser.add_argument('--stereo', action='store_true',
                        help='Output stereo audio with panning')
    parser.add_argument('--gap-ms', type=int, default=250,
                        help='Gap between lines in ms')
    parser.add_argument('--xfade-ms', type=int, default=20,
                        help='Crossfade between sentences in ms')
    parser.add_argument('--breath-ms', type=int, default=80,
                        help='Breath pause at sentence boundaries in ms')
    parser.add_argument('--normalize', type=float, default=-1.0,
                        help='Normalization target in dBFS')

    # Enhanced features
    parser.add_argument('--lufs', type=float,
                        help='Target LUFS loudness (e.g., -16 for podcasts)')
    parser.add_argument('--workers', type=int, default=3,
                        help='Parallel synthesis workers (default: 3)')
    parser.add_argument('--cache-dir', type=Path,
                        help='Cache directory for synthesized audio')
    parser.add_argument('--no-cache', action='store_true',
                        help='Disable synthesis caching')
    parser.add_argument('--clear-cache', action='store_true',
                        help='Clear cache and exit')

    # Fallback
    parser.add_argument('--default-speaker',
                        help='Default speaker for unmapped speakers')

    args = parser.parse_args()

    # Initialize enhanced engine
    engine = CachedDialogTTSEngine(
        engine=args.engine,
        sample_rate=args.sample_rate,
        stereo=args.stereo,
        model_dir=args.model_dir,
        cache_dir=args.cache_dir,
        max_workers=args.workers,
    )

    # Disable cache if requested
    if args.no_cache:
        engine.cache_enabled = False

    # Clear cache if requested
    if args.clear_cache:
        engine.clear_cache()
        cache_size = engine.get_cache_size()
        print(f"Cache size: {cache_size / 1024 / 1024:.1f} MB")
        return 0

    # Validate inputs
    if not args.script.exists():
        print(f"Error: Script file not found: {args.script}")
        return 1

    try:
        # Load speaker map
        speaker_map = load_speaker_map(
            file_path=args.speaker_map,
            voices_arg=args.voices,
            engine=args.engine
        )

        # Apply custom speaker names if provided
        if args.speaker_names:
            speaker_map = apply_speaker_name_mapping(
                speaker_map,
                args.speaker_names
            )

        print(f"Loaded configuration for speakers: {list(speaker_map.keys())}")

        # Synthesize dialog with enhanced features
        engine.synthesize_dialog_parallel(
            script_path=args.script,
            speaker_map=speaker_map,
            output_path=args.out,
            gap_ms=args.gap_ms,
            xfade_ms=args.xfade_ms,
            breath_ms=args.breath_ms,
            normalize_dbfs=args.normalize,
            lufs_target=args.lufs,
            default_speaker=args.default_speaker,
        )

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
