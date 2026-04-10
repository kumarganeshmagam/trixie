"""
Platform detector for Trixie 2.0.

Returns a normalised platform string and exposes platform-specific helpers
so the core never has to branch on sys.platform directly.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def current() -> str:
    """
    Return one of: 'Windows', 'Darwin', 'Linux', 'Android', 'iOS'.
    """
    if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
        return "Android"
    sdk = os.environ.get("SDK_NAME", "")
    if "iphone" in sdk.lower() or os.environ.get("BRIEFCASE_PLATFORM") == "iOS":
        return "iOS"
    return platform.system()


def is_mobile() -> bool:
    return current() in ("Android", "iOS")


def is_desktop() -> bool:
    return current() in ("Windows", "Darwin", "Linux")


def data_dir() -> Path:
    """
    Return the appropriate user-writable data directory for Trixie's files.

    Desktop  → ~/.trixie/
    Android  → /data/data/com.trixie.app/  (or ANDROID_PRIVATE env var)
    iOS      → ~/Documents/trixie/
    """
    plat = current()
    if plat == "Android":
        base = os.environ.get("ANDROID_PRIVATE", "/data/data/com.trixie.app")
        return Path(base) / "trixie"
    if plat == "iOS":
        return Path.home() / "Documents" / "trixie"
    return Path.home() / ".trixie"


def open_file_or_app(target: str) -> str:
    """Open a file or application using the platform's default launcher."""
    plat = current()
    try:
        if plat == "Windows":
            os.startfile(target)  # type: ignore[attr-defined]
        elif plat == "Darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return f"Opened: {target}"
    except Exception as exc:
        return f"Could not open '{target}': {exc}"
