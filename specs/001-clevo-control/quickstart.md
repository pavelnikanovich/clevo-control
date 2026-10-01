# Quickstart: building and verifying clevo-control

## Build and check from a clone

```bash
make module     # kernel module for the running kernel
make test       # Python tests against a fake sysfs tree
make lint       # ruff, mypy, checkpatch, extension syntax, validators, version check
make check      # all of the above
make deb        # Debian packages in ../ (needs debhelper, dh-dkms, dh-python)
```

## Hardware checklist (reference laptop, after installing the packages and rebooting)

Run `tools/hw-check.sh` for the read-only parts; the rest needs eyes and fingers.

1. `sudo dmesg | grep clevo-control` shows the keyboard and profile lines and no errors.
2. `clevoctl backlight color red`, `green`, `blue`: the keyboard matches the name.
3. `clevoctl backlight brightness 100%`, `off`, `on`.
4. Fn + `/` cycles the palette; `clevoctl status` shows the new colour.
5. Fn + `-`, Fn + `+`, Fn + `*`: brightness steps and on/off with the desktop indicator.
6. Fn + F1 (touchpad), Fn + F11 (airplane mode), Fn + F10 (webcam) behave as before, once per press.
7. Power mode Performance / Balanced / Power Saver / Quiet: `tools/hw-check.sh limits` prints
   60/109 W, 45/93 W, 30/30 W, 15/30 W.
8. Quiet then immediately another mode, ten times: shown mode equals firmware profile each time.
9. Suspend and resume: backlight off while suspended, same colour, brightness and profile after.
10. Reboot: colour and brightness restored.
11. Tray: indicator present; colour chooser; brightness window slider and percentage follow Fn
    keys; second launch opens the colour chooser; profile menu.
12. Disable the extension: the stock power menu is back; enable: Quiet is back.
13. Reinstall the same packages: nothing changes in the running session.
