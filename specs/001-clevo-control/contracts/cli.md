# Contract: `clevoctl`

```text
clevoctl status
clevoctl backlight color COLOR
clevoctl backlight brightness LEVEL
clevoctl backlight on | off
clevoctl backlight save | restore
clevoctl profile list | get
clevoctl profile set PROFILE
clevoctl --version
```

| Command | Effect | Output (stdout) |
|---------|--------|-----------------|
| `status` | none | lines `backlight:`, `  color: #rrggbb`, `  brightness: N/MAX (P%)`, `  saved: #rrggbb` or `none`, `profile: NAME` (sections for absent devices read `not available`) |
| `backlight color COLOR` | sets the colour and saves it | nothing |
| `backlight brightness LEVEL` | sets the brightness (`N` or `N%`) | nothing |
| `backlight on` | if brightness is 0, sets `max(1, MAX // 2)` | nothing |
| `backlight off` | sets brightness 0 | nothing |
| `backlight save` | saves the colour currently shown | nothing |
| `backlight restore` | applies the saved colour; nothing saved is not an error | nothing |
| `profile list` | none | one profile per line, the active one marked with `*` |
| `profile get` | none | active profile name |
| `profile set PROFILE` | writes the platform profile | nothing |

Exit status: `0` success; `1` device missing, permission denied, invalid value, I/O error (one
line on stderr, prefixed `clevoctl: `); `2` usage error (argparse).

Permission errors name the `plugdev` group. No command prints a traceback.

Environment (testing hooks, also usable for other LED names): `CLEVO_CONTROL_LED`,
`CLEVO_CONTROL_PROFILE_CLASS`, `CLEVO_CONTROL_STATE`.
