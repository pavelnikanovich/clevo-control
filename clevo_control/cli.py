# SPDX-License-Identifier: GPL-2.0-or-later
"""clevoctl: keyboard backlight and performance profile of Clevo laptops."""
import argparse
import os
import sys

from . import version
from .backlight import DEFAULT_LED, Backlight
from .colors import NAMED_COLORS, format_color, parse_brightness, parse_color, percent_of
from .errors import ClevoError
from .profile import DEFAULT_CLASS_DIR, Profile
from .state import DEFAULT_STATE, ColorState


def _backlight() -> Backlight:
    return Backlight(os.environ.get("CLEVO_CONTROL_LED", DEFAULT_LED))


def _profile() -> Profile:
    return Profile(os.environ.get("CLEVO_CONTROL_PROFILE_CLASS", DEFAULT_CLASS_DIR))


def _state() -> ColorState:
    return ColorState(os.environ.get("CLEVO_CONTROL_STATE", DEFAULT_STATE))


def cmd_status(_args: argparse.Namespace) -> None:
    lines = []
    backlight = _backlight()
    if backlight.available():
        level, maximum = backlight.get_brightness(), backlight.max_brightness()
        saved = _state().load()
        lines += [
            "backlight:",
            f"  color: #{format_color(backlight.get_color())}",
            f"  brightness: {level}/{maximum} ({percent_of(level, maximum)}%)",
            f"  saved: {'#' + format_color(saved) if saved else 'none'}",
        ]
    else:
        lines.append("backlight: not available")

    profile = _profile()
    lines.append(f"profile: {profile.get() if profile.available() else 'not available'}")
    print("\n".join(lines))


def cmd_backlight_color(args: argparse.Namespace) -> None:
    color = parse_color(args.color)
    _backlight().set_color(color)
    try:
        _state().save(color)
    except ClevoError as e:
        raise ClevoError(f"color set, but {e}") from e


def cmd_backlight_brightness(args: argparse.Namespace) -> None:
    backlight = _backlight()
    backlight.set_brightness(parse_brightness(args.level, backlight.max_brightness()))


def cmd_backlight_on(_args: argparse.Namespace) -> None:
    backlight = _backlight()
    if backlight.get_brightness() == 0:
        backlight.set_brightness(max(1, backlight.max_brightness() // 2))


def cmd_backlight_off(_args: argparse.Namespace) -> None:
    _backlight().set_brightness(0)


def cmd_backlight_save(_args: argparse.Namespace) -> None:
    _state().save(_backlight().get_color())


def cmd_backlight_restore(_args: argparse.Namespace) -> None:
    color = _state().load()
    if color is not None:
        _backlight().set_color(color)


def cmd_profile_list(_args: argparse.Namespace) -> None:
    profile = _profile()
    active = profile.get()
    for choice in profile.choices():
        print(f"{'*' if choice == active else ' '} {choice}")


def cmd_profile_get(_args: argparse.Namespace) -> None:
    print(_profile().get())


def cmd_profile_set(args: argparse.Namespace) -> None:
    _profile().set(args.profile)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clevoctl",
        description="Keyboard backlight and performance profile of Clevo laptops.")
    parser.add_argument("--version", action="version", version=f"clevoctl {version()}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    commands.add_parser("status", help="show backlight and profile").set_defaults(func=cmd_status)

    backlight = commands.add_parser("backlight", help="keyboard backlight")
    actions = backlight.add_subparsers(dest="action", metavar="ACTION", required=True)
    p = actions.add_parser("color", help="set and remember the color")
    p.add_argument("color", metavar="COLOR",
                   help=f"#RRGGBB, #RGB or a name: {', '.join(NAMED_COLORS)}")
    p.set_defaults(func=cmd_backlight_color)
    p = actions.add_parser("brightness", help="set the brightness")
    p.add_argument("level", metavar="LEVEL",
                   help="an absolute level (see 'clevoctl status' for the maximum) "
                        "or a percentage such as 50%%")
    p.set_defaults(func=cmd_backlight_brightness)
    actions.add_parser("on", help="turn the backlight on").set_defaults(func=cmd_backlight_on)
    actions.add_parser("off", help="turn the backlight off").set_defaults(func=cmd_backlight_off)
    actions.add_parser("save", help="remember the color shown now").set_defaults(
        func=cmd_backlight_save)
    actions.add_parser("restore", help="apply the remembered color").set_defaults(
        func=cmd_backlight_restore)

    profile = commands.add_parser("profile", help="firmware performance profile")
    actions = profile.add_subparsers(dest="action", metavar="ACTION", required=True)
    actions.add_parser("list", help="list the profiles, the active one marked with *"
                       ).set_defaults(func=cmd_profile_list)
    actions.add_parser("get", help="print the active profile").set_defaults(func=cmd_profile_get)
    p = actions.add_parser("set", help="set the profile")
    p.add_argument("profile", metavar="PROFILE")
    p.set_defaults(func=cmd_profile_set)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except ClevoError as e:
        print(f"clevoctl: {e}", file=sys.stderr)
        return 1
    return 0
