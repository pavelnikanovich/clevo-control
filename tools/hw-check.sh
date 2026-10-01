#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Read-only helper for the hardware checklist (specs/001-clevo-control/quickstart.md).
#   tools/hw-check.sh          overview
#   tools/hw-check.sh limits   firmware profile and CPU power limits
set -u

rapl=/sys/class/powercap/intel-rapl:0

limits() {
	profile=$(cat /sys/firmware/acpi/platform_profile 2>/dev/null || echo "not available")
	if [ -r "$rapl/constraint_0_power_limit_uw" ]; then
		pl1=$(( $(cat "$rapl/constraint_0_power_limit_uw") / 1000000 ))
		pl2=$(( $(cat "$rapl/constraint_1_power_limit_uw") / 1000000 ))
		echo "profile: $profile   PL1: ${pl1} W   PL2: ${pl2} W"
	else
		echo "profile: $profile   (no RAPL limits readable)"
	fi
}

if [ "${1:-}" = limits ]; then
	limits
	exit 0
fi

echo "board:    $(cat /sys/class/dmi/id/board_name 2>/dev/null)"
echo "kernel:   $(uname -r)"
echo "module:   $(if [ -d /sys/module/clevo_control ]; then echo loaded; else echo not loaded; fi)"
acpi=
for dev in /sys/bus/acpi/devices/CLV0001*; do
	[ -e "$dev" ] && acpi="$acpi${dev##*/} "
done
echo "acpi:     ${acpi:-none}"
for dev in /sys/bus/platform/devices/CLV0001:* /sys/bus/wmi/devices/ABBC0F6[BD]-*; do
	[ -e "$dev" ] || continue
	driver=$(basename "$(readlink "$dev/driver" 2>/dev/null)" 2>/dev/null)
	echo "bound:    ${dev##*/} -> ${driver:-none}"
done
led=/sys/class/leds/rgb:kbd_backlight
if [ -d "$led" ]; then
	echo "led:      brightness $(cat "$led/brightness")/$(cat "$led/max_brightness")," \
	     "intensity $(cat "$led/multi_intensity") ($(cat "$led/multi_index"))"
	stat -c 'led perm: %U:%G %a %n' "$led/brightness" "$led/multi_intensity"
else
	echo "led:      not present"
fi
for handler in /sys/class/platform-profile/*; do
	[ -r "$handler/name" ] || continue
	echo "profiles: $(cat "$handler/name"): $(cat "$handler/choices")"
	stat -c 'prof perm: %U:%G %a %n' "$handler/profile"
done
limits
if command -v powerprofilesctl >/dev/null 2>&1; then
	echo "desktop:  $(powerprofilesctl get 2>/dev/null)" \
	     "($(powerprofilesctl 2>/dev/null | grep -m1 PlatformDriver | tr -d ' \t'))"
fi
if command -v clevoctl >/dev/null 2>&1; then
	clevoctl status
fi
if command -v systemctl >/dev/null 2>&1; then
	echo "service:  $(systemctl is-active clevo-control-backlight.service 2>/dev/null)"
fi
