#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Runs tests/extension/test_extension.js: copies the extension next to the
# shell stand-ins with its GNOME Shell imports pointed at them, and gives it a
# fake platform-profile class directory instead of /sys.
set -eu
cd "$(dirname "$0")/../.."

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

cp -r tests/extension/shellstub tests/extension/test_extension.js "$work/"
sed -e "s|resource:///org/gnome/shell/ui/main.js|./shellstub/main.js|" \
    -e "s|resource:///org/gnome/shell/ui/popupMenu.js|./shellstub/popupMenu.js|" \
    -e "s|resource:///org/gnome/shell/ui/quickSettings.js|./shellstub/quickSettings.js|" \
    -e "s|resource:///org/gnome/shell/extensions/extension.js|./shellstub/extension.js|" \
    extension/extension.js > "$work/extension.js"
if grep -q 'resource:///' "$work/extension.js"; then
	echo "extension.js imports a shell module without a stand-in" >&2
	exit 1
fi

class="$work/platform-profile"
mkdir -p "$class/platform-profile-0"
echo clevo > "$class/platform-profile-0/name"
echo "low-power quiet balanced performance" > "$class/platform-profile-0/choices"
echo balanced > "$class/platform-profile-0/profile"
sed "s|^const CLASS_DIR = .*|const CLASS_DIR = '$class';|" extension/controller.js > "$work/controller.js"
grep -qF "const CLASS_DIR = '$class';" "$work/controller.js"

gjs -m "$work/test_extension.js" "$class"
