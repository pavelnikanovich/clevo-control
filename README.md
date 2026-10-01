# clevo-control

Keyboard backlight, Fn keys and performance profiles for Clevo laptops on Linux.

Clevo builds the laptops sold by many brands (Dream Machines, Sager, XMG, PCSpecialist and
others). Their keyboard backlight and "power modes" are controlled by firmware commands that
Linux does not use by itself. This project provides a kernel module that drives them through
**standard kernel interfaces**, so the desktop handles most of it without knowing about the
module, plus a small set of tools.

| You get | How |
|---------|-----|
| Keyboard color and brightness | the LED `rgb:kbd_backlight`; `clevoctl`, a tray applet, the desktop's keyboard brightness control |
| Backlight Fn keys | reported as standard keys, handled by the desktop; "next color" handled by the module |
| Firmware performance profiles | a kernel platform profile, switched together with the desktop power mode by `power-profiles-daemon` |
| The Quiet profile in GNOME | a GNOME Shell extension adding a fourth entry to the Power Mode menu |

## Supported hardware

| Hardware | Status |
|----------|--------|
| Clevo NH5x_NH7xHP (1-zone RGB keyboard, Intel 11th gen) | developed and tested on it |
| Other Clevo models with a 1-zone RGB keyboard | expected to work; performance profiles need `force_profiles=1` until the board is added to the list |
| 3-zone RGB keyboards | implemented, **not tested**: all zones get the same color |
| Models without the `CLV0001` ACPI device (WMI only) | implemented, **not tested** |
| White-only, per-key or no keyboard backlight | no backlight control; performance profiles only (with `force_profiles=1`) |

Details, measured values and how to report a new model: [docs/hardware.md](docs/hardware.md).

## Requirements

- Linux **6.14 or later** with headers for the running kernel (the module is built by DKMS).
- systemd and udev.
- Membership of the **`plugdev`** group to change settings without root. Desktop users have it by
  default on Debian and Ubuntu; check with `id -nG`, add with `sudo adduser "$USER" plugdev` and
  log in again.
- For the tray applet: GTK 3, PyGObject and AyatanaAppIndicator3; on GNOME also an AppIndicator
  extension (Ubuntu enables one by default).
- For the Quiet menu entry: GNOME Shell 50 and `power-profiles-daemon`.

**Secure Boot**: the kernel only loads the module if it is signed with an enrolled key. DKMS
signs it with the machine owner key of the system; if that key was never enrolled, do it once (on
Ubuntu: `sudo mokutil --import /var/lib/shim-signed/mok/MOK.der`, reboot, confirm in the MOK
screen).

**Conflict**: do not install together with `tuxedo-drivers` (or the older `tuxedo-keyboard`).
Both drive the same firmware interface and register the same LED.

## Install

### Debian, Ubuntu and derivatives

Build the packages (`debhelper`, `dh-dkms`, `dh-python` are needed) and install them:

```bash
sudo apt install debhelper dh-dkms dh-python
make deb
sudo apt install ../clevo-control-dkms_*_all.deb ../clevo-control_*_all.deb \
                 ../gnome-shell-extension-clevo-control_*_all.deb
sudo reboot
gnome-extensions enable clevo-control@pavelnikanovich.github.io   # GNOME only, once per user
```

The three packages are independent: the module, the tools with the tray, and the GNOME
extension. Installing or upgrading them never loads or unloads the module; the new module is used
from the next boot.

### Other distributions

```bash
sudo make install                       # tools, extension and module source (PREFIX=/usr)
sudo dkms install clevo-control/"$(cat VERSION)"
sudo systemd-tmpfiles --create clevo-control.conf
sudo udevadm control --reload
sudo reboot
```

`sudo make uninstall` and `sudo dkms remove clevo-control/"$(cat VERSION)" --all` undo it.

## Usage

### Keyboard backlight

```bash
clevoctl status
clevoctl backlight color '#ff00ff'     # or a name: red, green, blue, white, orange, ...
clevoctl backlight brightness 50%      # or an absolute level
clevoctl backlight off
clevoctl backlight on
```

The color is remembered when it is set and when the system shuts down; the brightness is
remembered by `systemd-backlight`. The raw interface is the LED itself:

```bash
echo "255 0 128" > /sys/class/leds/rgb:kbd_backlight/multi_intensity   # order: see multi_index
echo 128         > /sys/class/leds/rgb:kbd_backlight/brightness        # 0-255
```

### Fn keys

On the NH5x_NH7xHP the backlight keys are on the numeric keypad:

| Keys | Action | Handled by |
|------|--------|------------|
| Fn + `/` | next color: white, red, orange, yellow, green, cyan, blue, purple, pink | the module |
| Fn + `*` | backlight on/off | the desktop (UPower) |
| Fn + `-` / Fn + `+` | brightness down / up | the desktop (UPower) |

### Performance profiles

The firmware profiles (the "power modes" of the Windows control center) follow the desktop power
mode:

| Desktop power mode | Platform profile | Firmware profile | CPU limits on the NH5x_NH7xHP (PL1 / PL2) |
|--------------------|------------------|------------------|-------------------------------------------|
| Quiet (GNOME extension) | `quiet` | quiet | 15 W / 30 W |
| Power Saver | `low-power` | power saving | 30 W / 30 W |
| Balanced | `balanced` | entertainment | 45 W / 93 W |
| Performance | `performance` | performance | 60 W / 109 W |

```bash
powerprofilesctl               # shows "PlatformDriver: platform_profile" when connected
clevoctl profile list
clevoctl profile set quiet
```

The firmware cannot report which profile is active, nor whether it implements the command. The
module therefore offers the profiles only on boards where their effect was measured, sets
`balanced` when it starts and reports the last profile it set. On another board, try
`force_profiles=1` (see below) and please report the result.

### Quiet in the GNOME power menu

GNOME knows three power modes. The extension adds **Quiet** as a fourth entry to the Power Mode
menu of the quick settings. `power-profiles-daemon` treats the `quiet` platform profile as Power
Saver, so the Power panel of GNOME Settings (a separate program that cannot be extended) shows
Power Saver while Quiet is active. If a future GNOME Shell does not let the menu be extended, or
`power-profiles-daemon` is not running, the extension shows a separate **Quiet Mode** toggle.

### Tray applet

`clevo-control-tray` starts on login: color chooser, preset colors, a brightness window with a
slider, and the performance profile. Starting it again opens the color chooser of the running
instance.

## Module parameters

Put `options clevo-control name=value` into a file under `/etc/modprobe.d/`.

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `force_rgb` | `N` | treat the keyboard as 1-zone RGB when the firmware reports no RGB keyboard |
| `force_profiles` | `N` | offer the performance profiles on a board they were not verified on |

## Troubleshooting

```bash
sudo dmesg | grep clevo-control      # "1-zone RGB keyboard backlight", "performance profiles enabled"
dkms status clevo-control
clevoctl status
cat /sys/class/platform-profile/*/name
```

- **Nothing in `dmesg`, no LED**: the module is not loaded. Check `dkms status` (kernel older than
  6.14 is skipped) and Secure Boot (see Requirements).
- **`permission denied` from `clevoctl` or the tray**: you are not in the `plugdev` group.
- **Brightness keys show the on-screen indicator but nothing changes, or `powerprofilesctl` shows
  `PlatformDriver: placeholder`**: the desktop services were started before the module was
  loaded. Reboot.
- **The keyboard is RGB but no backlight device appears**: load the module with `force_rgb=1` and
  report the model.

## Scope

Keyboard backlight, its Fn keys and the firmware performance profiles, through firmware commands
documented by an existing GPL implementation. Fan control and direct embedded-controller access
are out of scope on purpose.

Manual pages: `clevo-control(7)`, `clevoctl(1)`, `clevo-control-tray(1)`.
Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).

## License and credits

GPL-2.0-or-later, see [LICENSE](LICENSE).

The firmware protocol spoken by the module (command and sub-command numbers, keyboard type
detection, hotkey event codes, the 1-zone color calibration factors and the performance profile
numbering) is taken from
[tuxedo-drivers](https://gitlab.com/tuxedocomputers/development/packages/tuxedo-drivers) v4.24.0,
Copyright (c) TUXEDO Computers GmbH, GPL-2.0-or-later (`clevo_interfaces.h`, `clevo_leds.h`,
`clevo_keyboard.h`, `clevo_wmi.c`, `clevo_acpi.c`, `tuxedo_io/tuxedo_io.c`). The code of the module
is written from scratch around that protocol.
