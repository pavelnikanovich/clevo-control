# Hardware notes

Facts about the firmware interface and what was measured. The commands themselves are listed in
the header of `module/clevo-control.c`.

## Firmware interfaces

| Interface | Identifier | Used for |
|-----------|------------|----------|
| ACPI device | `CLV0001` (`\_SB.DCHU` on the reference machine), `_DSM` UUID `93f224e4-fbdc-4bbf-add6-db71bdc0afad` | commands and hotkey notifications on newer models; preferred when present |
| WMI method | `ABBC0F6D-8EA1-11D1-00A0-C90629100000` | commands on models without `CLV0001` |
| WMI event | `ABBC0F6B-8EA1-11D1-00A0-C90629100000` | hotkeys on models without `CLV0001` |

On the reference machine all three exist; hotkeys are delivered only through `CLV0001`.

## Keyboard types

The firmware reports the keyboard backlight type in byte `0x0f` of the `GET_SPECS` reply:

| Type | Keyboard | Support |
|------|----------|---------|
| `0x06` | 1-zone RGB | yes (reference machine) |
| `0x02` | 3-zone RGB | yes, one color for all zones, untested |
| `0x01` | white only | not driven |
| `0xf3` | per-key RGB | not driven |

Firmware without `GET_SPECS` reports a 3-zone RGB keyboard as bit `0x00400000` of
`GET_BIOS_FEATURES_1`.

On 1-zone keyboards red is scaled by 180/255 and blue by 200/255, otherwise white looks pink.

## Hotkey events

| Code | Key on the NH5x_NH7xHP | Result |
|------|------------------------|--------|
| `0x81` | Fn + `-` | `KEY_KBDILLUMDOWN` |
| `0x82` | Fn + `+` | `KEY_KBDILLUMUP` |
| `0x9f` | Fn + `*` | `KEY_KBDILLUMTOGGLE` |
| `0x83` | Fn + `/` | next color, handled in the module |
| `0x20`, `0x21`, `0x3f` | (other models) | down, up, toggle |
| `0x5d`, `0xfc`, `0xfd` | touchpad | `KEY_F21` |
| `0x85` | airplane mode | `KEY_RFKILL` |
| `0x86`, `0xfa`, `0xfb` | duplicate rfkill, volume, mute | ignored |

Volume, screen brightness, webcam (Fn + F10 cuts the camera's USB power), touchpad and
airplane-mode keys work on the reference machine without this module.

## Performance profiles

Command `0x79`, argument `0x19000000 | profile`. The firmware has no command to read the profile.

Measured on the NH5x_NH7xHP (i7-11800H) from the RAPL package limits
(`/sys/class/powercap/intel-rapl:0`) and a 12 second all-core load:

| Firmware profile | Value | PL1 / PL2 | Package power under load | Peak temperature |
|------------------|-------|-----------|--------------------------|------------------|
| quiet | 0 | 15 W / 30 W | 19 W | 73 °C |
| power saving | 1 | 30 W / 30 W | 30 W | 78 °C |
| performance | 2 | 60 W / 109 W | 41 W | 97 °C |
| entertainment | 3 | 45 W / 93 W | 38 W | 93 °C |

The limits before any profile was set were 45 W / 93 W, so the firmware starts in
"entertainment".

## Desktop behaviour worth knowing

- UPower and `power-profiles-daemon` look for the keyboard backlight and the platform profile when
  they start. A module loaded later is only half noticed; reboot after the first installation.
- `power-profiles-daemon` 0.30 maps the platform profiles `low-power` and `quiet` both to Power
  Saver, does not rewrite the platform profile for the mode it already considers active, and
  notices an external change after about two seconds.

## Test matrix

| Item | NH5x_NH7xHP, kernel 7.0, Ubuntu 26.04 |
|------|----------------------------------------|
| Commands through `CLV0001` `_DSM` | see the hardware checklist result in the release notes |
| Commands through WMI | not exercised by this module on this machine (ACPI is preferred) |
| 3-zone keyboard, WMI-only event delivery | no hardware available |

## Reporting another model

Open an issue with:

```bash
cat /sys/class/dmi/id/board_name
uname -r
sudo dmesg | grep clevo-control
ls /sys/bus/acpi/devices/ | grep CLV
ls /sys/bus/wmi/devices/
```

and, for performance profiles, the RAPL limits after `clevoctl profile set` for each profile:

```bash
grep . /sys/class/powercap/intel-rapl:0/constraint_*_power_limit_uw
```
