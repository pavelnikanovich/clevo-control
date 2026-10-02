#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Build the Debian source package for an upload to a Launchpad PPA.
#
# The upstream tarball is the release tag without debian/; the packaging is
# debian/ of the current commit. The changelog version gets a suffix for the
# Ubuntu series, so that a later package from the distribution itself wins.
#
#   tools/ppa-source.sh [-s SERIES] [-r REVISION] [-k KEY] [-o DIRECTORY]
#
# Without -k the result is unsigned and good for a local test build only.
set -eu
cd "$(dirname "$0")/.."

series=resolute
revision=1
key=
out=build/ppa

usage() {
	sed -n '9p' "$0" | sed 's/^# *//' >&2
	exit 2
}

while getopts s:r:k:o: option; do
	case $option in
	s) series=$OPTARG ;;
	r) revision=$OPTARG ;;
	k) key=$OPTARG ;;
	o) out=$OPTARG ;;
	*) usage ;;
	esac
done
shift $((OPTIND - 1))
[ $# -eq 0 ] || usage

version=$(cat VERSION)
tag="v$version"
name=clevo-control

if ! git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
	echo "ppa-source: the release tag $tag does not exist" >&2
	exit 1
fi
if [ -n "$(git status --porcelain -- debian)" ]; then
	echo "ppa-source: debian/ has uncommitted changes" >&2
	exit 1
fi

packaged=$(dpkg-parsechangelog -S Version)
if [ "${packaged%-*}" != "$version" ]; then
	echo "ppa-source: debian/changelog is at ${packaged%-*}, VERSION says $version" >&2
	exit 1
fi
upload="$packaged~$series$revision"

mkdir -p "$out"
out=$(cd "$out" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# gzip -n leaves out the time stamp: the same tag always gives the same file,
# which Launchpad requires once a tarball of this version has been uploaded.
git archive --prefix="$name-$version/" "$tag" -- . ':(exclude)debian' |
	gzip -n >"$work/${name}_$version.orig.tar.gz"
tar -xzf "$work/${name}_$version.orig.tar.gz" -C "$work"
git archive HEAD -- debian | tar -x -C "$work/$name-$version"

sed -i "1s/^$name ([^)]*) [^;]*;/$name ($upload) $series;/" \
	"$work/$name-$version/debian/changelog"

if [ -n "$key" ]; then
	sign="-k$key"
else
	sign="-us -uc"
fi

# -d: a source package needs none of the build dependencies.
# shellcheck disable=SC2086  # $sign is one or two options
(cd "$work/$name-$version" && dpkg-buildpackage -S -sa -d $sign)

rm -rf "$work/$name-$version"
cp "$work"/* "$out/"
echo
echo "source package $upload in $out:"
for file in "$out/${name}_$version"*; do
	echo "  ${file##*/}"
done
