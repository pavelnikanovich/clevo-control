# Changelog

## 1.0.0

First public release.

- Kernel module `clevo-control`: RGB keyboard backlight as the LED `rgb:kbd_backlight`, backlight
  Fn keys, firmware performance profiles as a platform profile. Commands go through the
  `CLV0001` ACPI device where it exists and through WMI otherwise.
- `clevoctl`: backlight color and brightness, performance profile, status.
- `clevo-control-tray`: color chooser, presets, brightness slider, profile menu.
- GNOME Shell extension: a Quiet entry in the Power Mode quick-settings menu.
- Device rule, service and tmpfiles entry: settings without root for the `plugdev` group, the
  color remembered across reboots.
- Debian packaging: `clevo-control-dkms`, `clevo-control`, `gnome-shell-extension-clevo-control`.
