# SPDX-License-Identifier: GPL-2.0-or-later
"""Access to the keyboard backlight LED exposed by the clevo-control kernel module."""
import os

from .colors import Color
from .errors import ClevoError, from_oserror

DEFAULT_LED = "/sys/class/leds/rgb:kbd_backlight"
_CHANNELS = ("red", "green", "blue")


class Backlight:
    """The multicolour LED class device of the keyboard backlight."""

    def __init__(self, path: str = DEFAULT_LED):
        self.path = path

    def available(self) -> bool:
        return os.path.isdir(self.path)

    def _check(self) -> None:
        if not self.available():
            raise ClevoError(f"keyboard backlight not found ({self.path}): "
                             "is the clevo-control module loaded?")

    def _read(self, name: str) -> str:
        self._check()
        try:
            with open(os.path.join(self.path, name), encoding="ascii", errors="replace") as f:
                return f.read(4096).strip()
        except OSError as e:
            raise from_oserror(f"read backlight {name}", e) from e

    def _write(self, name: str, value: str) -> None:
        self._check()
        try:
            with open(os.path.join(self.path, name), "w") as f:
                f.write(value + "\n")
        except OSError as e:
            raise from_oserror(f"set backlight {name}", e) from e

    def _read_int(self, name: str) -> int:
        text = self._read(name)
        if not (text.isascii() and text.isdigit()):
            raise ClevoError(f"unexpected backlight {name}: {text[:40]!r}")
        return int(text)

    def _channels(self) -> list[str]:
        """Channel names in the order multi_intensity uses."""
        channels = self._read("multi_index").split()
        if sorted(channels) != sorted(_CHANNELS):
            raise ClevoError(f"unexpected backlight channels: {' '.join(channels)[:60]!r}")
        return channels

    def max_brightness(self) -> int:
        return self._read_int("max_brightness")

    def get_brightness(self) -> int:
        return self._read_int("brightness")

    def set_brightness(self, level: int) -> None:
        maximum = self.max_brightness()
        if not 0 <= level <= maximum:
            raise ClevoError(f"brightness {level} out of range 0-{maximum}")
        self._write("brightness", str(level))

    def get_color(self) -> Color:
        channels = self._channels()
        fields = self._read("multi_intensity").split()
        if len(fields) != len(channels) or not all(f.isascii() and f.isdigit() for f in fields):
            raise ClevoError(f"unexpected backlight multi_intensity: {' '.join(fields)[:60]!r}")
        values = {ch: min(int(f), 255) for ch, f in zip(channels, fields, strict=True)}
        return values["red"], values["green"], values["blue"]

    def set_color(self, color: Color) -> None:
        values = dict(zip(_CHANNELS, color, strict=True))
        self._write("multi_intensity", " ".join(str(values[ch]) for ch in self._channels()))
