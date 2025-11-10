# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the LocalKoreanTTS GUI on macOS.

Notes:
- We rely on the user-provided LK_TTS_MODEL_PATH / LK_TTS_CACHE_DIR at runtime,
  so models/audio assets are NOT bundled.
- PySide6 Qt libraries are automatically collected through hidden imports.
- Set an icon by editing the `icon` parameter if one becomes available.
"""

import pathlib
from PyInstaller.utils.hooks import collect_submodules

try:
    project_root = pathlib.Path(__file__).parent.resolve()
except NameError:  # when spec is executed via exec without __file__
    project_root = pathlib.Path.cwd()
gui_script = project_root / "gui_entry.py"

block_cipher = None

a = Analysis(
    [gui_script.as_posix()],
    pathex=[project_root.as_posix()],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules("PySide6"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="localkoreantts-gui.app",
    icon=None,
    bundle_identifier="com.localkorean.tts",
)
