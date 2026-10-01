# SPDX-License-Identifier: GPL-2.0-or-later
"""Parsing and formatting of colours and brightness levels."""
import re

from .errors import ClevoError

Color = tuple[int, int, int]

NAMED_COLORS = {
    "white": "ffffff",
    "red": "ff0000",
    "orange": "ff8000",
    "yellow": "ffff00",
    "green": "00ff00",
    "cyan": "00ffff",
    "blue": "0000ff",
    "purple": "8000ff",
    "pink": "ff4080",
    "magenta": "ff00ff",
}

_HEX = re.compile(r"#?([0-9a-f]{6}|[0-9a-f]{3})", re.ASCII)
_LEVEL = re.compile(r"([0-9]+)(%?)", re.ASCII)


def parse_color(text: str) -> Color:
    """Return (red, green, blue) for '#rrggbb', 'rrggbb', '#rgb', 'rgb' or a colour name."""
    value = text.strip().lower()
    value = NAMED_COLORS.get(value, value)
    match = _HEX.fullmatch(value)
    if not match:
        raise ClevoError(f"invalid color {text.strip()!r}: expected #RRGGBB or one of "
                         f"{', '.join(NAMED_COLORS)}")
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def format_color(color: Color) -> str:
    """Return 'rrggbb'."""
    return "{:02x}{:02x}{:02x}".format(*color)


def parse_brightness(text: str, maximum: int) -> int:
    """Return an absolute level for 'N' (0..maximum) or 'N%' (0..100)."""
    error = ClevoError(f"invalid brightness {text.strip()!r}: expected 0-{maximum} or 0%-100%")
    match = _LEVEL.fullmatch(text.strip())
    if not match:
        raise error
    number = int(match.group(1))
    if match.group(2):
        if number > 100:
            raise error
        return round(number * maximum / 100)
    if number > maximum:
        raise error
    return number


def percent_of(level: int, maximum: int) -> int:
    """Return level as a rounded percentage of maximum."""
    return round(level * 100 / maximum) if maximum > 0 else 0
