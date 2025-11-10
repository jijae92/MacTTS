"""Command line interface shared across macOS and Windows.

See README sections “Installation”, “macOS → 3. Run CLI & GUI”, and “CLI usage” for
examples; ARCHITECTURE.md summarizes the entry-point wiring.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from . import __version__
from .audio_io import AudioPlaybackError, play_wav
from .config import describe_environment
from .engine import LocalKoreanTTSEngine, VoiceProfile
from .ffmpeg import describe_ffmpeg, detect_ffmpeg_path
from .models import ModelNotReadyError, ensure_model_ready
from .paths import PathConfig, resolve_path_config


def _voice_lines(voices: Iterable[VoiceProfile]) -> List[str]:
    return [f"{voice.name} ({voice.locale}, {voice.sample_rate} Hz)" for voice in voices]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="localkoreantts",
        description="Offline Korean TTS with optional GUI launcher.",
    )
    parser.add_argument("--text", help="Text to synthesize. Use --input-file for files.")
    parser.add_argument("--input-file", help="Path to a UTF-8 text file to synthesize.")
    parser.add_argument("--in", dest="input_alias", help="Alias for --input-file.")
    parser.add_argument("--voice", default="standard-female", help="Voice preset name.")
    parser.add_argument("--lang", default=None, help="Language/locale hint (e.g., ko-KR).")
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed hint stored in metadata (default: 1.0).",
    )
    parser.add_argument(
        "--output",
        help="Destination WAV file. Defaults to ~/Downloads/latest.wav",
    )
    parser.add_argument("--out", dest="output_alias", help="Alias for --output.")
    parser.add_argument("--list-voices", action="store_true", help="List available voices.")
    parser.add_argument("--play", action="store_true", help="Play result via sounddevice.")
    parser.add_argument(
        "--skip-play",
        action="store_true",
        help="Always skip playback (even if --play is passed).",
    )
    parser.add_argument(
        "--ffmpeg-path",
        help="Explicit ffmpeg binary to aid macOS bundle packaging.",
    )
    parser.add_argument("--describe", action="store_true", help="Print environment info.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"LocalKoreanTTS {__version__}",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = resolve_path_config()
    try:
        ensure_model_ready(config)
    except ModelNotReadyError as exc:
        print(f"Model error: {exc}", file=sys.stderr)
        print(
            "Install a sample bundle via 'python scripts/setup_test_model.py' then retry.",
            file=sys.stderr,
        )
        return 2
    ffmpeg_path = None
    ffmpeg_error = None
    try:
        ffmpeg_path = detect_ffmpeg_path(args.ffmpeg_path)
    except FileNotFoundError as exc:
        ffmpeg_error = str(exc)

    if ffmpeg_path is None and ffmpeg_error is None:
        ffmpeg_error = (
            "ffmpeg not found. Install via 'brew install ffmpeg', "
            "set LK_TTS_FFMPEG_BIN, or pass --ffmpeg-path."
        )

    if ffmpeg_error:
        print(f"FFmpeg notice: {ffmpeg_error}", file=sys.stderr)

    engine = LocalKoreanTTSEngine(
        path_config=config,
        ffmpeg_path=ffmpeg_path,
    )

    if args.describe:
        ffmpeg_line = "ffmpeg=unset"
        if engine.ffmpeg_path:
            ffmpeg_line = describe_ffmpeg(engine.ffmpeg_path)
        print(describe_environment())
        print(ffmpeg_line)

    if args.list_voices:
        for line in _voice_lines(engine.voices()):
            print(line)
        return 0

    text = args.text
    input_file = args.input_file or args.input_alias
    if input_file:
        text = Path(input_file).read_text(encoding="utf-8")
    if not text:
        parser.error("Either --text or --input-file must be provided.")

    destination_arg = args.output or args.output_alias
    if destination_arg:
        destination = Path(destination_arg)
    else:
        # Default to ~/Downloads/latest.wav
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        destination = downloads_dir / "latest.wav"

    selected_voice = engine.voice_for(args.voice)
    result = engine.synthesize_to_file(text=text, voice_name=selected_voice.name, output_path=destination)
    _write_metadata(
        output_path=result,
        voice=selected_voice,
        text=text,
        lang=args.lang,
        speed=args.speed,
        config_path=config,
        ffmpeg_path=engine.ffmpeg_path,
    )
    print(f"Wrote {result}")

    if args.play and not args.skip_play:
        try:
            play_wav(result)
        except AudioPlaybackError as exc:
            print(f"Skipping playback: {exc}", file=sys.stderr)

    return 0


def entry_point() -> None:
    raise SystemExit(main())


def _write_metadata(
    *,
    output_path: Path,
    voice: VoiceProfile,
    text: str,
    lang: Optional[str],
    speed: float,
    config_path: PathConfig,
    ffmpeg_path: Optional[Path],
) -> Path:
    meta_path = output_path.with_name(output_path.stem + ".meta.json")
    payload = {
        "text": text,
        "voice": voice.name,
        "voice_locale": voice.locale,
        "lang": lang or voice.locale,
        "speed": speed,
        "sample_rate": voice.sample_rate,
        "output_file": str(output_path),
        "ffmpeg_path": str(ffmpeg_path) if ffmpeg_path else None,
        "model_dir": str(config_path.model_dir),
        "cache_dir": str(config_path.cache_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cli_version": __version__,
    }
    meta_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta_path


if __name__ == "__main__":  # pragma: no cover
    entry_point()
