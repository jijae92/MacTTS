# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller configuration for producing the LocalKoreanTTS macOS .app bundle.

- Collects only PySide6 (no other Qt bindings) to satisfy PyInstaller policy.
- Ships the GUI entry point, README snippet, sample input, and app icon.
- Builds a windowed bundle at dist/localkoreantts-gui/LocalKoreanTTS.app.
"""

import pathlib
from PyInstaller.utils.hooks import collect_submodules

try:
    project_root = pathlib.Path(__file__).parent.resolve()
except NameError:
    project_root = pathlib.Path.cwd()
distpath = (project_root / "dist" / "localkoreantts-gui").as_posix()
workpath = (project_root / "build" / "mac_app").as_posix()
gui_entry = project_root / "gui_entry.py"
resources_dir = project_root / "resources"
icon_file = resources_dir / "app_icon.icns"

block_cipher = None

datas = [
    (str(icon_file), "resources"),
    (str(project_root / "README.md"), "docs"),
    (str(project_root / "sample" / "sample.txt"), "sample"),
]

a = Analysis(
    [gui_entry.as_posix()],
    pathex=[project_root.as_posix()],
    binaries=[],
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
