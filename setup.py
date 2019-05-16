#!/usr/bin/env python3

"""
Install a set of capabilities on the local machine.
Each capability must be a neighboring directory of this script.
Capability directories are expected to have some of the following contents:
  setup.sh
    An executable script that sets up the capability.
  config.d/
    A directory containing config files that need to be copied to the system
    root. Files are copied to the root relative to their location within the
    config directory. For example:
        //CAPABILITY/config.d/path/to/file -> /path/to/file
  capability.yaml
    A YAML file with the following properties:
      * vars: A dictionary of variable substitutions.
      * packages: A list of APT packages to install.
      * services: A list of systemd services that provide the capability.
      * files: A dictionary of relative file paths within config.d mapped to
        objects with mode and/or owner keys.
"""

import argparse
import grp
import os
import pwd
import pystache
import stat
import subprocess
import sys
import tempfile
import yaml


FORMAT_MAGENTA = "\033[95m"
FORMAT_BLUE = "\033[94m"
FORMAT_GREEN = "\033[92m"
FORMAT_YELLOW = "\033[33m"
FORMAT_RED = "\033[31m"
FORMAT_RESET = "\033[0m"

LOG_LEVEL = None


def set_log_level(log_level):
    global LOG_LEVEL
    LOG_LEVEL = log_level


def message(msg, file, *args, **kwargs):
    print(msg.format(*args, **kwargs), file=file)


def error(msg, *args, **kwargs):
    if LOG_LEVEL in ("error", "warning", "info", "debug", "trace"):
        message(
            "{}ERROR:{}{}".format(FORMAT_RED, msg, FORMAT_RESET),
            sys.stderr,
            *args,
            **kwargs
        )
    quit(1)


def warning(msg, *args, **kwargs):
    if LOG_LEVEL in ("warning", "info", "debug", "trace"):
        message(
            "{} WARN:{}{}".format(FORMAT_YELLOW, msg, FORMAT_RESET),
            sys.stderr,
            *args,
            **kwargs
        )


def info(msg, *args, **kwargs):
    if LOG_LEVEL in ("info", "debug", "trace"):
        message(
            "{} INFO:{}{}".format(FORMAT_GREEN, msg, FORMAT_RESET),
            sys.stdout,
            *args,
            **kwargs
        )


def debug(msg, *args, **kwargs):
    if LOG_LEVEL in ("debug", "trace"):
        message(
            "{}DEBUG:{}{}".format(FORMAT_BLUE, msg, FORMAT_RESET),
            sys.stdout,
            *args,
            **kwargs
        )


def trace(msg, *args, **kwargs):
    if LOG_LEVEL in ("trace"):
        message(
            "{}TRACE:{}{}".format(FORMAT_MAGENTA, msg, FORMAT_RESET),
            sys.stdout,
            *args,
            **kwargs
        )


def run(command, **kwargs):
    trace("run")

    debug("Running command: {}", command)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs)
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        message = "Command succeeded!"
        if stdout:
            message += "\n  stdout:\n\n{}\n".format(stdout.decode("utf-8"))
        if stderr:
            message += "\n  stderr:\n\n{}\n".format(stderr.decode("utf-8"))
        debug(message)
    else:
        error("\n".join([
            "Command failed!",
            "  command: {}".format(command),
            "  returncode: {}".format(process.returncode),
            "  stdout:\n\n{}\n".format(stdout.decode("utf-8")),
            "  stderr:\n\n{}\n".format(stderr.decode("utf-8")),
        ]))


def root_dir():
    trace("root_dir")

    return os.path.dirname(os.path.realpath(__file__))


def capability_root(capability_name):
    trace("capability_root")

    return os.path.join(root_dir(), capability_name)


def capability_path(capability_name, path):
    trace("capability_path")

    return os.path.join(capability_root(capability_name), path)


def capability_spec_path(capability_name):
    trace("capability_spec_path")

    return capability_path(capability_name, "capability.yaml")


def capability_spec(capability_name):
    trace("capability_spec")

    capability_yaml = open(capability_spec_path(capability_name), "r")
    capability = yaml.load(capability_yaml, Loader=yaml.SafeLoader)
    capability["name"] = capability_name
    return capability


def generate_capability_names():
    trace("generate_capability_names")

    root = root_dir()
    for name in os.listdir(root):
        path_dir = os.path.join(root, name)
        if not os.path.isdir(path_dir):
            debug("{} is not a directory", path_dir)
            continue

        path_capability = capability_spec_path(path_dir)
        if not os.path.isfile(path_capability):
            debug("{} is not a file", path_capability)
            continue

        yield os.path.basename(path_dir)


def generate_capabilities():
    trace("generate_capabilities")

    for capability_name in generate_capability_names():
        yield capability_spec(capability_name)


def install_capability_packages(capability):
    trace("install_capability_packages")

    packages = capability.get("packages", [])
    if len(packages) > 0:
        info(
            "Installing packages({}) for capability {}...",
            len(packages),
            capability["name"],
        )
        run(["apt-get", "install", "--assume-yes"] + packages)
    else:
        debug("No packages for capability {}", capability["name"])


def install_capabilities_packages(capabilities):
    trace("install_capabilities_packages")

    info("Updating APT package repository...")
    run(["apt-get", "update"])

    for capability in capabilities:
        install_capability_packages(capability)


def run_capability_setup_script(capability):
    trace("run_capability_setup_script")

    template_setup_script = capability_path(capability["name"], "setup.sh")
    if not os.path.isfile(template_setup_script):
        debug("No setup script found for capability {}", capability["name"])
        return

    debug(
        "Rendering setup script template for capability {}",
        capability["name"],
    )
    template_vars = capability.get("vars", {})
    rendered_setup_script = pystache.Renderer().render_path(
        template_setup_script,
        template_vars,
    )

    try:
        handle, setup_script = tempfile.mkstemp()
        open(setup_script, "w").write(rendered_setup_script)
        os.close(handle)
        os.chmod(setup_script, stat.S_IRWXU)

        info("Running setup script for capability {}...", capability["name"])
        run([setup_script])
    finally:
        os.unlink(setup_script)


def run_capabilities_setup_script(capabilities):
    trace("run_capabilities_setup_script")

    for capability in capabilities:
        run_capability_setup_script(capability)


def copy_capability_config_files(capability):
    trace("copy_capability_config_files")

    info("Copying config files for capability {}...", capability["name"])
    renderer = pystache.Renderer()
    template_vars = capability.get("vars", {})

    config_root = capability_path(capability["name"], "config.d")
    for root, dirnames, filenames in os.walk(config_root):
        for dirname in dirnames:
            config_path = os.path.join(root, dirname)
            system_path = os.path.join(
                "/",
                os.path.relpath(config_path, config_root),
            )
            debug("Creating directory {}", system_path)
            os.makedirs(system_path, exist_ok=True)

        for filename in filenames:
            config_path = os.path.join(root, filename)
            rendered_file = renderer.render_path(config_path, template_vars)
            system_path = os.path.join(
                "/",
                os.path.relpath(config_path, config_root),
            )
            debug("Creating file {}", system_path)
            open(system_path, "w").write(rendered_file)

    for key, value in capability.get("files", {}).items():
        path = renderer.render(key, template_vars)
        if "mode" in value:
            debug("Setting file mode: {}: {}", value["mode"], path)
            os.chmod(path, value["mode"])
        if "owner" in value:
            debug(
                "Setting file owner: {}:{}: {}",
                value["user"],
                value["group"],
                path,
            )
            os.chown(
                path,
                pwd.getpdnam(value["user"]).pw_uid,
                grp.getgrnam(value["group"]).gr_gid,
            )


def copy_capabilities_config_files(capabilities):
    trace("copy_capabilities_config_files")

    for capability in capabilities:
        copy_capability_config_files(capability)


def activate_capability_services(capability):
    trace("activate_capability_services")

    services = capability.get("services", [])
    if len(services) > 0:
        for service in capability.get("services", []):
            info(
                "Activating service {} for capability {}...",
                service,
                capability["name"],
            )
            run(["systemctl", "enable", service])
            run(["systemctl", "restart", service])
            run(["systemctl", "is-active", service])
    else:
        debug("No services for capability {}", capability["name"])


def activate_capabilities_services(capabilities):
    trace("activate_capabilities_services")

    for capability in capabilities:
        activate_capability_services(capability)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-level",
        "-l",
        choices=("error", "warning", "info", "debug", "trace"),
        default="error",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    set_log_level(args.log_level)

    if os.getuid() != 0:
        error("This script must be run as root! Exiting.")

    capabilities = [c for c in generate_capabilities()]

    install_capabilities_packages(capabilities)
    run_capabilities_setup_script(capabilities)
    copy_capabilities_config_files(capabilities)
    activate_capabilities_services(capabilities)

if __name__ == "__main__":
    main()
