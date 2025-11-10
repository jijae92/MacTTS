#!/usr/bin/env python3
"""Download a sample Coqui TTS model into the LocalKoreanTTS model directory."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from localkoreantts.paths import resolve_path_config

MODEL_DIR_NAME = "coqui-tts-tacotron2-ddc"
LICENSE_LINK = "https://github.com/coqui-ai/TTS#license"
DEFAULT_FILE_SOURCES = [
    {
        "url": "https://raw.githubusercontent.com/coqui-ai/TTS/main/tests/data/dummy_speakers.pth",
        "target": "dummy_speakers.pth",
        "note": "weights",
    },
    {
        "url": "https://raw.githubusercontent.com/coqui-ai/TTS/main/tests/data/dummy_speakers.json",
        "target": "dummy_speakers.json",
        "note": "config",
    },
]


def download_file(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in ("", None):
        src = Path(url).expanduser()
        shutil.copy2(src, destination)
        return
    if parsed.scheme == "file":
        local_path = Path(urllib.request.url2pathname(parsed.path))
        shutil.copy2(local_path, destination)
        return

    with urllib.request.urlopen(url) as response, destination.open("wb") as fh:
        shutil.copyfileobj(response, fh)


def extract_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(destination)


def copy_to_model_dir(source_root: Path, target_root: Path) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    for entry in source_root.iterdir():
        dest = target_root / entry.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        if entry.is_dir():
            shutil.copytree(entry, dest)
        else:
            shutil.copy2(entry, dest)

def write_license_file(target_root: Path, sources: list[str]) -> None:
    license_note = target_root / "MODEL_SOURCE.txt"
    lines = [
        "Sample resources downloaded from Coqui TTS for testing only.",
        f"License: {LICENSE_LINK}",
        "Sources:",
    ]
    lines.extend(f"- {src}" for src in sources)
    license_note.write_text("\n".join(lines) + "\n", encoding="utf-8")


def install_default_bundle(target_dir: Path) -> None:
    sources: list[str] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for spec in DEFAULT_FILE_SOURCES:
        dest = target_dir / spec["target"]
        print(f"Downloading {spec['note']} from {spec['url']}")
        download_file(spec["url"], dest)
        sources.append(spec["url"])
    write_license_file(target_dir, sources)


def install_from_archive(archive_url: str, target_dir: Path) -> None:
    print(f"Downloading sample model from {archive_url}")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_path = tmp_path / "model.zip"
        download_file(archive_url, archive_path)
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        extract_zip(archive_path, extract_dir)

        candidates = [p for p in extract_dir.iterdir() if p.is_dir()]
        if len(candidates) == 1:
            source_root = candidates[0]
        elif candidates:
            source_root = candidates[0]
        else:
            source_root = extract_dir
        print(f"Copying files into {target_dir}")
        copy_to_model_dir(source_root, target_dir)
    write_license_file(target_dir, [archive_url])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite even if the model already exists.",
    )
    args = parser.parse_args(argv)

    config = resolve_path_config()
    target_dir = (config.model_dir / MODEL_DIR_NAME).resolve()
    sentinel = target_dir / "MODEL_SOURCE.txt"
    if sentinel.exists() and not args.force:
        print(f"Model already present at {target_dir}. Use --force to overwrite.")
        return 0

    model_url = os.environ.get("LK_TTS_TEST_MODEL_URL")
    if model_url:
        install_from_archive(model_url, target_dir)
    else:
        install_default_bundle(target_dir)

    print("Model installation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
