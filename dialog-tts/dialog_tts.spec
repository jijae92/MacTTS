# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for Dialog TTS
Builds a standalone CLI executable for macOS
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from pydub
pydub_datas = collect_data_files('pydub')

# Collect backend modules
backend_modules = collect_submodules('backends')

a = Analysis(
    ['dialog_tts.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include config files
        ('config/*.yaml', 'config'),
        # Include sample files
        ('samples/*.txt', 'samples'),
    ] + pydub_datas,
    hiddenimports=[
        'pydub',
        'pydub.utils',
        'pydub.effects',
        'pydub.generators',
        'pydub.silence',
        'yaml',
        'backends.mac_nsspeech',
        'backends.mac_say_cli',
        'backends.xtts_backend',
    ] + backend_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude XTTS heavy dependencies to keep size down
        'TTS',
        'torch',
        'tensorflow',
        'tkinter',
        'matplotlib',
        'scipy',
    ],
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
    name='dialog-tts',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # CLI tool
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
    name='dialog-tts',
)
