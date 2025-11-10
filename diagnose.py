#!/usr/bin/env python3
"""
MacTTS 진단 스크립트 - 모든 문제를 확인합니다

사용법:
    python diagnose.py
"""

import sys
import shutil
from pathlib import Path

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_ffmpeg():
    print_section("1. FFmpeg 설치 확인")

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

            # Get version
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
                    print(f"  {version_line}")
            except Exception as e:
                print(f"  (버전 확인 실패: {e})")
        else:
            print(f"✗ {name}: not found")

    if not found_any:
        print("\n⚠️  PROBLEM: ffmpeg가 설치되지 않았습니다!")
        print("해결: brew install ffmpeg")
        return False

    return True

def check_pydub():
    print_section("2. pydub 설정 확인")

    try:
        from pydub import AudioSegment
        print("✓ pydub 설치됨")

        # Check if pydub can find ffmpeg
        import shutil
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            ffmpeg_path = '/opt/homebrew/bin/ffmpeg' if Path('/opt/homebrew/bin/ffmpeg').exists() else None
        if not ffmpeg_path:
            ffmpeg_path = '/usr/local/bin/ffmpeg' if Path('/usr/local/bin/ffmpeg').exists() else None

        if ffmpeg_path:
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffmpeg = ffmpeg_path
            print(f"✓ pydub configured to use: {ffmpeg_path}")

            # Test conversion
            try:
                # This will fail but shows if ffmpeg is accessible
                print("  Testing ffmpeg access...")
                test_path = Path("/tmp/test_nonexistent.mp3")
                AudioSegment.from_mp3(str(test_path))
            except FileNotFoundError:
                print("  ✓ ffmpeg is accessible (file not found is expected)")
            except Exception as e:
                if "does not exist" in str(e) or "No such file" in str(e):
                    print("  ✓ ffmpeg is accessible")
                else:
                    print(f"  ✗ ffmpeg error: {e}")
                    return False
        else:
            print("✗ pydub cannot find ffmpeg")
            return False

    except ImportError:
        print("✗ pydub not installed")
        print("해결: pip install pydub")
        return False

    return True

def check_tts_engines():
    print_section("3. TTS 엔진 확인")

    engines_ok = True

    # edge-tts
    try:
        import edge_tts
        print("✓ edge-tts 설치됨")
    except ImportError:
        print("✗ edge-tts not installed")
        print("  해결: pip install edge-tts")
        engines_ok = False

    # gtts
    try:
        from gtts import gTTS
        print("✓ gtts 설치됨")
    except ImportError:
        print("✗ gtts not installed")
        print("  해결: pip install gtts")
        engines_ok = False

    return engines_ok

def check_dialog_tts():
    print_section("4. Dialog-TTS 확인")

    # Check if dialog-tts directory exists
    project_root = Path(__file__).parent
    dialog_tts_dir = project_root / "dialog-tts"

    if not dialog_tts_dir.exists():
        print(f"✗ dialog-tts 디렉토리가 없습니다: {dialog_tts_dir}")
        print("  해결: dialog-tts 서브모듈을 클론하거나 다운로드하세요")
        return False

    print(f"✓ dialog-tts 디렉토리 존재: {dialog_tts_dir}")

    # Check for dialog_tts.py
    dialog_tts_py = dialog_tts_dir / "dialog_tts.py"
    if not dialog_tts_py.exists():
        print(f"✗ dialog_tts.py 파일이 없습니다: {dialog_tts_py}")
        return False

    print(f"✓ dialog_tts.py 파일 존재")

    # Try importing
    try:
        sys.path.insert(0, str(dialog_tts_dir))
        from dialog_tts import DialogTTSEngine, SpeakerConfig, apply_speaker_name_mapping
        print("✓ dialog-tts 모듈 import 성공")
        print(f"  - DialogTTSEngine: {DialogTTSEngine}")
        print(f"  - SpeakerConfig: {SpeakerConfig}")
        return True
    except Exception as e:
        print(f"✗ dialog-tts import 실패: {e}")
        print(f"  에러 타입: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def check_gui():
    print_section("5. GUI 의존성 확인")

    try:
        from PySide6 import QtCore, QtGui, QtWidgets
        print("✓ PySide6 설치됨")
        print(f"  버전: {QtCore.__version__}")
        return True
    except ImportError as e:
        print("✗ PySide6 not installed")
        print("  해결: pip install PySide6")
        return False

def main():
    print("=" * 60)
    print("  MacTTS 진단 도구")
    print("=" * 60)

    results = {
        "ffmpeg": check_ffmpeg(),
        "pydub": check_pydub(),
        "tts_engines": check_tts_engines(),
        "dialog_tts": check_dialog_tts(),
        "gui": check_gui(),
    }

    print_section("진단 결과 요약")

    all_ok = all(results.values())

    for name, status in results.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {name}: {'OK' if status else 'FAILED'}")

    print("\n" + "=" * 60)

    if all_ok:
        print("✓ 모든 검사 통과!")
        print("\nGUI 실행 방법:")
        print("  python -m localkoreantts.gui")
        print("  또는")
        print("  python gui_entry.py")
    else:
        print("✗ 일부 검사 실패")
        print("\n위의 해결 방법을 따라 문제를 해결하세요.")

        # Specific recommendations
        if not results["ffmpeg"] or not results["pydub"]:
            print("\n🔧 사인파 문제 해결:")
            print("  1. brew install ffmpeg")
            print("  2. GUI 재시작")

        if not results["dialog_tts"]:
            print("\n🔧 대화 형식 탭 문제 해결:")
            print("  1. dialog-tts 디렉토리 확인")
            print("  2. 필요한 파일이 있는지 확인")

        return 1

    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
