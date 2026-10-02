# Contributing

Bug reports, hardware reports and patches are welcome. For a new laptop model see
"Reporting another model" in [docs/hardware.md](docs/hardware.md).

## Layout

| Directory | Content |
|-----------|---------|
| `module/` | the kernel module and its DKMS configuration |
| `clevo_control/`, `bin/` | the Python package behind `clevoctl` and `clevo-control-tray` |
| `extension/` | the GNOME Shell extension (`controller.js` has no shell imports; `extension.js` is tested against stand-ins for the shell modules in `tests/extension/shellstub`) |
| `data/` | device rule, service unit, tmpfiles, desktop entries, AppStream metadata |
| `man/` | manual pages (`@VERSION@` is filled in by `make`) |
| `tests/` | Python tests against a fake sysfs tree, gjs tests of the extension logic |
| `debian/` | Debian packaging |
| `specs/`, `.specify/` | specification, plan and task list (Spec Kit), and the project constitution |

## Building and checking

```bash
make module     # build the kernel module with W=1 (needs the headers of the running kernel)
make test       # Python tests, and the extension tests when gjs is installed
make lint       # ruff, mypy, checkpatch, syntax checks, validators, version check
make check      # all of the above
make deb        # Debian packages (debhelper, dh-dkms, dh-python)
```

`make lint` skips checks whose tool is not installed; `STRICT=1 make lint` fails instead.

After `make deb`, check the packages with `lintian --profile debian -EvIL +pedantic ../*.changes`:
it must report nothing. (With the Ubuntu profile lintian objects to the `unstable` distribution in
`debian/changelog`; the ITP-bug warning for the first changelog entry is overridden, because these
packages are built from this repository and not uploaded to the Debian archive.)

## Releasing

1. Set `VERSION`, add the section to `CHANGELOG.md` and the entry to `debian/changelog`; `make check`.
2. Tag the commit `v<version>` and push the branch and the tag.
3. `make deb` and attach the three packages to the GitHub release.
4. For the PPA, build the source package and upload it:

   ```bash
   tools/ppa-source.sh -k <your OpenPGP key>     # -s SERIES, -r REVISION; default resolute, 1
   dput ppa:<launchpad user>/clevo-control build/ppa/clevo-control_*_source.changes
   ```

   The upstream tarball is made from the tag (without `debian/`) and is the same file every time;
   the packaging is `debian/` of the current commit. The upload is versioned
   `<version>-<n>~<series><revision>`, so it never shadows a package from the distribution. A
   change to the packaging alone needs a new `debian/changelog` entry (`-2`, …) and no new tag.

   Launchpad builds from the declared build dependencies with no network access. To try that
   first, unpack the `.dsc` in a clean `ubuntu:<release>` container, install the build
   dependencies with `mk-build-deps` and run `dpkg-buildpackage -b` under `unshare -n`.

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
