# Contract: firmware commands used

Source: tuxedo-drivers v4.24.0 (GPL-2.0-or-later). Transport: ACPI `_DSM` of `CLV0001`
(UUID `93f224e4-fbdc-4bbf-add6-db71bdc0afad`, function = command, argument package with one
integer) or WMI method GUID `ABBC0F6D-8EA1-11D1-00A0-C90629100000` (method id = command, 32-bit
input). Events: ACPI notify on `CLV0001`, or WMI event GUID `ABBC0F6B-8EA1-11D1-00A0-C90629100000`.

| Command | Id | Argument | Use |
|---------|----|----------|-----|
| GET_EVENT | 0x01 | 0 | fetch the pending event (WMI: its value is the event code) |
| GET_SPECS | 0x0d | 0 | buffer; byte 0x0f = keyboard backlight type (0x06 1-zone RGB, 0x02 3-zone RGB) |
| SET_EVENTS_ENABLED | 0x46 | 0 | make the firmware report hotkeys |
| GET_BIOS_FEATURES_1 | 0x52 | 0 | sanity check (`0xffffffff` = not this interface); bit 0x00400000 = 3-zone RGB on firmware without GET_SPECS |
| SET_KB_RGB_LEDS | 0x67 | `0xF0000000 \| zone<<24 \| blue<<16 \| red<<8 \| green` | zone colour (zone 0–2) |
| SET_KB_RGB_LEDS | 0x67 | `0xF4000000 \| brightness` | brightness 0–255 |
| OPT | 0x79 | `0x19000000 \| profile` | performance profile 0–3 |

No other command is sent. No command is sent before GET_BIOS_FEATURES_1 has answered.
