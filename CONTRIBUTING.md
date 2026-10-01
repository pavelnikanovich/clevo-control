# Contributing

Bug reports, hardware reports and patches are welcome. For a new laptop model see
"Reporting another model" in [docs/hardware.md](docs/hardware.md).

## Layout

| Directory | Content |
|-----------|---------|
| `module/` | the kernel module and its DKMS configuration |
| `clevo_control/`, `bin/` | the Python package behind `clevoctl` and `clevo-control-tray` |
| `extension/` | the GNOME Shell extension (`controller.js` has no shell imports and is tested with gjs) |
| `data/` | device rule, service unit, tmpfiles, desktop entries, AppStream metadata |
| `man/` | manual pages (`@VERSION@` is filled in by `make`) |
| `tests/` | Python tests against a fake sysfs tree, gjs tests of the extension logic |
| `debian/` | Debian packaging |
| `specs/`, `.specify/` | specification, plan and task list (Spec Kit), and the project constitution |

## Building and checking

```bash
make module     # build the kernel module (needs the headers of the running kernel)
make test       # Python tests, and the gjs tests when gjs is installed
make lint       # ruff, mypy, checkpatch, syntax checks, validators, version check
make check      # all of the above
make deb        # Debian packages (debhelper, dh-dkms, dh-python)
```

`make lint` skips checks whose tool is not installed; `STRICT=1 make lint` fails instead.

## Rules

They are spelled out in [.specify/memory/constitution.md](.specify/memory/constitution.md). In
short:

- The module exposes hardware only through existing kernel subsystems, and uses only firmware
  commands documented by an existing GPL implementation. No direct embedded-controller access,
  no fan control.
- Kernel code follows the kernel coding style: `checkpatch.pl --strict` and a `W=1` build are clean.
- Python logic comes with tests; errors reach the user as one line, never as a traceback.
- The version lives in `VERSION` only.
- Anything that depends on hardware is stated as tested only for the hardware it was tested on.

Contributions are accepted under GPL-2.0-or-later. Sign your commits off (`git commit -s`) to
certify the [Developer Certificate of Origin](https://developercertificate.org/).
