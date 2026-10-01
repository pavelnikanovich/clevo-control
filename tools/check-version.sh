#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# VERSION is the only place the version is maintained by hand; the Debian
# changelog has to agree with it, and nothing else may spell it out.
set -eu
cd "$(dirname "$0")/.."

version=$(cat VERSION)
status=0

if [ -f debian/changelog ]; then
	debian=$(sed -n '1s/^[^(]*(\([^)]*\)).*/\1/p' debian/changelog)
	if [ "${debian%-*}" != "$version" ]; then
		echo "debian/changelog is at ${debian%-*}, VERSION says $version" >&2
		status=1
	fi
fi

# A version number hard-coded anywhere else will go stale. Only files under
# version control are looked at, so build output does not count.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	if git ls-files -z | grep -zvE '^(VERSION|CHANGELOG\.md|debian/changelog|specs/|\.specify/|\.claude/)' |
		xargs -0 grep -nF -- "$version"; then
		echo "the version $version is spelled out in the files above; use @VERSION@ or drop it" >&2
		status=1
	fi
fi

exit $status
