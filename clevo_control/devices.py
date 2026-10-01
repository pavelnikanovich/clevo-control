# SPDX-License-Identifier: GPL-2.0-or-later
"""The devices and state file the tools act on.

The environment variables exist for the test suite and for LEDs with another name.
"""
import os

from .backlight import DEFAULT_LED, Backlight
from .colors import Color
from .errors import ClevoError
from .profile import DEFAULT_CLASS_DIR, Profile
from .state import DEFAULT_STATE, ColorState


def backlight() -> Backlight:
    return Backlight(os.environ.get("CLEVO_CONTROL_LED", DEFAULT_LED))


def profile() -> Profile:
    return Profile(os.environ.get("CLEVO_CONTROL_PROFILE_CLASS", DEFAULT_CLASS_DIR))


def color_state() -> ColorState:
    return ColorState(os.environ.get("CLEVO_CONTROL_STATE", DEFAULT_STATE))


def set_color_and_remember(color: Color) -> None:
    """Set the colour and save it; a failed save is reported as such, the colour stays set."""
    backlight().set_color(color)
    try:
        color_state().save(color)
    except ClevoError as e:
        raise ClevoError(f"color set, but {e}") from e
