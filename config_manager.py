
# config_manager.py — With Version Tracking & Diff Comparison
from netmiko import ConnectHandler
from datetime import datetime
import os
import json
import difflib


# ============================================================
# PULL CONFIG — Connects to a device and saves the config
# ============================================================
def pull_config(device):
    """
    SSH into a device, pull the running config,
    save it with a version number, and update the version log.
    """
    host = device["host"]
    print(f"Connecting to {host}...")

    # Connect using Netmiko
    connection = ConnectHandler(**device)

    # Send the right command based on vendor
    if "junos" in device["device_type"]:
        output = connection.send_command("show configuration")
    else:
        output = connection.send_command("show running-config")

    connection.disconnect()

    # Create device folder inside saved_configs
    device_folder = f"saved_configs/{host}"
    os.makedirs(device_folder, exist_ok=True)

    # Get the next version number
    version = get_next_version(host)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save the config file
    config_filename = f"{device_folder}/v{version}.txt"
    with open(config_filename, "w") as f:
        f.write(output)

    # Update the version log
    update_version_log(host, version, timestamp)

    print(f"Config saved as version {version} → {config_filename}")
    return config_filename


# ============================================================
# VERSION LOG — Keeps track of all versions for each device
# ============================================================
def get_version_log_path(host):
    """Returns the path to a device's version log file."""
    return f"saved_configs/{host}/version_log.json"


def load_version_log(host):
    """Loads the version log for a device. Creates one if it doesn't exist."""
    log_path = get_version_log_path(host)
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return json.load(f)
    return {"device": host, "versions": []}


def update_version_log(host, version, timestamp):
    """Adds a new version entry to the log."""
    log = load_version_log(host)
    log["versions"].append({
        "version": version,
        "timestamp": timestamp,
        "filename": f"v{version}.txt"
    })
    log_path = get_version_log_path(host)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=4)


def get_next_version(host):
    """Figures out what the next version number should be."""
    log = load_version_log(host)
    if not log["versions"]:
        return 1
    return log["versions"][-1]["version"] + 1


# ============================================================
# SHOW VERSIONS — Lists all saved versions for a device
# ============================================================
def show_versions(host):
    """Displays all saved config versions for a device."""
    log = load_version_log(host)

    if not log["versions"]:
        print(f"No saved configs for {host}")
        return

    print(f"\nSaved versions for {host}:")
    print("-" * 45)
    print(f"{'Version':<10} {'Timestamp':<25}")
    print("-" * 45)

    for entry in log["versions"]:
        print(f"v{entry['version']:<9} {entry['timestamp']:<25}")

    print(f"\nTotal: {len(log['versions'])} version(s)")


# ============================================================
# DIFF — Compare two config versions side by side
# ============================================================
def compare_configs(host, version_a, version_b):
    """
    Compares two config versions and shows what changed.
    Green (+) = added lines
    Red (-) = removed lines
    """
    file_a = f"saved_configs/{host}/v{version_a}.txt"
    file_b = f"saved_configs/{host}/v{version_b}.txt"

    # Make sure both files exist
    if not os.path.exists(file_a):
        print(f"Version {version_a} not found!")
        return
    if not os.path.exists(file_b):
        print(f"Version {version_b} not found!")
        return

    # Read both configs
    with open(file_a, "r") as f:
        config_a = f.readlines()
    with open(file_b, "r") as f:
        config_b = f.readlines()

    # Generate the diff
    diff = difflib.unified_diff(
        config_a,
        config_b,
        fromfile=f"v{version_a}",
        tofile=f"v{version_b}",
        lineterm=""
    )

    # Display the results
    changes_found = False
    added = 0
    removed = 0

    print(f"\nComparing v{version_a} → v{version_b} for {host}")
    print("=" * 60)

    for line in diff:
        changes_found = True
        if line.startswith("+") and not line.startswith("+++"):
            print(f"  [ADDED]   {line[1:]}")
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            print(f"  [REMOVED] {line[1:]}")
            removed += 1

    if not changes_found:
        print("No changes detected — configs are identical!")
    else:
        print("=" * 60)
        print(f"Summary: {added} line(s) added, {removed} line(s) removed")

