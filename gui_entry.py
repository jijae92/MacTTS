"""Standalone entry point for bundling the GUI with PyInstaller.

Used by app_macos.spec per README “macOS packaging”.
"""

from localkoreantts.gui import run


if __name__ == "__main__":
    raise SystemExit(run())
