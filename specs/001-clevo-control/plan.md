# Implementation Plan: clevo-control 1.0

**Branch**: `main` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-clevo-control/spec.md`

## Summary

Rebuild Clevo laptop support as one coherently named project: a DKMS kernel module exposing the
RGB keyboard backlight, the backlight Fn keys and the firmware performance profiles through
standard kernel interfaces; a Python command line tool and tray applet on top of those
interfaces; a GNOME Shell extension that adds the firmware "quiet" profile to the power mode
menu; system integration (device rule, service unit, tmpfiles); and Debian packaging with
debhelper producing three packages. The design decisions come from the review of the previous
implementation and are recorded in [research.md](research.md).

## Technical Context

**Language/Version**: C (Linux kernel module, kernel ≥ 6.14, developed on 7.0); Python ≥ 3.11
(standard library; PyGObject for the tray); JavaScript ES modules for GJS (GNOME Shell 50)
**Primary Dependencies**: kernel subsystems `wmi`, `leds` (multicolor class), `input`
(sparse-keymap), `platform_profile`, ACPI; GTK 3 + AyatanaAppIndicator3 + libnotify via GObject
introspection; GNOME Shell quick-settings API; power-profiles-daemon (optional at run time)
**Storage**: one text file, `/var/lib/clevo-control/backlight-color` (six hex digits)
**Testing**: `unittest` against a fake sysfs tree for the Python package and CLI; `make W=1` and
`checkpatch --strict` for the module; validators (`udevadm verify`, `systemd-analyze verify`,
`desktop-file-validate`, `appstreamcli validate`, `node --check`); `lintian`; hardware checklist
in [quickstart.md](quickstart.md)
**Target Platform**: x86_64 Linux on Clevo laptops; reference Ubuntu 26.04 / GNOME 50
**Project Type**: kernel module + CLI/desktop tools + shell extension + distribution packaging
**Performance Goals**: CLI start under 100 ms; no blocking I/O in the shell process; backlight
change visible within one firmware call
**Constraints**: standard kernel interfaces only; documented firmware commands only; no module
load/unload or foreign service restarts from packaging; group-writable state treated as untrusted
**Scale/Scope**: about 800 lines of C, 700 of Python, 400 of JavaScript, plus packaging and docs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Standard Interfaces Only | Module exposes LED class, input and platform profile only; tools use sysfs of those classes | PASS |
| II. Documented Firmware Commands Only | Command set limited to those in tuxedo-drivers v4.24.0; replies checked; profile support gated (research R2) | PASS |
| III. One Name, One Version | Naming table in spec; `VERSION` file; no version in module, man sources or metadata sources | PASS |
| IV. Verified Before Claimed | `make check` aggregates every automated check; hardware checklist; untested paths listed in README | PASS |
| V. Failure Is Explicit | Single error type in the Python package; bounded validated read of state; no tracebacks in CLI or tray | PASS |
| VI. Packaging By The Book | `debian/` with debhelper, dh-dkms, dh-python; no hand-written maintainer scripts; state in `/var/lib` | PASS |
| VII. Small And Reversible | Three packages; extension degrades to its own toggle and undoes everything on disable | PASS |

Post-design re-check (after Phase 1): no violations; the Complexity Tracking table stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-clevo-control/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md              # clevoctl commands, output and exit codes
│   ├── kernel-interfaces.md # LED, input keys, platform profile exposed by the module
│   └── firmware.md         # firmware commands used and their source
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
clevo-control/
├── VERSION                     # single source of the version
├── Makefile                    # module, test, lint, check, install/uninstall (DESTDIR), deb
├── README.md  LICENSE  CHANGELOG.md  CONTRIBUTING.md
├── module/
│   ├── clevo-control.c         # the kernel module
│   ├── Kbuild
│   └── dkms.conf
├── clevo_control/              # Python package (installed to /usr/share/clevo-control/)
│   ├── __init__.py
│   ├── errors.py               # ClevoError
│   ├── colors.py               # colour and brightness parsing
│   ├── backlight.py            # LED class device access
│   ├── profile.py              # platform profile class device access
│   ├── state.py                # saved colour, atomic and bounded
│   ├── cli.py                  # clevoctl
│   └── tray.py                 # clevo-control-tray
├── bin/
│   ├── clevoctl
│   └── clevo-control-tray
├── extension/
│   ├── extension.js
│   └── metadata.json.in
├── data/
│   ├── 70-clevo-control.rules
│   ├── clevo-control-backlight.service
│   ├── clevo-control.tmpfiles
│   ├── io.github.pavelnikanovich.ClevoControl.desktop
│   ├── io.github.pavelnikanovich.ClevoControl-autostart.desktop
│   └── io.github.pavelnikanovich.ClevoControl.metainfo.xml
├── man/
│   ├── clevoctl.1.in
│   ├── clevo-control-tray.1.in
│   └── clevo-control.7.in
├── tests/
│   ├── fakesysfs.py            # builds the fake LED / profile tree
│   ├── test_colors.py
│   ├── test_backlight.py
│   ├── test_profile.py
│   ├── test_state.py
│   └── test_cli.py
├── docs/
│   └── hardware.md             # hand-written hardware facts and test matrix
├── debian/
│   ├── control  rules  changelog  copyright  source/format
│   ├── clevo-control-dkms.dkms  clevo-control-dkms.install
│   ├── clevo-control.install  clevo-control.manpages  clevo-control.udev
│   ├── clevo-control.service  clevo-control.tmpfiles
│   └── gnome-shell-extension-clevo-control.install
├── .github/workflows/ci.yml
└── tools/
    ├── check-version.sh        # VERSION vs debian/changelog
    └── hw-check.sh             # read-only hardware checklist helper
```

**Structure Decision**: one repository with one directory per deliverable (`module/`,
`clevo_control/`, `extension/`, `data/`, `man/`, `debian/`). The top-level `Makefile` is the single
entry point; `debian/rules` calls `make install DESTDIR=debian/tmp` and the `*.install` files split
the result into the three packages.

## Work Packages

Detailed tasks are in [tasks.md](tasks.md). Order and dependencies:

1. **Setup** — repository skeleton, `VERSION`, `Makefile`, licence.
2. **Module** — firmware transport, core, LED, hotkeys, profiles (User Stories 1, 2, 3, 7).
3. **Python package and CLI** — test-first against fake sysfs (User Stories 1, 3).
4. **System integration** — rule, unit, tmpfiles (User Story 1 persistence).
5. **Tray** (User Story 5).
6. **Extension** (User Story 4).
7. **Packaging** (User Story 6) — needs debhelper, dh-dkms, dh-python installed.
8. **Documentation, CI, lint** (User Story 8).
9. **Migration and hardware verification** on the reference laptop, independent review.

## Complexity Tracking

No constitution violations to justify.
