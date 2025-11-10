import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from localkoreantts.paths import LK_TTS_CACHE_ENV, LK_TTS_MODEL_ENV


def _home_scoped_dir(suffix: str) -> Path:
    base = Path.home() / ".cache" / "localkoreantts-smoke"
    run_dir = base / suffix
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


@pytest.mark.usefixtures("_mock_ffmpeg_bin")
def test_cli_smoke_creates_wave_and_metadata(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    output_file = artifacts_dir / "sample_out.wav"
    input_file = tmp_path / "input.txt"
    long_text = "\n\n".join(
        [
            "첫 번째 문단입니다. 긴 텍스트 청크 분할을 흉내 내기 위해 여러 문장을 포함합니다.",
            "두 번째 문단은 줄바꿈을 포함하여 CLI가 파일 기반 입력을 그대로 처리하는지 검증합니다.",
            "세 번째 문단은 메타데이터에 전체 본문이 보존되는지를 확인하기 위한 것입니다.",
        ]
    )
    input_file.write_text(long_text, encoding="utf-8")

    fake_ffmpeg = tmp_path / "ffmpeg-mock"
    fake_ffmpeg.write_text("#!/bin/sh\necho 'ffmpeg mock 1.0'\n", encoding="utf-8")
    fake_ffmpeg.chmod(0o755)

    run_root = _home_scoped_dir(f"run-{uuid4().hex}")
    model_dir = run_root / "model"
    cache_dir = run_root / "cache"
    model_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "dummy.bin").write_text("ok", encoding="utf-8")

    env = os.environ.copy()
    env[LK_TTS_MODEL_ENV] = str(model_dir)
    env[LK_TTS_CACHE_ENV] = str(cache_dir)

    command = [
        sys.executable,
        "-m",
        "localkoreantts.cli",
        "--in",
        str(input_file),
        "--out",
        str(output_file),
        "--lang",
        "ko-KR",
        "--speed",
        "1.25",
        "--skip-play",
        "--describe",
        "--ffmpeg-path",
        str(fake_ffmpeg),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert output_file.exists()

        meta_path = output_file.with_suffix(".meta.json")
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        expected_keys = {
            "text",
            "voice",
            "voice_locale",
            "lang",
            "speed",
            "sample_rate",
            "output_file",
            "model_dir",
            "cache_dir",
            "created_at",
            "cli_version",
        }
        assert expected_keys.issubset(meta)
        assert meta["text"] == long_text
        assert meta["lang"] == "ko-KR"
        assert meta["speed"] == 1.25
        assert meta["output_file"] == str(output_file)
        assert meta["model_dir"] == str(model_dir)
        assert meta["cache_dir"] == str(cache_dir)

        stdout_lines = result.stdout.splitlines()
        describe_line = next((line for line in stdout_lines if "platform=" in line), "")
        assert "model_dir=~/" in describe_line
        assert f"Wrote {output_file}" in result.stdout
    finally:
        shutil.rmtree(run_root, ignore_errors=True)
