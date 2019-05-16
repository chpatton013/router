#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id --user)" != 0 ]]; then
  echo This script must be run as root! Exiting. >&2
  exit 1
fi

if ! which python3 &>/dev/null || ! which pip3 &>/dev/null; then
  apt-get update
  apt-get install --assume-yes python3 python3-pip
fi

pip3 install --requirement requirements.txt

./setup.py "$@"
