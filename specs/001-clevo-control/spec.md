# Feature Specification: clevo-control 1.0

**Feature Branch**: `main` (initial build of the project)
**Created**: 2026-10-01
**Status**: Draft
**Input**: User description: "Create a clean project in `_projects` with its own repository, rethink
every name, and rebuild from scratch a project that fixes the shortcomings found in the review of
the previous implementation: keyboard backlight, Fn keys and firmware performance profiles for
Clevo laptops on Linux, with desktop integration, proper Debian packaging and documentation good
enough for open-source publication. The tray gets a brightness control with a slider and a
percentage readout."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keyboard backlight colour and brightness (Priority: P1)

The owner of a Clevo laptop with an RGB keyboard chooses the backlight colour and brightness from
a terminal, and the laptop keeps that choice across reboots and suspend.

**Why this priority**: it is the original reason for the project and the smallest slice that is
useful on its own.

**Independent Test**: install the module package and the tools package, run the colour and
brightness commands, reboot, and observe the keyboard.

**Acceptance Scenarios**:

1. **Given** the module is loaded on an RGB keyboard, **When** the user sets a named colour or a
   hex colour, **Then** the keyboard shows that colour and the status command reports it.
2. **Given** a colour and brightness were set, **When** the machine is rebooted, **Then** the same
   colour and brightness are shown without user action.
3. **Given** the backlight is on, **When** the machine suspends and resumes, **Then** the backlight
   is off during suspend and returns with the same colour and brightness.
4. **Given** the user is a member of the documented group, **When** they change colour or
   brightness, **Then** no administrator rights are requested.
5. **Given** an invalid colour or brightness, **When** the command runs, **Then** it prints a
   one-line error naming the accepted forms and exits with a non-zero status.

---

### User Story 2 - Backlight Fn keys (Priority: P1)

The user presses the keyboard-backlight Fn keys and the desktop reacts: brightness up and down,
backlight on/off, next colour.

**Why this priority**: without it the hardware keys printed on the keyboard do nothing.

**Independent Test**: with only the module package installed and a standard desktop, press each
key and observe brightness, on-screen indicator and colour.

**Acceptance Scenarios**:

1. **Given** a desktop session started after the module was loaded, **When** brightness up or down
   is pressed, **Then** the brightness changes by one desktop step and an indicator is shown.
2. **Given** the backlight is on, **When** the on/off key is pressed, **Then** it turns off, and a
   second press restores it.
3. **Given** any colour, **When** the next-colour key is pressed, **Then** the keyboard moves to the
   next colour of a fixed documented list, and the new colour is what every status view reports.
4. **Given** the machine is suspended or suspending, **When** a key event arrives, **Then** the
   backlight is not switched on.
5. **Given** the firmware also reports touchpad and airplane-mode keys, **When** they are pressed,
   **Then** they keep working exactly once per press.

---

### User Story 3 - Performance profiles follow the desktop power mode (Priority: P2)

The user switches the desktop power mode (Power Saver, Balanced, Performance) and the laptop
firmware changes its power limits accordingly.

**Why this priority**: it gives real control over heat, noise and battery life, but the laptop is
usable without it.

**Independent Test**: switch the desktop power mode and read the CPU power limits after each
switch.

**Acceptance Scenarios**:

1. **Given** the power mode service started after the module, **When** each of the three desktop
   modes is selected, **Then** the firmware profile and the CPU power limits change to the values
   documented for that mode.
2. **Given** a profile was chosen, **When** the machine suspends and resumes, **Then** the same
   profile is active.
3. **Given** firmware that does not accept the profile command, **When** the module loads,
   **Then** no profile control is offered and the desktop does not claim to control the firmware.
4. **Given** the tools package, **When** the user asks for the current or available profiles or
   sets one from the terminal, **Then** the command reports or applies it without administrator
   rights for group members.

---

### User Story 4 - Quiet mode in the desktop power menu (Priority: P2)

The user picks a fourth entry, Quiet, in the GNOME power mode quick-settings menu to get the
lowest-power firmware profile, and leaves it by picking any other entry.

**Why this priority**: the quiet profile is the most noticeable one, and the stock desktop cannot
select it.

**Independent Test**: enable the extension, select each of the four entries in turn, including
quick successive changes, and read the firmware profile after each.

**Acceptance Scenarios**:

1. **Given** the extension is enabled, **When** the power mode menu is opened, **Then** it lists
   Performance, Balanced, Power Saver and Quiet, with a check mark on the entry that matches the
   real firmware profile.
2. **Given** any mode, **When** Quiet is chosen, **Then** the firmware is in the quiet profile and
   the button subtitle says Quiet.
3. **Given** Quiet is active, **When** another entry is chosen, even within two seconds of entering
   Quiet, **Then** the firmware profile of that entry is active after a single click.
4. **Given** the power mode service is not running, or a shell version whose menu cannot be
   extended, **When** the extension is enabled, **Then** a separate Quiet toggle is shown instead
   and works.
5. **Given** the extension is disabled, **When** the menu is opened, **Then** it is exactly the
   stock menu and nothing of the extension keeps reacting.
6. **Given** the module is reloaded while the session runs, **When** the profile changes
   afterwards, **Then** the menu still reflects it.

---

### User Story 5 - Tray applet (Priority: P3)

On desktops with a system tray the user controls the backlight from an indicator: a colour
chooser, preset colours, a brightness window with a slider and a percentage readout, and the
performance profile.

**Why this priority**: a convenience over the terminal tool, and the only graphical control on
desktops other than GNOME.

**Independent Test**: start the applet, use every menu entry, start it a second time, start it
without the module loaded.

**Acceptance Scenarios**:

1. **Given** the applet runs, **When** the user opens Brightness, **Then** a window shows a slider
   and the current value as a percentage; moving the slider changes the keyboard brightness
   immediately and the readout follows.
2. **Given** the brightness is changed elsewhere (Fn keys, terminal), **When** the brightness
   window is open, **Then** the slider and readout follow the real value.
3. **Given** the applet runs, **When** it is launched again from the application menu, **Then** no
   second indicator appears and the first instance presents its colour chooser.
4. **Given** the backlight device is absent at login, **When** it appears later, **Then** the
   applet becomes usable without being restarted.
5. **Given** a failure to apply a setting, **When** it happens, **Then** the user gets a
   notification with the reason, including the missing group membership when that is the cause.

---

### User Story 6 - Install, upgrade and remove like any other package (Priority: P2)

The user installs the packages with the system package manager, later upgrades them, and can
remove them without leftovers.

**Why this priority**: it decides whether other people can use the project at all and whether a
distribution would accept it.

**Independent Test**: on a clean machine build the packages, install, upgrade to a rebuilt version,
remove and purge, checking the system state after each step.

**Acceptance Scenarios**:

1. **Given** a supported kernel, **When** the packages are installed, **Then** the module is built
   for the installed kernels and is used from the next boot, with no service restarted and no
   module loaded or unloaded by the installation.
2. **Given** a kernel older than the minimum, **When** the module package is installed, **Then**
   installation succeeds and the module is skipped for that kernel with a clear message.
3. **Given** an installed version, **When** a newer one is installed, **Then** the running session
   keeps working and the administrator's enable/disable choices for services are preserved.
4. **Given** the packages are purged, **When** the file system is inspected, **Then** no file of the
   project remains.
5. **Given** the built packages, **When** the distribution's package checker runs with pedantic
   checks, **Then** it reports no errors and no warnings.

---

### User Story 7 - Performance profiles on Clevo laptops without an RGB keyboard (Priority: P3)

The owner of a Clevo laptop with a white or no keyboard backlight still gets the performance
profiles, and the firmware keeps handling its keys as before.

**Why this priority**: it widens the audience, but cannot be verified on the reference hardware.

**Independent Test**: by code inspection against the reference implementation and, when a tester
with such hardware is available, by the hardware checklist.

**Acceptance Scenarios**:

1. **Given** firmware that answers the interface check but reports no RGB keyboard, **When** the
   module loads, **Then** performance profiles are available (where supported) and no backlight
   or hotkey device is created.
2. **Given** such a machine, **When** the module loads, **Then** it does not ask the firmware to
   hand its hotkeys to the operating system.

---

### User Story 8 - Contributor can build, check and understand the project (Priority: P2)

A developer clones the repository, builds and checks everything with documented commands, and
finds out from the documentation what each part does and what hardware it was tested on.

**Why this priority**: required for publication and review.

**Independent Test**: follow the README and CONTRIBUTING on a machine that never saw the project.

**Acceptance Scenarios**:

1. **Given** a fresh clone, **When** the documented build, test and lint commands are run, **Then**
   they pass without undocumented prerequisites.
2. **Given** the documentation, **When** each command, path and option in it is tried, **Then** it
   exists and behaves as described.
3. **Given** the repository, **When** it is searched, **Then** it contains no private transcripts,
   no direct embedded-controller tools and no personal paths.
4. **Given** any artifact name, **When** compared with the naming table below, **Then** it matches.

### Edge Cases

- The saved-colour state file is missing, empty, oversized, malformed, or not writable.
- The user is not a member of the group that may change the backlight and profile.
- Two programs change the colour at the same moment.
- The LED or profile device disappears and reappears (module reload) while tools, tray or
  extension are running.
- The firmware accepts a command at the transport level but rejects it.
- A machine exposes only the WMI interface, only the ACPI device, or both.
- Another driver for the same hardware (tuxedo-drivers) is installed.
- Secure Boot is enabled and the module is not signed with an enrolled key.
- The power mode service notices an external profile change only after about two seconds.
- No power mode service is installed at all.
- A hotkey arrives during suspend.
- The desktop has no tray support.

## Requirements *(mandatory)*

### Functional Requirements

**Kernel module**

- **FR-001**: The module MUST expose an RGB keyboard backlight as a standard multicolour keyboard
  backlight device with brightness and per-channel intensity, for 1-zone keyboards, and for 3-zone
  keyboards with all zones showing the same colour.
- **FR-002**: The module MUST report the keyboard-backlight Fn keys (brightness down/up, on/off)
  as standard key events, and MUST handle the next-colour key itself through the same path the
  rest of the system uses to change the colour, so that suspend state and status views stay
  consistent.
- **FR-003**: Where it takes over the firmware hotkeys, the module MUST forward the touchpad and
  airplane-mode events as standard key events exactly once per press, whichever firmware
  interface delivers them.
- **FR-004**: The module MUST expose the firmware performance profiles (quiet, power saving,
  entertainment, performance) as a standard platform profile, only when the firmware is known to
  accept the profile command on the running machine.
- **FR-005**: Profiles MUST NOT depend on the presence of an RGB keyboard. On machines without a
  supported RGB keyboard the module MUST leave hotkey handling to the firmware.
- **FR-006**: The module MUST re-apply colour, brightness and profile after resume and MUST keep
  the backlight off while suspended.
- **FR-007**: The module MUST refuse to bind to firmware that fails the interface sanity check and
  MUST send no state-changing command before that check.
- **FR-008**: The module MUST check the status of firmware replies and report rejected commands as
  errors to the caller.
- **FR-009**: The module MUST be configurable only by parameters that override detection
  (keyboard type, profile support); initial colour and brightness are not module parameters.
- **FR-010**: The module's build configuration MUST declare the minimum supported kernel and
  architecture so that unsupported kernels are skipped instead of failing.

**Command line tool**

- **FR-011**: A single command MUST provide: overall status; backlight colour (hex or named),
  brightness (absolute or percent), on, off, save, restore; profile list, get, set.
- **FR-012**: Colour and brightness arguments MUST be parsed strictly, and every failure MUST
  produce a one-line message and a non-zero exit status.
- **FR-013**: The chosen colour MUST be remembered whenever it is set through the tool or the
  tray, and the colour in use at shutdown MUST be remembered as well; it is restored when the
  backlight device appears.
- **FR-014**: The remembered state MUST be stored outside the configuration directory, be
  writable by the documented group, be written atomically, and be read with a size bound and full
  validation, since it is read by privileged code.

**Tray applet**

- **FR-015**: The applet MUST offer a colour chooser, preset colours, a brightness window with a
  slider and a percentage readout, a profile choice, and quit.
- **FR-016**: The applet MUST run as a single instance per session; a second launch activates the
  running instance.
- **FR-017**: The applet MUST keep running while the backlight device is absent and become usable
  when it appears.

**GNOME Shell extension**

- **FR-018**: The extension MUST add a Quiet entry to the shell's power mode menu and reflect the
  real firmware profile in the check mark and subtitle.
- **FR-019**: Leaving Quiet MUST take effect with one action regardless of the power mode
  service's reaction delay.
- **FR-020**: Without a running power mode service, or when the menu cannot be extended, the
  extension MUST show a self-contained Quiet toggle instead.
- **FR-021**: Disabling the extension MUST remove every item, handler and override it added,
  whether or not the power mode service is running.
- **FR-022**: The extension MUST keep working after the profile device was removed and re-created.
- **FR-023**: File access from the extension MUST NOT block the shell.

**System integration and packaging**

- **FR-024**: Members of one documented group MUST be able to change colour, brightness and
  profile without administrator rights.
- **FR-025**: Restoring and saving the colour MUST be done by a service unit bound to the
  backlight device, not by programs started from device rules.
- **FR-026**: The project MUST build three packages: the module (DKMS), the tools with the tray,
  and the shell extension, each installable without the others, with dependencies that make every
  installed program start.
- **FR-027**: Package installation, upgrade and removal MUST NOT load or unload the module,
  restart other packages' services, or change service enablement set by the administrator.
- **FR-028**: The module package MUST declare a conflict with other drivers for the same hardware.
- **FR-029**: A plain install target with a staging directory MUST exist for non-Debian systems.

**Project**

- **FR-030**: Every artifact name MUST follow the naming table below.
- **FR-031**: The version MUST be defined in one place; all other occurrences are generated or
  verified at build time.
- **FR-032**: The repository MUST provide one command each to build the module, run the tests, run
  all linters, and build the packages, and a continuous-integration configuration that runs them.
- **FR-033**: The documentation MUST state supported and tested hardware, untested code paths,
  minimum kernel, Secure Boot handling, group membership, the conflict with tuxedo-drivers,
  installation on Debian-based and other systems, usage, the Fn keys, the profile table with the
  measured limits of the reference machine, and troubleshooting.
- **FR-034**: Attribution MUST name the tuxedo-drivers version from which protocol constants were
  taken; the licence is GPL-2.0-or-later.

### Naming Table

| Artifact | Name |
|----------|------|
| Repository, project directory | `clevo-control` |
| Debian source package | `clevo-control` |
| Module package | `clevo-control-dkms` |
| Tools package (command, tray, units, rules) | `clevo-control` |
| Extension package | `gnome-shell-extension-clevo-control` |
| Kernel module | `clevo-control` (`clevo_control`) |
| Command | `clevoctl` |
| Tray applet | `clevo-control-tray` |
| Application ID | `io.github.pavelnikanovich.ClevoControl` |
| Python package | `clevo_control` |
| Extension UUID | `clevo-control@pavelnikanovich.github.io` |
| Saved colour | `/var/lib/clevo-control/backlight-color` |
| Device rules | `70-clevo-control.rules` |
| Service unit | `clevo-control-backlight.service` |
| Keyboard backlight device | `rgb:kbd_backlight` (kernel standard) |
| Platform profile handler | `clevo` |

### Key Entities

- **Backlight state**: colour (three 8-bit channels) and brightness (0–255); brightness is
  remembered by the system's backlight service, colour by this project.
- **Firmware profile**: one of quiet, power saving, entertainment, performance; mapped to the
  platform profiles quiet, low-power, balanced, performance; write-only in the firmware.
- **Hotkey event**: a firmware event code delivered through WMI or the ACPI device, mapped to a
  key or handled in the module.
- **Saved colour**: a single validated colour value on disk, group-writable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the reference laptop every item of the hardware checklist passes: colours match
  their names, brightness steps, all four backlight Fn keys, touchpad and airplane-mode keys,
  reboot persistence, and suspend/resume.
- **SC-002**: Selecting each desktop power mode and Quiet yields the documented CPU power limits
  (15/30 W, 30/30 W, 45/93 W, 60/109 W on the reference laptop) within three seconds.
- **SC-003**: Entering and immediately leaving Quiet ten times in a row never leaves the firmware
  in a profile different from the one shown.
- **SC-004**: Package build passes the distribution's checker with pedantic checks enabled with
  zero errors and zero warnings; every remaining informational tag is listed with a reason.
- **SC-005**: Upgrading the packages in a running session changes no visible behaviour until the
  next boot and leaves service enablement as it was.
- **SC-006**: All automated checks (module build with extra warnings, kernel style checker, Python
  tests, type and style checks, extension syntax, unit/rule/desktop/metadata validators) pass from
  a fresh clone with one documented command each.
- **SC-007**: Every command, path and option mentioned in the documentation is verified to exist.
- **SC-008**: An independent review of the finished project finds no finding of severity "bug" and
  no unresolved finding from the review of the previous implementation.
- **SC-009**: The version appears in exactly one maintained place.

## Assumptions

- The reference and only test hardware is a Clevo NH5x_NH7xHP (1-zone RGB, WMI plus `CLV0001`);
  3-zone, white-only and WMI-only machines are implemented from the reference driver and listed as
  untested.
- The target system is Ubuntu 26.04 with kernel 7.0, GNOME Shell 50 and power-profiles-daemon
  0.30; the minimum kernel is 6.14.
- The next-colour key stays handled inside the module (accepted limitation for a possible future
  mainline submission, which is out of scope together with fan control).
- Documentation and code comments are in English; the first release is version 1.0.0.
- The previous implementation in `~/clevo_kbd_color` is a private archive: nothing is copied from
  it verbatim except hardware facts.
- Publication to a public remote, release assets and extension store submission are separate,
  explicitly triggered steps.
- Build tooling for Debian packages (debhelper, dh-dkms, dh-python) is installed by the maintainer
  before the packaging work package.
