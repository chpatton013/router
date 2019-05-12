#!/usr/bin/env bash
set -xeuo pipefail

# The list of capabilities this script will install.
# Each capability must be a neighboring directory of this script.
# Capability directories are expected to have some of the following contents:
#   packages.list
#     * A flat list of APT packages to install.
#   services.list
#     * A flat list of systemd services that provide the capability.
#   setup.sh
#     * An executable script that sets up the capability.
#   config.d/
#     * A directory containing config files that need to be copied to the system
#       root. Files are copied to the root relative to their location within the
#       config directory. For example:
#         //CAPABILITY/config.d/path/to/file -> /path/to/file
#   config.owner
#     * A list of file ownership settings for files copied from config.d.
#       Example format: `path/to/file user:group`
#   config.mode
#     * A list of file mode settings for files copied from config.d.
#       Example format: `path/to/file 644`
CAPABILITIES=(
  ntp
  unattended-upgrades
)

ROOT_DIR="$(builtin cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

function install_capability_packages() {
  local capability capability_root package_list
  capability="$1"
  capability_root="$ROOT_DIR/$capability"
  package_list="$capability_root/packages.list"
  readonly capability capability_root package_list

  if [ -f "$package_list" ]; then
    local -a packages
    while IFS="" read -r package || [[ -n $package ]]; do
      packages+=("$package")
    done <"$package_list"
    readonly -a packages

    echo Installing packages for capability $capability.
    apt-get install --assume-yes "${packages[@]}"
  fi
}

function install_capabilities_packages() {
  echo Update APT package repositories.
  apt-get update

  for capability in "${CAPABILITIES[@]}"; do
    install_capability_packages "$capability"
  done
}

function run_capability_setup_script() {
  local capability capability_root setup_script
  capability="$1"
  capability_root="$ROOT_DIR/$capability"
  setup_script="$capability_root/setup.sh"
  readonly capability capability_root setup_script

  if [ -f "$setup_script" ]; then
    echo Running setup script for capability $capability.
    "$setup_script"
  fi
}

function run_capabilities_setup_scripts() {
  for capability in "${CAPABILITIES[@]}"; do
    run_capability_setup_script "$capability"
  done
}

function copy_capability_config_files() {
  local capability capability_root config_root
  capability="$1"
  capability_root="$ROOT_DIR/$capability"
  config_root="$capability_root/config.d"
  readonly capability capability_root config_root

  local -a config_dirs
  find "$config_root" -type d |
    xargs realpath --relative-to="$config_root" |
    while IFS="" read -r config_dir || [[ -n $config_dir ]]; do
      config_dirs+=("$config_dir")
    done
  readonly -a config_dirs
  if [ -n "${config_dirs[@]}" ]; then
    echo Creating config file directories for capability $capability.
    echo "${config_dirs[@]}" | xargs -I{} mkdir --parents /{}
  fi

  local -a config_files
  find "$config_root" -type f |
    xargs realpath --relative-to="$config_root" |
    while IFS="" read -r config_file || [[ -n $config_file ]]; do
      config_files+=("$config_file")
    done
  readonly -a config_files
  if [ -n "${config_files[@]}" ]; then
    echo Copying config files for capability $capability.
    echo "${config_files[@]}" | xargs -I{} cp "$capability_root/{}" /{}
  fi

  if [ -f "$capability_root/config.owner" ]; then
    echo Setting config file owner for capability $capability.
    while IFS="" read -r line || [[ -n $line ]]; do
      file_path="/${line% *}"
      file_owner="${line##* }"
      chown "$file_owner" "$file_path"
    done <"$capability_root/config.owner"
  fi

  if [ -f "$capability_root/config.mode" ]; then
    echo Setting config file mode for capability $capability.
    while IFS="" read -r line || [[ -n $line ]]; do
      file_path="/${line% *}"
      file_mode="${line##* }"
      chmod "$file_mode" "$file_path"
    done <"$capability_root/config.mode"
  fi
}

function copy_capabilities_config_files() {
  for capability in "${CAPABILITIES[@]}"; do
    copy_capability_config_files "$capability"
  done
}

function verify_service() {
  local service
  service="$1"
  readonly service

  echo Verify that the $service service started successfully.
  for ((n = 0; n < 5; n++)); do
    if systemctl is-active "$service"; then
      return 0
    fi
  done
  return 1
}

function activate_capability_services() {
  local capability capability_root services_list
  capability="$1"
  capability_root="$ROOT_DIR/$capability"
  services_list="$capability_root/services.list"
  readonly capability capability_root services_list

  if [ -f "$services_list" ]; then
    while IFS="" read -r service || [[ -n $service ]]; do
      echo Enable the $service service so it will run after a system restart.
      systemctl enable "$service"

      echo Restart the $service service to reload config changes.
      systemctl restart "$service"

      verify_service "$service"
    done <"$services_list"
  fi
}

function activate_capabilities_services() {
  for capability in "${CAPABILITIES[@]}"; do
    activate_capability_services "$capability"
  done
}

function main() {
  if [[ "$(id --user)" != 0 ]]; then
    echo This script must be run as root! Exiting. >&2
    exit 1
  fi

  install_capabilities_packages
  run_capabilities_setup_scripts
  copy_capabilities_config_files
  activate_capabilities_services
}

main
