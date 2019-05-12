# router

Hand-rolled home router provisioning.

## Networking Capabilities

| Capability      | iptables | dhcpd | bind9 | ntpd | nginx | undecided |
|-----------------|----------|-------|-------|------|-------|-----------|
| NAT             |    X     |       |       |      |       |           |
| Firewall        |    X     |       |       |      |       |           |
| Port Forwarding |    X     |       |       |      |       |           |
| DHCP            |          |   X   |       |      |       |           |
| DNS             |          |       |   X   |      |       |           |
| DDNS            |          |       |   X   |      |       |           |
| NTP             |          |       |       |  X   |       |           |
| SSL Termination |          |       |       |      |   X   |           |
| Web Proxy       |          |       |       |      |   X   |           |
| VPN             |          |       |       |      |       |     X     |

## System Administration Details

Operating system: Debian 9 ("stretch")

Capability packages:
* iptables
* isc-dhcp-server
* bind9
* ntp
* nginx

Additional packages:
* apt-config-auto-update
* apt-listchanges
* etckeeper
* htop
* mailutils
* openssh-server
* sudo
* unattended-upgrades
* vim-tiny

VirtualBox packages:
* build-essential
* linux-headers-$(uname --kernel-release)
