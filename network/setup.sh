#!/usr/bin/env bash
set -euo pipefail

# Disable IPv6 for all interfaces on this machine.
sysctl -w net.ipv6.conf.all.disable_ipv6=1
