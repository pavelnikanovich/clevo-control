#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Every static check of the project. A missing tool skips its check with a
# note, unless STRICT=1 (continuous integration), where it is an error.
set -u
cd "$(dirname "$0")/.." || exit 1

KDIR=${KDIR:-/lib/modules/$(uname -r)/build}
BUILD=${BUILD:-build}
status=0

run() {
	name=$1; shift
	if "$@"; then
		echo "ok    $name"
	else
		echo "FAIL  $name"
		status=1
	fi
}

need() {
	if command -v "$1" >/dev/null 2>&1; then
		return 0
	fi
	if [ "${STRICT:-0}" = 1 ]; then
		echo "FAIL  $1 is not installed"
		status=1
	else
		echo "skip  $1 is not installed"
	fi
	return 1
}

need ruff && run "ruff" ruff check -q .
need mypy && run "mypy" mypy --no-error-summary

if [ -x "$KDIR/scripts/checkpatch.pl" ]; then
	run "checkpatch" "$KDIR/scripts/checkpatch.pl" -q --no-tree --strict -f module/clevo-control.c
elif [ "${STRICT:-0}" = 1 ]; then
	echo "FAIL  no checkpatch.pl in $KDIR"; status=1
else
	echo "skip  no checkpatch.pl in $KDIR"
fi

# node only parses files it recognises as modules.
if need node; then
	tmp=$(mktemp -d)
	for f in extension/extension.js extension/controller.js tests/extension/test_controller.js; do
		cp "$f" "$tmp/check.mjs"
		run "syntax $f" node --check "$tmp/check.mjs"
	done
	rm -rf "$tmp"
fi

run "metadata.json" python3 -c "import json, sys; json.load(open(sys.argv[1]))" \
	"$BUILD/extension/metadata.json"

need udevadm && run "udev rules" udevadm verify --no-summary data/70-clevo-control.rules
need desktop-file-validate && run "desktop files" desktop-file-validate data/*.desktop
need appstreamcli && run "metainfo" appstreamcli validate --no-net \
	data/io.github.pavelnikanovich.ClevoControl.metainfo.xml

# The unit can only be verified where the program it starts exists.
if need systemd-analyze; then
	if [ -x /usr/bin/clevoctl ]; then
		run "service unit" systemd-analyze verify data/clevo-control-backlight.service
	else
		echo "skip  service unit (clevoctl is not installed)"
	fi
fi

if need man; then
	for page in "$BUILD"/man/*; do
		out=$(MANWIDTH=80 man --warnings -E UTF-8 -l "$page" 2>&1 >/dev/null)
		if [ -z "$out" ]; then
			echo "ok    man ${page##*/}"
		else
			echo "FAIL  man ${page##*/}"; echo "$out"; status=1
		fi
	done
fi

need shellcheck && run "shellcheck" shellcheck tools/*.sh

run "version" tools/check-version.sh

exit $status
