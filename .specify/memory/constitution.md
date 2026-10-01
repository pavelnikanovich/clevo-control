# clevo-control Constitution

## Core Principles

### I. Standard Interfaces Only

The kernel module MUST expose hardware through existing kernel subsystems (LED class, input,
platform profile) and MUST NOT add private sysfs files, ioctls or device nodes. Userspace MUST
talk to those standard interfaces, never to the firmware directly.

Rationale: the desktop (UPower, power-profiles-daemon, systemd-backlight) then works without
knowing about this project, and the driver stays reviewable against documented kernel ABI.

### II. Documented Firmware Commands Only

The driver MUST use only firmware commands whose meaning is documented by an existing GPL
implementation (tuxedo-drivers). Direct embedded-controller access (port I/O, EC RAM writes) and
commands of unknown meaning are forbidden. Fan control is out of scope.

Every firmware reply that carries a status MUST be checked; a feature whose support cannot be
established for the running machine MUST NOT be registered as working.

Rationale: a wrong EC write can damage hardware, and a silently ignored command makes the system
believe it controls something it does not.

### III. One Name, One Version

Every artifact (repository, packages, kernel module, commands, Python package, extension UUID,
state files, units) MUST derive its name from the single stem `clevo-control` according to the
naming table in the specification. The version MUST have exactly one source of truth (`VERSION`);
every other occurrence is generated or checked at build time.

Rationale: the previous project carried four unrelated names and eight copies of the version.

### IV. Verified Before Claimed

Automated checks MUST pass before a work package is considered done: kernel build with `W=1` and
`checkpatch --strict` clean, Python tests with `ruff` and `mypy` clean, extension syntax check,
unit/udev/desktop/metainfo validators, package build with `lintian` clean.

Behaviour that depends on hardware MUST be confirmed on real hardware before it is described as
working. Code paths that could not be exercised on available hardware MUST be listed as untested
in the README.

### V. Failure Is Explicit

Userspace tools MUST report every I/O or parse failure as a clear one-line error with a non-zero
exit status; no tracebacks, no silent fallbacks. Code that runs as root (units, udev helpers) MUST
treat files writable by unprivileged users as untrusted input: bounded reads, strict validation,
no following of user-controlled paths.

### VI. Packaging By The Book

Distribution packages MUST be built from a `debian/` directory with debhelper; maintainer scripts
are generated, not hand-written. Installing or upgrading the package MUST NOT load or unload kernel
modules, restart services owned by other packages, or override an administrator's enable/disable
choices. Program state lives under `/var/lib`, not `/etc`.

### VII. Small And Reversible

Each component has one responsibility and can be removed without breaking the others: the module
works without the tools, the tools without the tray, the desktop without the extension. Anything
that relies on private internals of another program (the GNOME Shell extension) MUST detect
incompatibility and degrade to a self-contained fallback, and MUST undo all of its changes when
disabled.

## Scope And Constraints

- Target: Clevo laptops exposing the Clevo WMI method interface (and optionally the `CLV0001`
  ACPI device); reference hardware is the NH5x_NH7xHP (1-zone RGB keyboard).
- Minimum kernel: 6.14 (platform profile class API). The DKMS configuration MUST refuse older
  kernels rather than fail to build.
- Licence: GPL-2.0-or-later. Firmware protocol constants are attributed to tuxedo-drivers with the
  version consulted. No code is taken from projects under incompatible licences.
- Languages: C (kernel style), Python 3 (standard library plus PyGObject for the tray),
  JavaScript (GJS, GNOME Shell extension API). Documentation and comments are in English.
- Private material (reverse-engineering transcripts, EC experiments, personal paths) MUST NOT
  enter the repository.

## Development Workflow

- Work is specified, planned and broken into tasks with Spec Kit before implementation; the
  specification artifacts are kept in the repository.
- One commit per completed work package or logically separate change, with a message that says
  what changed and why. History is not rewritten after publication.
- Userspace logic is developed test-first against a fake sysfs tree; kernel behaviour is verified
  with the hardware checklist in the specification.
- Publication (pushing to a public remote, release assets, extension store submission) happens
  only on the maintainer's explicit instruction.

## Governance

This constitution takes precedence over other project documents. A change to it is made by editing
this file in a dedicated commit that states the reason; principle removals or redefinitions are a
major version bump, added or materially expanded principles a minor bump, clarifications a patch
bump. Specifications, plans and reviews MUST check compliance with the principles above, and any
deliberate deviation MUST be recorded with its justification in the plan of the feature concerned.

**Version**: 1.0.0 | **Ratified**: 2026-10-01 | **Last Amended**: 2026-10-01
