# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller configuration for producing the LocalKoreanTTS macOS .app bundle.

- Collects only PySide6 (no other Qt bindings) to satisfy PyInstaller policy.
- Ships the GUI entry point, README snippet, sample input, and app icon.
- Builds a windowed bundle at dist/localkoreantts-gui/LocalKoreanTTS.app.
"""

import pathlib
import shutil
from PyInstaller.utils.hooks import collect_submodules

try:
    project_root = pathlib.Path(__file__).parent.resolve()
except NameError:
    project_root = pathlib.Path.cwd()
src_dir = project_root / "src"
distpath = (project_root / "dist" / "localkoreantts-gui").as_posix()
workpath = (project_root / "build" / "mac_app").as_posix()
gui_entry = project_root / "gui_entry.py"
resources_dir = project_root / "resources"
icon_file = resources_dir / "app_icon.icns"
dialog_tts_dir = project_root / "dialog-tts"

block_cipher = None

datas = [
    (str(icon_file), "resources"),
    (str(project_root / "README.md"), "docs"),
    (str(project_root / "sample" / "sample.txt"), "sample"),
]
if dialog_tts_dir.exists():
    for file_path in dialog_tts_dir.rglob("*"):
        if file_path.is_file():
            relative_parent = file_path.relative_to(dialog_tts_dir).parent
            destination = pathlib.Path("dialog-tts") / relative_parent
            datas.append((str(file_path), destination.as_posix()))

# Find and bundle ffmpeg if available
binaries_list = []
ffmpeg_path = shutil.which('ffmpeg')
if ffmpeg_path:
    print(f"✓ Found ffmpeg at: {ffmpeg_path}")
    binaries_list.append((ffmpeg_path, '.'))

    ffprobe_path = shutil.which('ffprobe')
    if not ffprobe_path:
        candidate = pathlib.Path(ffmpeg_path).with_name('ffprobe')
        if candidate.exists():
            ffprobe_path = candidate.as_posix()
    if ffprobe_path:
        print(f"✓ Found ffprobe at: {ffprobe_path}")
        binaries_list.append((ffprobe_path, '.'))
    else:
        print("⚠️  ffprobe not found - dialog synthesis may fail")
else:
    print("⚠️  ffmpeg not found - app will need system ffmpeg installed")

a = Analysis(
    [gui_entry.as_posix()],
    pathex=[project_root.as_posix(), src_dir.as_posix()],
    binaries=binaries_list,
    datas=datas,
    hiddenimports=collect_submodules("PySide6") + [
        'edge_tts',
        'gtts',
        'pydub',
        'asyncio',
        'aiohttp',
        'certifi',
        'tabulate',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "TTS", "torch", "transformers"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="localkoreantts-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="localkoreantts-gui",
)

app = BUNDLE(
    coll,
    name="LocalKoreanTTS.app",
    icon=str(icon_file),
    bundle_identifier="com.localkoreantts.gui",
)
