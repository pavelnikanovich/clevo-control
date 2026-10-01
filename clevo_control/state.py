# SPDX-License-Identifier: GPL-2.0-or-later
"""The remembered backlight colour.

The file is written by members of an unprivileged group and read by root (the
service that restores the colour), so reading is bounded and strict and never
follows a symbolic link, and writing replaces the file atomically.
"""
import contextlib
import os
import re
import stat
import tempfile

from .colors import Color, format_color
from .errors import from_oserror

DEFAULT_STATE = "/var/lib/clevo-control/backlight-color"
_MAX_BYTES = 16
_CONTENT = re.compile(r"[0-9a-fA-F]{6}", re.ASCII)


class ColorState:
    def __init__(self, path: str = DEFAULT_STATE):
        self.path = path

    def load(self) -> Color | None:
        """Return the saved colour, or None if nothing valid is saved."""
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        except OSError:
            return None
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return None
            data = os.read(fd, _MAX_BYTES + 1)
        except OSError:
            return None
        finally:
            os.close(fd)

        if len(data) > _MAX_BYTES:
            return None
        try:
            text = data.decode("ascii").strip()
        except UnicodeDecodeError:
            return None
        if not _CONTENT.fullmatch(text):
            return None
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)

    def save(self, color: Color) -> None:
        """Atomically replace the saved colour."""
        directory = os.path.dirname(self.path)
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(dir=directory, prefix=".backlight-color.")
            with os.fdopen(fd, "w") as f:
                f.write(format_color(color) + "\n")
                # Other members of the group must be able to replace it later.
                os.fchmod(f.fileno(), 0o664)
            os.replace(tmp, self.path)
        except OSError as e:
            if tmp is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp)
            raise from_oserror(f"save the color to {self.path}", e) from e
