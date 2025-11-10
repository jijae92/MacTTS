#!/usr/bin/env python3
"""
FFmpeg 설치 상태 확인 스크립트

사용법:
    python check_ffmpeg.py
"""

import sys
import shutil
from pathlib import Path

def check_ffmpeg():
    print("=" * 60)
    print("FFmpeg 설치 상태 확인")
    print("=" * 60)
    print()

    # Check common locations
    locations = [
        ("System PATH", shutil.which('ffmpeg')),
        ("Homebrew (Apple Silicon)", "/opt/homebrew/bin/ffmpeg"),
        ("Homebrew (Intel)", "/usr/local/bin/ffmpeg"),
        ("MacPorts", "/opt/local/bin/ffmpeg"),
    ]

    found_any = False
    for name, path in locations:
        if path and Path(path).exists():
            print(f"✓ {name}: {path}")
            found_any = True

            # Try to get version
            try:
                import subprocess
                result = subprocess.run(
                    [path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0]
                    print(f"  Version: {version_line}")
            except:
                pass
        else:
            print(f"✗ {name}: {'not in PATH' if name == 'System PATH' else 'not found'}")

    print()
    print("-" * 60)

    if found_any:
        print("✓ FFmpeg가 설치되어 있습니다!")
        print()
        print("pydub 테스트:")
        try:
            from pydub import AudioSegment
            print("✓ pydub가 설치되어 있습니다")

            # Try to configure pydub
            ffmpeg_path = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg' or '/usr/local/bin/ffmpeg'
            if ffmpeg_path and Path(ffmpeg_path).exists():
                AudioSegment.converter = ffmpeg_path
                AudioSegment.ffmpeg = ffmpeg_path
                print(f"✓ pydub configured to use: {ffmpeg_path}")
        except ImportError:
            print("✗ pydub가 설치되지 않았습니다")
            print("  설치: pip install pydub")

        print()
        print("MacTTS GUI를 재시작하면 TTS가 작동합니다!")
    else:
        print("✗ FFmpeg를 찾을 수 없습니다!")
        print()
        print("설치 방법:")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        print()
        print("설치 후 이 스크립트를 다시 실행하세요.")
        return 1

    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(check_ffmpeg())
