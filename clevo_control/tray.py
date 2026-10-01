# SPDX-License-Identifier: GPL-2.0-or-later
"""clevo-control-tray: tray applet for the keyboard backlight and performance profile."""
import contextlib
import sys
from collections.abc import Callable
from functools import partial
from typing import Any

try:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("AyatanaAppIndicator3", "0.1")
    gi.require_version("Notify", "0.7")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
    from gi.repository import Gdk, Gio, GLib, Gtk, Notify
except (ImportError, ValueError) as e:  # ValueError: a typelib is missing
    print(f"clevo-control-tray: missing GTK 3 / AppIndicator bindings: {e}", file=sys.stderr)
    sys.exit(1)

from . import devices
from .colors import NAMED_COLORS, format_color, parse_color, percent_of
from .errors import ClevoError

APP_ID = "io.github.pavelnikanovich.ClevoControl"
ICON = "keyboard-brightness-symbolic"
TITLE = "Keyboard backlight"
PRESETS = ("white", "red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink")
DEVICE_POLL_SECONDS = 3
BRIGHTNESS_POLL_MS = 500


class BrightnessWindow(Gtk.Window):  # type: ignore[misc]
    """A slider with a percentage readout that follows the real brightness."""

    def __init__(self, application: Gtk.Application, report: Callable[[ClevoError], None]):
        super().__init__(application=application, title="Keyboard brightness")
        self._report = report
        self._syncing = False

        self.set_default_size(360, -1)
        self.set_resizable(False)
        self.set_icon_name(ICON)

        self._scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self._scale.set_draw_value(False)
        self._scale.set_hexpand(True)
        self._scale.connect("value-changed", self._on_value_changed)

        self._label = Gtk.Label()
        self._label.set_width_chars(5)
        self._label.set_xalign(1.0)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_border_width(18)
        box.pack_start(self._scale, True, True, 0)
        box.pack_start(self._label, False, False, 0)
        self.add(box)

        self._timer = GLib.timeout_add(BRIGHTNESS_POLL_MS, self._sync)
        self.connect("destroy", self._on_destroy)
        self._sync()

    def _show_percent(self, percent: int) -> None:
        self._label.set_text(f"{percent}%")

    def _sync(self) -> bool:
        """Follow changes made elsewhere (Fn keys, clevoctl, the desktop)."""
        try:
            backlight = devices.backlight()
            percent = percent_of(backlight.get_brightness(), backlight.max_brightness())
        except ClevoError:
            self._scale.set_sensitive(False)
            self._label.set_text("–")
            return True

        self._scale.set_sensitive(True)
        if round(self._scale.get_value()) != percent:
            self._syncing = True
            self._scale.set_value(percent)
            self._syncing = False
        self._show_percent(percent)
        return True

    def _on_value_changed(self, scale: Gtk.Scale) -> None:
        percent = round(scale.get_value())
        self._show_percent(percent)
        if self._syncing:
            return
        try:
            backlight = devices.backlight()
            backlight.set_brightness(round(percent * backlight.max_brightness() / 100))
        except ClevoError as e:
            self._report(e)

    def _on_destroy(self, _window: Gtk.Window) -> None:
        GLib.source_remove(self._timer)


class TrayApplication(Gtk.Application):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._indicator: Any = None
        self._backlight_items: list[Gtk.MenuItem] = []
        self._profile_items: dict[str, Gtk.CheckMenuItem] = {}
        self._profile_widgets: list[Gtk.Widget] = []
        self._updating_profiles = False
        self._color_dialog: Gtk.ColorChooserDialog | None = None
        self._brightness_window: BrightnessWindow | None = None
        self._launched = False

    # Application life cycle

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        Notify.init(TITLE)

        self._indicator = AppIndicator.Indicator.new(
            "clevo-control", ICON, AppIndicator.IndicatorCategory.HARDWARE)
        self._indicator.set_title(TITLE)
        self._indicator.set_menu(self._build_menu())
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        # The indicator is not a window, so nothing else keeps the application alive.
        self.hold()
        self._refresh()
        GLib.timeout_add_seconds(DEVICE_POLL_SECONDS, self._refresh)

    def do_activate(self) -> None:
        # The first activation is the start itself (also at login); a later one means the
        # launcher was used while the applet was already running.
        if self._launched:
            self._choose_color()
        self._launched = True

    # Menu

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        def add(label: str, handler: Callable[[], None], backlight: bool = False) -> None:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", lambda _item: handler())
            menu.append(item)
            if backlight:
                self._backlight_items.append(item)

        add("Choose color…", self._choose_color, backlight=True)
        for name in PRESETS:
            add(name.capitalize(), partial(self._set_color, NAMED_COLORS[name]), backlight=True)
        menu.append(Gtk.SeparatorMenuItem())
        add("Brightness…", self._show_brightness, backlight=True)

        separator = Gtk.SeparatorMenuItem()
        menu.append(separator)
        self._profile_widgets.append(separator)
        group: list[Gtk.RadioMenuItem] = []
        try:
            choices = devices.profile().choices()
        except ClevoError:
            choices = ["quiet", "low-power", "balanced", "performance"]
        for choice in choices:
            item = Gtk.RadioMenuItem.new_with_label(group, f"Profile: {choice}")
            group = item.get_group()
            item.connect("toggled", self._on_profile_toggled, choice)
            menu.append(item)
            self._profile_items[choice] = item
            self._profile_widgets.append(item)

        menu.append(Gtk.SeparatorMenuItem())
        add("Quit", self.quit)

        menu.show_all()
        return menu

    def _refresh(self) -> bool:
        """Reflect devices that appear or disappear and profile changes made elsewhere."""
        has_backlight = devices.backlight().available()
        for item in self._backlight_items:
            item.set_sensitive(has_backlight)

        profile = devices.profile()
        try:
            active = profile.get() if profile.available() else None
        except ClevoError:
            active = None
        for widget in self._profile_widgets:
            widget.set_visible(active is not None)
        if active in self._profile_items and not self._profile_items[active].get_active():
            self._updating_profiles = True
            self._profile_items[active].set_active(True)
            self._updating_profiles = False
        return True

    # Actions

    def _report(self, error: ClevoError) -> None:
        try:
            Notify.Notification.new(TITLE, str(error), ICON).show()
        except GLib.Error:
            print(f"clevo-control-tray: {error}", file=sys.stderr)

    def _set_color(self, color: str) -> None:
        try:
            devices.set_color_and_remember(parse_color(color))
        except ClevoError as e:
            self._report(e)

    def _choose_color(self) -> None:
        if self._color_dialog is not None:
            self._color_dialog.present()
            return

        dialog = Gtk.ColorChooserDialog(title="Keyboard color", use_alpha=False)
        dialog.set_application(self)
        with contextlib.suppress(ClevoError):
            current = Gdk.RGBA()
            if current.parse("#" + format_color(devices.backlight().get_color())):
                dialog.set_rgba(current)
        dialog.connect("response", self._on_color_response)
        self._color_dialog = dialog
        dialog.present()

    def _on_color_response(self, dialog: Gtk.ColorChooserDialog, response: int) -> None:
        if response == Gtk.ResponseType.OK:
            rgba = dialog.get_rgba()
            self._set_color(format_color((round(rgba.red * 255), round(rgba.green * 255),
                                          round(rgba.blue * 255))))
        self._color_dialog = None
        dialog.destroy()

    def _show_brightness(self) -> None:
        if self._brightness_window is None:
            self._brightness_window = BrightnessWindow(self, self._report)
            self._brightness_window.connect("destroy", self._on_brightness_closed)
            self._brightness_window.show_all()
        self._brightness_window.present()

    def _on_brightness_closed(self, _window: Gtk.Window) -> None:
        self._brightness_window = None

    def _on_profile_toggled(self, item: Gtk.RadioMenuItem, choice: str) -> None:
        if self._updating_profiles or not item.get_active():
            return
        try:
            devices.profile().set(choice)
        except ClevoError as e:
            self._report(e)
            self._refresh()


def main() -> int:
    return int(TrayApplication().run(sys.argv))
