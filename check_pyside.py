#!/usr/bin/env python3
"""Lightweight PySide6 diagnostics for macOS developers.

Run this when the GUI fails to launch due to missing platform plugins.
It prints the Qt plugin search path and checks for the Cocoa platform plugin.

If the plugin is missing, rerun with QT_DEBUG_PLUGINS=1 to get verbose logs:

    QT_DEBUG_PLUGINS=1 python check_pyside.py

Refer to README “macOS” for installation and troubleshooting instructions.
"""

from __future__ import annotations

from pathlib import Path
import sys

try:
    from PySide6.QtCore import QLibraryInfo, Qt
except Exception as exc:  # pragma: no cover - script is executed manually
    print("PySide6 import failed:", exc)
    print("Run `pip install .[gui]` or rerun ./mac_bootstrap.sh")
    sys.exit(1)


def main() -> int:
    plugins_dir = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    platforms_dir = plugins_dir / "platforms"
    cocoa_plugin = platforms_dir / "libqcocoa.dylib"

    print(f"Qt plugin directory: {plugins_dir}")
    print(f"Platform plugins: {list(platforms_dir.glob('*'))}")

    if cocoa_plugin.exists():
        print("[OK] Cocoa platform plugin detected.")
        return 0

    print(
        "[WARN] libqcocoa.dylib missing. Set QT_DEBUG_PLUGINS=1 and rerun this "
        "script to inspect Qt's plugin lookup. Reinstall PySide6 via "
        "`pip install --force-reinstall PySide6` or rerun ./mac_bootstrap.sh."
    )
    return 2


if __name__ == "__main__":  # pragma: no cover - manual diagnostic
    raise SystemExit(main())
