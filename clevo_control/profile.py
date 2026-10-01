# SPDX-License-Identifier: GPL-2.0-or-later
"""Access to the firmware performance profile exposed as a kernel platform profile."""
import os

from .errors import ClevoError, from_oserror

DEFAULT_CLASS_DIR = "/sys/class/platform-profile"
HANDLER_NAME = "clevo"


class Profile:
    """The platform-profile class device registered by the clevo-control kernel module."""

    def __init__(self, class_dir: str = DEFAULT_CLASS_DIR):
        self.class_dir = class_dir

    def _find(self) -> str | None:
        """Directory of the handler, looked up on every call: its index changes on reload."""
        try:
            entries = sorted(os.listdir(self.class_dir))
        except OSError:
            return None
        for entry in entries:
            path = os.path.join(self.class_dir, entry)
            try:
                with open(os.path.join(path, "name"), encoding="ascii", errors="replace") as f:
                    if f.read(256).strip() == HANDLER_NAME:
                        return path
            except OSError:
                continue
        return None

    def available(self) -> bool:
        return self._find() is not None

    def _path(self, name: str) -> str:
        handler = self._find()
        if handler is None:
            raise ClevoError("performance profiles not available: is the clevo-control module "
                             "loaded and are profiles supported on this machine?")
        return os.path.join(handler, name)

    def _read(self, name: str) -> str:
        path = self._path(name)
        try:
            with open(path, encoding="ascii", errors="replace") as f:
                return f.read(4096).strip()
        except OSError as e:
            raise from_oserror(f"read performance {name}", e) from e

    def choices(self) -> list[str]:
        return self._read("choices").split()

    def get(self) -> str:
        return self._read("profile")

    def set(self, profile: str) -> None:
        choices = self.choices()
        if profile not in choices:
            raise ClevoError(f"invalid profile {profile!r}: expected one of {', '.join(choices)}")
        path = self._path("profile")
        try:
            with open(path, "w") as f:
                f.write(profile + "\n")
        except OSError as e:
            raise from_oserror("set performance profile", e) from e
