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

# A version number hard-coded anywhere else will go stale.
if grep -rnF --exclude-dir=.git --exclude-dir=build --exclude-dir=specs --exclude-dir=.specify \
	--exclude-dir=.claude --exclude=VERSION --exclude=CHANGELOG.md --exclude=changelog \
	"$version" . ; then
	echo "the version $version is spelled out in the files above; use @VERSION@ or drop it" >&2
	status=1
fi

exit $status
