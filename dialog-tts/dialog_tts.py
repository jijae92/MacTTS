#!/usr/bin/env python3
"""
Dialog TTS - Multi-speaker dialog synthesis tool

Automatically recognizes speaker labels in dialog scripts and synthesizes
each speaker with different voices, then merges into a single audio file.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, List
import yaml

# Import backends
from backends.mac_nsspeech import MacNSSpeechBackend, PYOBJC_AVAILABLE
from backends.mac_say_cli import MacSayBackend
from backends.xtts_backend import XTTSBackend, XTTS_AVAILABLE
from backends.edge_tts_backend import EdgeTTSBackend, EDGE_TTS_AVAILABLE

# Import utilities
from parser_utils import DialogParser, DialogLine, Directive, split_sentences
from audio_utils import AudioProcessor

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub is required. Install with: pip install pydub")
    sys.exit(1)


class SpeakerConfig:
    """Configuration for a single speaker."""

    def __init__(self, config_dict: dict, engine: str = "edge"):
        self.config = config_dict
        self.engine = engine

        # Common parameters
        self.gain_db = float(config_dict.get('gain_db', 0.0))
        self.pan = float(config_dict.get('pan', 0.0))
        self.aliases = config_dict.get('aliases', [])

        # Edge TTS / Mac engine parameters (both use similar config)
        if engine in ("edge", "mac"):
            self.voice_hint = config_dict.get('voice_hint', 'ko_KR')
            self.voice_name = config_dict.get('voice_name')
            self.rate_wpm = int(config_dict.get('rate_wpm', 180))

        # XTTS parameters
        elif engine == "xtts":
            self.ref_wav = Path(config_dict.get('ref_wav', ''))
            self.lang = config_dict.get('lang', 'ko')
            self.speed = float(config_dict.get('speed', 1.0))


class DialogTTSEngine:
    """Main dialog TTS engine."""

    def __init__(
        self,
        engine: str = "edge",
        sample_rate: int = 24000,
        stereo: bool = False,
        model_dir: Optional[Path] = None
    ):
        """
        Initialize dialog TTS engine.

        Args:
            engine: TTS engine to use ("edge", "mac", "xtts")
            sample_rate: Audio sample rate in Hz
            stereo: Whether to output stereo audio
            model_dir: XTTS model directory (optional)
        """
        self.engine = engine
        self.sample_rate = sample_rate
        self.stereo = stereo

        selected_engine = engine

        # Initialize TTS backend
        if selected_engine == "edge":
            if not EDGE_TTS_AVAILABLE:
                print("Edge TTS not available, falling back to macOS backend")
                selected_engine = "mac"
            else:
                self.backend = EdgeTTSBackend()
                print("Using Microsoft Edge TTS for natural, high-quality Korean speech")
                selected_engine = "edge"

        if selected_engine == "xtts":
            if not XTTS_AVAILABLE:
                raise RuntimeError("XTTS backend not available. Install with: pip install TTS")
            self.backend = XTTSBackend(model_dir=model_dir)
        elif selected_engine == "edge":
            # Already handled above
            pass
        else:  # mac
            # Try PyObjC first, fall back to say CLI
            try:
                if PYOBJC_AVAILABLE:
                    self.backend = MacNSSpeechBackend()
                    print("Using macOS NSSpeechSynthesizer backend")
                else:
                    self.backend = MacSayBackend()
                    print("Using macOS 'say' command backend")
            except Exception as e:
                print(f"PyObjC backend failed: {e}")
                self.backend = MacSayBackend()
                print("Using macOS 'say' command backend")

        # Initialize audio processor
        self.audio_processor = AudioProcessor(sample_rate=sample_rate)

    def synthesize_dialog(
        self,
        script_path: Path,
        speaker_map: Dict[str, SpeakerConfig],
        output_path: Path,
        gap_ms: int = 250,
        xfade_ms: int = 20,
        breath_ms: int = 80,
        normalize_dbfs: float = -1.0,
        default_speaker: Optional[str] = None
    ) -> Path:
        """
        Synthesize dialog from script.

        Args:
            script_path: Path to dialog script file
            speaker_map: Mapping of speaker names to configurations
            output_path: Output audio file path
            gap_ms: Gap between lines in milliseconds
            xfade_ms: Crossfade duration between sentences in milliseconds
            breath_ms: Short breath pause at sentence boundaries
            normalize_dbfs: Final normalization target in dBFS
            default_speaker: Default speaker for unmapped speakers

        Returns:
            Path to output audio file
        """
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

        # Synthesize each line
        print(f"\nSynthesizing {len([e for e in elements if isinstance(e, DialogLine)])} dialog lines...")

        audio_segments = []
        temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(temp_dir.name)

        try:
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

                    print(f"  [{i+1}] {speaker}: {text[:50]}...")

                    # Split into sentences for better prosody
                    sentences = split_sentences(text)

                    sentence_segments = []
                    for j, sentence in enumerate(sentences):
                        # Synthesize sentence
                        temp_file = temp_path / f"line_{i:04d}_sent_{j:02d}.wav"
                        self._synthesize_line(sentence, temp_file, config)

                        # Load audio
                        audio = self.audio_processor.load_audio(temp_file)

                        # Apply gain and pan
                        audio = self.audio_processor.apply_gain(audio, config.gain_db)

                        if self.stereo:
                            audio = self.audio_processor.apply_pan(audio, config.pan)

                        sentence_segments.append(audio)

                    # Concatenate sentences with short breath pauses
                    if len(sentence_segments) > 1:
                        breath = self.audio_processor.create_silence(breath_ms)
                        line_audio = sentence_segments[0]
                        for seg in sentence_segments[1:]:
                            line_audio = self.audio_processor.crossfade(
                                line_audio + breath, seg, xfade_ms
                            )
                    else:
                        line_audio = sentence_segments[0]

                    audio_segments.append(line_audio)

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
            print(f"Normalizing to {normalize_dbfs} dBFS...")
            final_audio = self.audio_processor.normalize(final_audio, normalize_dbfs)

            # Export
            print(f"Exporting to {output_path}...")
            output_format = output_path.suffix[1:] if output_path.suffix else "wav"
            self.audio_processor.export(final_audio, output_path, format=output_format)

            duration_sec = len(final_audio) / 1000.0
            print(f"\n✓ Successfully created dialog audio: {output_path}")
            print(f"  Duration: {duration_sec:.1f}s")
            print(f"  Sample rate: {self.sample_rate} Hz")
            print(f"  Channels: {'Stereo' if self.stereo else 'Mono'}")

            return output_path

        finally:
            temp_dir.cleanup()

    def _synthesize_line(self, text: str, output_path: Path, config: SpeakerConfig):
        """Synthesize a single line of dialog."""
        if self.engine == "xtts":
            self.backend.synthesize_to_file(
                text=text,
                output_path=output_path,
                speaker_wav=config.ref_wav,
                language=config.lang,
                speed=config.speed
            )
        elif self.engine == "edge":
            # Edge TTS backend
            self.backend.synthesize_to_file(
                text=text,
                output_path=output_path,
                voice_name=config.voice_name or "Yuna",
                rate_wpm=config.rate_wpm
            )
        else:  # mac
            # Find voice
            if hasattr(self.backend, 'find_voice'):
                voice = self.backend.find_voice(
                    voice_hint=config.voice_hint,
                    voice_name=config.voice_name
                )
            else:
                voice = config.voice_name

            self.backend.synthesize_to_file(
                text=text,
                output_path=output_path,
                voice=voice,
                rate_wpm=config.rate_wpm
            )


def apply_speaker_name_mapping(
    speaker_map: Dict[str, SpeakerConfig],
    custom_names: List[str]
) -> Dict[str, SpeakerConfig]:
    """
    Remap speaker keys to custom names.

    Maps default speakers (A, B, C...) to custom names in order.

    Args:
        speaker_map: Original speaker map with keys like A, B, C
        custom_names: List of custom names in order (e.g., ["학생", "전문가"])

    Returns:
        New speaker map with custom names as keys

    Example:
        Original: {"A": config_a, "B": config_b}
        custom_names: ["학생", "전문가"]
        Result: {"학생": config_a, "전문가": config_b}
    """
    # Get sorted speaker keys (A, B, C...)
    sorted_speakers = sorted(speaker_map.keys())

    if len(custom_names) > len(sorted_speakers):
        raise ValueError(
            f"Too many custom names ({len(custom_names)}) for available speakers ({len(sorted_speakers)})"
        )

    # Create new mapping
    new_map = {}
    for i, custom_name in enumerate(custom_names):
        original_speaker = sorted_speakers[i]
        config = speaker_map[original_speaker]

        # Update aliases to include both original and custom name
        if original_speaker not in config.aliases:
            config.aliases.append(original_speaker)

        new_map[custom_name] = config

    # Add remaining speakers that weren't remapped
    for speaker in sorted_speakers[len(custom_names):]:
        new_map[speaker] = speaker_map[speaker]

    print(f"Speaker name mapping applied:")
    for i, custom_name in enumerate(custom_names):
        print(f"  {sorted_speakers[i]} → {custom_name}")

    return new_map


def load_speaker_map(
    file_path: Optional[Path] = None,
    voices_arg: Optional[List[str]] = None,
    engine: str = "mac"
) -> Dict[str, SpeakerConfig]:
    """
    Load speaker mapping from YAML file or command-line arguments.

    Args:
        file_path: Path to YAML speaker map file
        voices_arg: List of voice specs from --voices argument
        engine: TTS engine being used

    Returns:
        Dictionary mapping speaker names to SpeakerConfig objects
    """
    if file_path:
        # Load from YAML
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        speaker_map = {}
        for speaker, config in data.items():
            speaker_map[speaker] = SpeakerConfig(config, engine=engine)

        return speaker_map

    elif voices_arg:
        # Parse from command line
        # Format: A="ko_KR:Yuna,rate=180,pan=-0.35,gain=0"
        speaker_map = {}

        for spec in voices_arg:
            # Parse speaker=params
            if '=' not in spec:
                continue

            speaker, params_str = spec.split('=', 1)
            speaker = speaker.strip()

            # Remove quotes
            params_str = params_str.strip('"\'')

            # Parse parameters
            params = {}
            for param in params_str.split(','):
                param = param.strip()
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key.strip()] = value.strip()
                elif ':' in param:
                    # Handle voice_hint:voice_name format
                    hint, name = param.split(':', 1)
                    params['voice_hint'] = hint.strip()
                    params['voice_name'] = name.strip()

            speaker_map[speaker] = SpeakerConfig(params, engine=engine)

        return speaker_map

    else:
        raise ValueError("Either --speaker-map or --voices must be provided")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Dialog TTS - Multi-speaker dialog synthesis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using macOS voices with inline configuration
  %(prog)s --script dialog.txt --voices A="ko_KR:Yuna,rate=180,pan=-0.3" B="ko_KR:Jinho,rate=170,pan=+0.3" --out dialog.wav

  # Using speaker map file
  %(prog)s --script dialog.txt --speaker-map speakers.yaml --out dialog.wav --stereo

  # Using custom speaker names (maps A→학생, B→전문가)
  %(prog)s --script dialog.txt --voices A="ko_KR:Yuna" B="ko_KR:Jinho" --speaker-names 학생 전문가 --out dialog.wav --stereo

  # Using XTTS with speaker map
  %(prog)s --script dialog.txt --engine xtts --speaker-map speakers_xtts.yaml --out dialog.wav
        """
    )

    parser.add_argument('--script', type=Path, required=True,
                        help='Dialog script file')
    parser.add_argument('--out', type=Path, required=True,
                        help='Output audio file (WAV or MP3)')

    # Engine selection
    parser.add_argument('--engine', choices=['edge', 'mac', 'xtts'], default='edge',
                        help='TTS engine to use (default: edge)')
    parser.add_argument('--model-dir', type=Path,
                        help='XTTS model directory (optional)')

    # Speaker mapping
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--speaker-map', type=Path,
                       help='YAML file with speaker configurations')
    group.add_argument('--voices', nargs='+',
                       help='Speaker voice specs: A="ko_KR:Yuna,rate=180,pan=-0.3"')

    # Custom speaker names (maps script speakers to custom names)
    parser.add_argument('--speaker-names', nargs='+',
                        help='Custom speaker names in order (e.g., "학생 전문가" maps A→학생, B→전문가)')

    # Audio parameters
    parser.add_argument('--sr', '--sample-rate', type=int, default=24000,
                        dest='sample_rate', help='Sample rate in Hz (default: 24000)')
    parser.add_argument('--stereo', action='store_true',
                        help='Output stereo audio with panning')
    parser.add_argument('--gap-ms', type=int, default=250,
                        help='Gap between lines in ms (default: 250)')
    parser.add_argument('--xfade-ms', type=int, default=20,
                        help='Crossfade between sentences in ms (default: 20)')
    parser.add_argument('--breath-ms', type=int, default=80,
                        help='Breath pause at sentence boundaries in ms (default: 80)')
    parser.add_argument('--normalize', type=float, default=-1.0,
                        help='Normalization target in dBFS (default: -1.0)')

    # Fallback
    parser.add_argument('--default-speaker',
                        help='Default speaker for unmapped speakers')

    args = parser.parse_args()

    # Validate inputs
    if not args.script.exists():
        print(f"Error: Script file not found: {args.script}")
        sys.exit(1)

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

        # Initialize engine
        engine = DialogTTSEngine(
            engine=args.engine,
            sample_rate=args.sample_rate,
            stereo=args.stereo,
            model_dir=args.model_dir
        )

        # Synthesize dialog
        engine.synthesize_dialog(
            script_path=args.script,
            speaker_map=speaker_map,
            output_path=args.out,
            gap_ms=args.gap_ms,
            xfade_ms=args.xfade_ms,
            breath_ms=args.breath_ms,
            normalize_dbfs=args.normalize,
            default_speaker=args.default_speaker
        )

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
