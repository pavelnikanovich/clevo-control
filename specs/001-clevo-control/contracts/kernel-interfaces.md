# Contract: interfaces exposed by the `clevo-control` module

## LED: `/sys/class/leds/rgb:kbd_backlight` (only with a supported RGB keyboard)

| Attribute | Access | Meaning |
|-----------|--------|---------|
| `brightness` | rw | 0–`max_brightness` |
| `max_brightness` | r | 255 |
| `multi_index` | r | `red green blue` |
| `multi_intensity` | rw | three integers, order per `multi_index`; values above 255 act as 255 |

Flags: suspends with the system (off while suspended, restored on resume).

## Input device: `Clevo hotkeys` (only with a supported RGB keyboard)

Keys: `KEY_KBDILLUMDOWN`, `KEY_KBDILLUMUP`, `KEY_KBDILLUMTOGGLE`, `KEY_F21` (touchpad toggle),
`KEY_RFKILL`. Each firmware event produces one press and
release, with `MSC_SCAN` carrying the firmware code.

## Platform profile: handler `clevo` (when profile support is established)

Choices: `quiet`, `low-power`, `balanced`, `performance`. Reading returns the last profile set by
the module. Visible through `/sys/class/platform-profile/*/` (attributes `name`, `choices`,
`profile`) and the legacy `/sys/firmware/acpi/platform_profile`.

## Module parameters

| Parameter | Type | Default | Meaning |
|-----------|------|---------|---------|
| `force_rgb` | bool | N | treat the keyboard as 1-zone RGB when the firmware does not report an RGB type |
| `force_profiles` | bool | N | register the performance profiles on a board that is not in the allow-list |

## Log messages (stable enough to quote in documentation)

- `clevo-control <device>: N-zone RGB keyboard backlight` (info, once at bind)
- `clevo-control <device>: performance profiles enabled` (info, once at bind)
- failures to set up the backlight or the profiles are reported as errors or warnings; everything
  else is at debug level
