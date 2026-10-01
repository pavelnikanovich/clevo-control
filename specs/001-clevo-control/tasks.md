---
description: "Task list for clevo-control 1.0"
---

# Tasks: clevo-control 1.0

**Input**: Design documents from `/specs/001-clevo-control/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Python logic is developed test-first (constitution, Development Workflow). Kernel
behaviour is verified with the hardware checklist in quickstart.md.

**Organization**: tasks are grouped by user story; the module tasks of US1, US2, US3 and US7 touch
the same file and are therefore sequential.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: user story from spec.md

---

## Phase 1: Setup

- [ ] T001 Create `VERSION` (1.0.0), `LICENSE` (GPL-2.0 text), directory skeleton per plan.md
- [ ] T002 Create top-level `Makefile` with targets `module`, `test`, `lint`, `check`, `install`, `uninstall`, `deb`, `clean` and version substitution for `*.in` files
- [ ] T003 [P] Create `tools/check-version.sh` comparing `VERSION` with `debian/changelog`

---

## Phase 2: Foundational (blocking prerequisites)

- [ ] T004 Module skeleton in `module/clevo-control.c`: header and attribution, constants from contracts/firmware.md, `struct clevo_laptop`, transport ops, `clevo_fw_call()` / `clevo_fw_call_buffer()` returning the firmware result (R1, R2)
- [ ] T005 ACPI back-end in `module/clevo-control.c`: platform driver on `CLV0001`, `_DSM` transport with a constant GUID, notify handler
- [ ] T006 WMI back-end in `module/clevo-control.c`: method driver that declines when `CLV0001` is present, event driver, single owner pointer for the WMI pair only
- [ ] T007 Core bind in `module/clevo-control.c`: sanity check (0x52) before any write, keyboard type detection, `force_rgb`
- [ ] T008 [P] `module/Kbuild` and `module/dkms.conf` with `BUILD_EXCLUSIVE_KERNEL_MIN="6.14"`, `BUILD_EXCLUSIVE_ARCH="x86_64"`
- [ ] T009 [P] Fake sysfs builder in `tests/fakesysfs.py` (LED and platform-profile trees)
- [ ] T010 [P] `clevo_control/__init__.py` and `clevo_control/errors.py` (`ClevoError`)

**Checkpoint**: module builds with `W=1`, `checkpatch --strict` clean.

---

## Phase 3: User Story 1 — backlight colour and brightness (P1)

- [ ] T011 [US1] Multicolour LED in `module/clevo-control.c`: registration only for RGB keyboards, colour to all zones then brightness, 1-zone calibration, `LED_CORE_SUSPENDRESUME`, initial white at half brightness
- [ ] T012 [P] [US1] Tests `tests/test_colors.py` for colour and brightness parsing (strict forms per data-model.md)
- [ ] T013 [P] [US1] `clevo_control/colors.py`
- [ ] T014 [P] [US1] Tests `tests/test_backlight.py` (channel order, range, missing device, unreadable/unwritable attributes, malformed attribute content)
- [ ] T015 [US1] `clevo_control/backlight.py`
- [ ] T016 [P] [US1] Tests `tests/test_state.py` (absent, empty, oversized, malformed, symlink, atomic write, unwritable directory)
- [ ] T017 [US1] `clevo_control/state.py`
- [ ] T018 [US1] Tests `tests/test_cli.py` for `status` and `backlight …` (output, exit codes 0/1/2, error text, env overrides)
- [ ] T019 [US1] `clevo_control/cli.py` backlight commands and `bin/clevoctl`
- [ ] T020 [P] [US1] `data/70-clevo-control.rules`: group access to `multi_intensity`, systemd tag, alias, wants (R8, R9)
- [ ] T021 [P] [US1] `data/clevo-control-backlight.service` bound to the LED device: restore on start, save on stop
- [ ] T022 [P] [US1] `data/clevo-control.tmpfiles` for `/var/lib/clevo-control`

**Checkpoint**: colour and brightness from the terminal, persisted.

---

## Phase 4: User Story 2 — backlight Fn keys (P1)

- [ ] T023 [US2] Hotkeys in `module/clevo-control.c`: devm input device with parent, sparse keymap with named event constants, events enabled only with an RGB keyboard, re-enable on resume
- [ ] T024 [US2] Colour cycle in `module/clevo-control.c` through `led_access` + `led_set_brightness()` (R4)

---

## Phase 5: User Story 3 — performance profiles (P2)

- [ ] T025 [US3] Platform profile in `module/clevo-control.c`: DMI allow-list and `force_profiles`, set `balanced` at bind, reply checked, re-apply on resume (R2)
- [ ] T026 [P] [US3] Tests `tests/test_profile.py` (handler lookup by name, choices, get, set, invalid profile, device re-created under another index)
- [ ] T027 [US3] `clevo_control/profile.py`
- [ ] T028 [US3] Extend `tests/test_cli.py` and `clevo_control/cli.py` with `profile list|get|set` and profile line in `status`
- [ ] T029 [US3] Add group access to the `clevo` platform-profile `profile` attribute in `data/70-clevo-control.rules`

---

## Phase 6: User Story 7 — machines without an RGB keyboard (P3)

- [ ] T030 [US7] In `module/clevo-control.c`: bind without LED, input device and event enabling when no supported RGB keyboard is detected; profiles still subject to T025

---

## Phase 7: User Story 4 — Quiet in the GNOME power menu (P2)

- [ ] T031 [US4] `extension/extension.js`: asynchronous profile controller with lazy handler lookup and monitor re-creation
- [ ] T032 [US4] `extension/extension.js`: power menu integration with tracked handlers, explicit item destruction, all ornaments cleared when quiet
- [ ] T033 [US4] `extension/extension.js`: fallback toggle, live switch on daemon owner change, complete `disable()`
- [ ] T034 [P] [US4] `extension/metadata.json.in` (UUID, url, version-name, shell-version)

---

## Phase 8: User Story 5 — tray applet (P3)

- [ ] T035 [US5] `clevo_control/tray.py`: `Gtk.Application`, indicator, colour chooser, presets, notifications with group hint
- [ ] T036 [US5] `clevo_control/tray.py`: brightness window with slider and percentage readout following the real value
- [ ] T037 [US5] `clevo_control/tray.py`: profile submenu; waiting for the LED device
- [ ] T038 [P] [US5] `bin/clevo-control-tray`, `data/*.desktop` (launcher and autostart)

---

## Phase 9: User Story 6 — packaging (P2)

- [ ] T039 [US6] `Makefile` `install`/`uninstall` with `DESTDIR` and `PREFIX` covering every installed file
- [ ] T040 [US6] `debian/control`, `debian/rules`, `debian/changelog`, `debian/copyright`, `debian/source/format`
- [ ] T041 [US6] `debian/*.install`, `.dkms`, `.manpages`, `.udev`, `.service`, `.tmpfiles` for the three packages
- [ ] T042 [P] [US6] `data/io.github.pavelnikanovich.ClevoControl.metainfo.xml` with modalias provides
- [ ] T043 [US6] Build packages, run `lintian` with pedantic checks, fix or document every tag

---

## Phase 10: User Story 8 — documentation and automation (P2)

- [ ] T044 [P] [US8] `man/clevoctl.1.in`, `man/clevo-control-tray.1.in`, `man/clevo-control.7.in`
- [ ] T045 [P] [US8] `README.md` per FR-033
- [ ] T046 [P] [US8] `CONTRIBUTING.md`, `CHANGELOG.md`
- [ ] T047 [P] [US8] `docs/hardware.md`: hardware facts, measured profile limits, test matrix, untested paths
- [ ] T048 [US8] `make lint` complete: ruff, mypy, checkpatch, `node --check`, udev/systemd/desktop/appstream validators, man warnings, version check
- [ ] T049 [P] [US8] `.github/workflows/ci.yml`
- [ ] T050 [P] [US8] `tools/hw-check.sh` (read-only checklist helper)

---

## Phase 11: Verification

- [ ] T051 Determine firmware reply semantics from the reference machine's ACPI tables; replace the DMI allow-list with a reply check if usable (research O1)
- [ ] T052 Migrate the reference laptop: remove the old package, install the three packages, carry over the saved colour, switch extensions
- [ ] T053 Run the hardware checklist in quickstart.md, including suspend/resume
- [ ] T054 Verify every command, path and option in README and man pages
- [ ] T055 Independent review of the finished project; resolve findings

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → user stories.
- US1 module task T011 precedes US2 (T023, T024); T025 (US3) and T030 (US7) follow because they
  edit the same file.
- Python: T009, T010 → T012–T019 → T026–T028; tray (T035–T038) needs backlight, profile, state.
- Extension (Phase 7) is independent of the Python package.
- Packaging (Phase 9) needs every installed file to exist; T043 needs debhelper, dh-dkms,
  dh-python on the build machine.
- T051–T053 need the maintainer (root access, eyes on the hardware).

## Implementation Strategy

MVP is Phases 1–4 (backlight and Fn keys on the reference machine). Each later phase adds one user
story and ends with its own check; one commit per phase.
