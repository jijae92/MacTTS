#!/usr/bin/env python3
"""
Linux 환경에서 테스트 빌드를 수행합니다.
이는 macOS 앱이 아니며, 코드 검증용입니다.
"""

import PyInstaller.__main__
import sys
from pathlib import Path

print("="*60)
print("MacTTS Linux Test Build")
print("="*60)
print()
print("⚠️  이 빌드는 Linux 전용 실행 파일을 생성합니다.")
print("   macOS .app 번들은 macOS에서만 빌드 가능합니다.")
print()
print("빌드 시작...")
print()

# Simple build for GUI entry point
PyInstaller.__main__.run([
    'gui_entry.py',
    '--name=LocalKoreanTTS-Linux',
    '--onefile',
    '--windowed',
    '--hidden-import=localkoreantts',
    '--hidden-import=localkoreantts.gui',
    '--hidden-import=localkoreantts.engine',
    '--hidden-import=localkoreantts.cli',
    '--hidden-import=PySide6',
    '--hidden-import=edge_tts',
    '--hidden-import=pydub',
    '--collect-all=PySide6',
    '--noconfirm',
    '--clean',
])

print()
print("="*60)
print("빌드 완료")
print("="*60)
print()
print("출력 위치: dist/LocalKoreanTTS-Linux")
print()
print("⚠️  주의: 이 실행 파일은 Linux에서만 작동합니다.")
print("         macOS 앱을 빌드하려면 macOS에서:")
print("         ./build_macos.sh")
print()
