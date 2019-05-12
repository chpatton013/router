#!/usr/bin/env bash
set -euo pipefail

echo Download the current listing of leap seconds from IETF to a temp file.
wget \
  --no-cache \
  --output-document=/tmp/leap-seconds.list \
  https://www.ietf.org/timezones/data/leap-seconds.list

echo Ensure the leap seconds file is not empty.
test -s /tmp/leap-seconds.list

echo Make the temp file usable by the ntp user.
chown ntp:ntp /tmp/leap-seconds.list
chmod 644 /tmp/leap-seconds.list

echo Overwrite the old leap seconds listing.
mv /tmp/leap-seconds.list /var/lib/ntp/leap
