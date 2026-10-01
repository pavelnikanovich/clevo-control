# SPDX-License-Identifier: GPL-2.0-or-later
"""Userspace side of clevo-control: keyboard backlight and performance profiles."""
from pathlib import Path


def version() -> str:
    """Version of the installed package, or of the source tree when run from it."""
    here = Path(__file__).resolve().parent
    # _version is written at install time; the source tree has VERSION next to the package.
    for candidate in (here / "_version", here.parent / "VERSION"):
        try:
            return candidate.read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError):
            continue
    return "unknown"
