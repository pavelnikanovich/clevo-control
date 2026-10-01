# Data Model: clevo-control 1.0

## Backlight state (kernel, per LED device `rgb:kbd_backlight`)

| Field | Type | Range | Source of truth |
|-------|------|-------|-----------------|
| brightness | integer | 0–255 | LED class `brightness`; remembered by systemd-backlight |
| intensity red/green/blue | integer each | 0–255 (values above are clamped) | LED class `multi_intensity`, order given by `multi_index` |
| zones | integer | 1 or 3 | firmware keyboard type, fixed at bind |

Transitions: any write to `brightness` or `multi_intensity` sends the colour to every zone and
then the brightness. Suspend sets the hardware to brightness 0 without changing the stored
values; resume re-applies them. The colour-cycle hotkey replaces the intensities with the next
entry of the palette (the entry after the current colour, or the first entry if the current colour
is not in the palette).

Palette (in order): `ffffff`, `ff0000`, `ff8000`, `ffff00`, `00ff00`, `00ffff`, `0000ff`,
`8000ff`, `ff4080`.

## Firmware profile (kernel, platform-profile handler `clevo`)

| Platform profile | Firmware profile | Firmware value |
|------------------|------------------|----------------|
| `quiet` | quiet | 0 |
| `low-power` | power saving | 1 |
| `performance` | performance | 2 |
| `balanced` | entertainment | 3 |

The firmware cannot be queried. State held by the module: the last profile it set. At bind the
module sets `balanced`; after resume it sets the stored profile again.

## Hotkey event (kernel)

| Firmware code | Meaning | Result |
|---------------|---------|--------|
| 0x81 / 0x20 | backlight down | `KEY_KBDILLUMDOWN` |
| 0x82 / 0x21 | backlight up | `KEY_KBDILLUMUP` |
| 0x9f / 0x3f | backlight on/off | `KEY_KBDILLUMTOGGLE` |
| 0x83 | next colour | handled in the module |
| 0x5d, 0xfc, 0xfd | touchpad | `KEY_F21` (the touchpad-toggle key desktops listen for) |
| 0x85 | airplane mode | `KEY_RFKILL` |
| 0x86, 0xfa, 0xfb | duplicates, volume, mute | ignored |

Events exist only on machines with a supported RGB keyboard (research R3).

## Saved colour (userspace)

- Location: `/var/lib/clevo-control/backlight-color`
- Content: six lowercase hexadecimal digits `rrggbb` followed by a newline
- Validation on read: regular file opened without following symlinks, at most 16 bytes, must match
  `[0-9a-f]{6}` after stripping whitespace; otherwise treated as absent
- Written: when the colour is set through `clevoctl` or the tray, and by `clevoctl backlight save`
  when the service stops

## Colour and brightness arguments (userspace)

- Colour: `#rrggbb`, `rrggbb`, `#rgb`, `rgb` (ASCII hex only, at most one leading `#`) or a name
  from: white, red, orange, yellow, green, cyan, blue, purple, pink, magenta
- Brightness: ASCII digits `0`–max, or ASCII digits followed by `%` (0–100) mapped to
  `round(percent × max / 100)`

## Relationships

```text
firmware ── transport (ACPI _DSM | WMI) ── clevo_laptop ─┬─ LED rgb:kbd_backlight ─ sysfs ─┬─ clevoctl / tray
                                                         ├─ input "Clevo hotkeys" ─ desktop │
                                                         └─ platform profile "clevo" ─ sysfs ┴─ power-profiles-daemon / extension
saved colour ── clevo-control-backlight.service (restore on device add, save on stop)
```
