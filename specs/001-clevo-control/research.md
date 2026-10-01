# Research: clevo-control 1.0

Decisions taken before design. Sources: the review of the previous implementation, the kernel
sources (v6.13, v6.14, v6.19, v7.0), tuxedo-drivers v4.24.0, power-profiles-daemon 0.30, the GNOME
Shell 50 sources shipped in `libshell-18.so`, and measurements on the reference laptop.

## R1. Ownership and firmware transport in the module

**Decision**: one core object, `struct clevo_laptop`, owned by exactly one driver:

- the platform driver on the ACPI device `CLV0001` when that device exists — firmware calls go
  through its `_DSM`, hotkeys arrive as ACPI notifications;
- otherwise the WMI driver on the method GUID — firmware calls go through WMI, hotkeys arrive on
  the WMI event GUID.

Both back-ends fill a two-function transport (`call`, `read`) and feed one
`clevo_laptop_event()`. When `CLV0001` is present the WMI method driver declines to bind.

**Rationale**: tuxedo-drivers gives the ACPI interface priority on machines that have it. A single
owner removes the global pointer shared between unrelated drivers and the input device created at
module load.

**Alternatives considered**: keep WMI for calls and ACPI only for events (previous
implementation; two half-owners and a global); a module-created platform device with interfaces
registering to it (the tuxedo layout; more indirection than this size of driver needs).

## R2. Which firmware replies can be trusted

**Decision**: every call returns the firmware's integer result to the caller. Binding requires
`GET_BIOS_FEATURES_1` (0x52) to answer something other than `0xffffffff`, as in tuxedo-drivers.
Whether a `SET` command reports rejection in its result is not documented; until it is established
from the ACPI tables of the reference machine (task in tasks.md), performance profiles are
registered only on boards in a DMI allow-list of machines where the effect was measured, or with
the `force_profiles` module parameter.

**Rationale**: the previous implementation called the profile command once and treated a
successful method evaluation as support, which proves nothing. A measured allow-list is honest;
an override keeps other owners able to try.

**Alternatives considered**: sending an invalid sub-command to see the error value (an
undocumented command, forbidden by the constitution); registering unconditionally (the defect
being fixed).

## R3. Scope on machines without a supported RGB keyboard

**Decision**: the module binds and offers the performance profiles (subject to R2). It does not
enable firmware events, creates no input device and no LED. White-only and per-key keyboards are
not driven.

**Rationale**: on the reference machine the touchpad, airplane-mode, volume and webcam keys work
without firmware events being enabled; events are only needed for the backlight keys of an
OS-controlled RGB keyboard. Enabling them where nothing consumes the backlight keys could take
those keys away from the firmware. Untestable code for other keyboard types is not shipped.

**Alternatives considered**: port tuxedo's white-backlight LED (cannot be verified on available
hardware).

## R4. Colour-cycle hotkey

**Decision**: handled in the module. Under the LED core's `led_access` mutex it writes the three
intensities and calls `led_set_brightness()` with the current brightness, exactly what the
`multi_intensity` attribute does.

**Rationale**: the LED core then enforces suspend state and reports the new colour through sysfs.
Emitting a key instead would need a userspace daemon for one key.

## R5. Initial state and module parameters

**Decision**: at bind the module applies white at half brightness; systemd-backlight restores the
brightness and the project's unit restores the colour. Parameters: `force_rgb` and
`force_profiles` only. The 1-zone red/blue calibration from tuxedo-drivers is always applied.

**Rationale**: colour and brightness defaults are policy that userspace already handles.

## R6. Kernel API level

**Decision**: minimum kernel 6.14 (`devm_platform_profile_register`, `struct
platform_profile_ops`). The WMI calls use `wmidev_evaluate_method()` and the `.notify` callback,
which exist from 6.14 through 7.0; their replacements (`wmidev_invoke_method`, `.notify_new`) do
not exist before 7.0. `dkms.conf` sets `BUILD_EXCLUSIVE_KERNEL_MIN="6.14"` and
`BUILD_EXCLUSIVE_ARCH="x86_64"`. No `MODULE_VERSION` (the version has one source).

## R7. Saved colour

**Decision**: `/var/lib/clevo-control/backlight-color`, six lowercase hex digits and a newline.
The directory is created by tmpfiles.d as `root:plugdev 2775`. Writes go to a temporary file in the
same directory followed by `rename`. Reads open with `O_NOFOLLOW`, read at most 16 bytes and
validate against `[0-9a-f]{6}`; anything else counts as "nothing saved".

**Rationale**: the file is written by group members and read by root. A bounded, validated read
cannot be turned into resource exhaustion, and a failed validation never echoes file content.
Atomic rename replaces a planted symlink instead of following it.

**Alternatives considered**: JSON in `/etc` (previous implementation: program state in the
configuration directory, unbounded parse as root, non-atomic).

## R8. Who may change colour and profile

**Decision**: a device rule gives group `plugdev` write access to `multi_intensity` and
`brightness` of the LED and to `profile` of the `clevo` platform-profile device.

**Rationale**: `chgrp`/`chmod` from `RUN` is the established idiom for sysfs attributes (GROUP and
MODE apply to device nodes only). Desktop users are members of `plugdev` on Debian and Ubuntu.
logind and UPower already offer the brightness to the active session, but the command line tool
must also work over SSH and from scripts, so it writes sysfs like everything else.

## R9. Restore and save of the colour

**Decision**: the device rule tags the LED for systemd, gives it the alias
`/sys/subsystem/leds/devices/rgb:kbd_backlight` and wants `clevo-control-backlight.service`. The
unit is bound to that device (`BindsTo`, `After`), runs `clevoctl backlight restore` on start and
`clevoctl backlight save` on stop.

**Rationale**: no interpreter is started from udev; the unit follows the device through module
reloads and saves at shutdown without a condition evaluated once at boot. This mirrors
`systemd-backlight@.service`.

## R10. Python layout

**Decision**: package `clevo_control` installed as a private module under
`/usr/share/clevo-control/`; `bin/clevoctl` and `bin/clevo-control-tray` add that directory to
`sys.path`. Colour and brightness parsing, LED access, profile access and state are separate
modules behind one exception type, `ClevoError`.

**Rationale**: Debian Python policy places application-private modules outside the public
`dist-packages`; dh_python3 handles `/usr/share/<package>`.

## R11. Tray

**Decision**: `Gtk.Application` with application ID `io.github.pavelnikanovich.ClevoControl`
(single instance through D-Bus; a second launch activates the first and opens the colour
chooser), GTK 3 with AyatanaAppIndicator3. Brightness is a small window with a `Gtk.Scale` (0–100)
and a percentage label, refreshed from sysfs while open. The applet polls for the LED while it is
absent. The tools package depends on the GObject introspection data it imports.

**Rationale**: AyatanaAppIndicator3 is what the Ubuntu AppIndicators extension and other desktops
support. Its GLib successor (`AyatanaAppIndicatorGlib`) is packaged on the target release but
needs a different menu model (`Gio.Menu` instead of `Gtk.Menu`); moving to it is left for later,
at the cost of a deprecation message in the log at start-up.

## R12. Extension

**Decision**: keep the approach verified on GNOME Shell 50 — override `_syncProfiles` and `_sync`
of the shell's `PowerProfilesToggle` through `InjectionManager` to append a Quiet item — with these
changes: every handler connected to a shell-owned item is recorded and disconnected on disable;
the item is destroyed explicitly; a fallback `QuickToggle` is shown when the menu cannot be
extended or the daemon has no owner on the bus, switching live on `notify::g-name-owner`; the
profile path and file monitor are re-resolved when the device disappears; all file access is
asynchronous; leaving Quiet always writes the target firmware profile directly.

**Rationale**: power-profiles-daemon 0.30 maps the platform profile `quiet` to Power Saver, does
not rewrite the firmware profile for the mode it already considers active, and notices an external
change after about two seconds (measured).

## R13. Packaging

**Decision**: source format `3.0 (quilt)`, version `1.0.0-1`, `debhelper-compat (= 13)`,
`dh-sequence-dkms`, `dh-sequence-python3`. Binary packages: `clevo-control-dkms`,
`clevo-control`, `gnome-shell-extension-clevo-control`. `debian/rules` runs
`make install DESTDIR=debian/tmp`. No maintainer scripts are written by hand: the unit is installed
by `dh_installsystemd`, tmpfiles by `dh_installtmpfiles`, the rule by `dh_installudev`, DKMS by
`dh_dkms`. `clevo-control-dkms` conflicts with `tuxedo-drivers` and `tuxedo-keyboard-dkms`.

**Rationale**: these are the findings of the packaging review; generated scripts preserve the
administrator's choices and handle failed upgrades.

## R14. Version and generated files

**Decision**: `VERSION` holds the upstream version. `man/*.in` and `extension/metadata.json.in`
carry `@VERSION@`, substituted by `make`. `tools/check-version.sh` fails the build when the
upstream part of `debian/changelog` differs from `VERSION`. The README never names a versioned
file.

## R15. Attribution

**Decision**: protocol constants, the keyboard-type detection, the 1-zone calibration factors,
the hotkey event codes and the performance-profile numbering are credited to tuxedo-drivers
v4.24.0 (GPL-2.0-or-later, `clevo_interfaces.h`, `clevo_leds.h`, `clevo_keyboard.h`, `clevo_wmi.c`,
`clevo_acpi.c`, `tuxedo_io/tuxedo_io.c`) in the module header, the README and `debian/copyright`,
with a TUXEDO copyright line.

## Open item (resolved 2026-10-01)

- **O1**: the DSDT of the reference machine shows that `SET` commands return the command number
  regardless of the outcome, so R2 stands: the reply cannot establish profile support. The firmware
  gates the profile sub-command on bit `0x04` of the feature word returned by command `0x60`.
  That command is not documented by tuxedo-drivers, so by constitution principle II the module
  does not use it and keeps the board allow-list. Using it would need a constitution amendment.
