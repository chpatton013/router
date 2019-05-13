#!/usr/bin/env bash
set -euo pipefail

tmpfile="$(mktemp)"

echo Download the current listing of leap seconds from IETF to a temp file.
wget \
  --no-cache \
  --output-document="$tmpfile" \
  https://www.ietf.org/timezones/data/leap-seconds.list

echo Ensure the leap seconds file is not empty.
test -s "$tmpfile"

echo Make the temp file usable by the ntp user.
chown ntp:ntp "$tmpfile"
chmod 644 "$tmpfile"

echo Overwrite the old leap seconds listing.
mv "$tmpfile" ${LEAP_SECONDS_FILE}
