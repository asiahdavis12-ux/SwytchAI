
# config_pusher.py — Config Push with Approval Workflow
from netmiko import ConnectHandler
from datetime import datetime
import os
import json


# ============================================================
# CHANGE LOG — Tracks all proposed and pushed changes
# ============================================================
def get_change_log_path():
    """Returns the path to the change log file."""
    os.makedirs("change_logs", exist_ok=True)
    return "change_logs/change_log.json"


def load_change_log():
    """Loads the change log. Creates one if it doesn't exist."""
    log_path = get_change_log_path()
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return json.load(f)
    return {"changes": []}


def save_change_log(log):
    """Saves the change log to file."""
    log_path = get_change_log_path()
    with open(log_path, "w") as f:
        json.dump(log, f, indent=4)


def get_next_change_id():
    """Gets the next change ID number."""
    log = load_change_log()
    if not log["changes"]:
        return 1
    return log["changes"][-1]["change_id"] + 1


# ============================================================
# PROPOSE A CHANGE — Stage a config change for review
# ============================================================
def propose_change(device, config_lines, description=""):
    """
    Stages a config change for review. Does NOT push it yet.
    Returns the change ID for tracking.
    """
    host = device["host"]
    change_id = get_next_change_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the change record
    change_record = {
        "change_id": change_id,
        "host": host,
        "description": description,
        "config_lines": config_lines,
        "status": "PENDING",
        "proposed_at": timestamp,
        "proposed_by": "Asiah",
        "reviewed_at": None,
        "reviewed_by": None,
        "pushed_at": None,
        "rollback_config": None,
    }

    # Save to change log
    log = load_change_log()
    log["changes"].append(change_record)
    save_change_log(log)

    print(f"\n{'=' * 60}")
    print(f"  CHANGE #{change_id} PROPOSED")
    print(f"{'=' * 60}")
    print(f"  Device:      {host}")
    print(f"  Description: {description}")
    print(f"  Proposed at: {timestamp}")
    print(f"  Status:      ⏳ PENDING APPROVAL")
    print(f"{'=' * 60}")
    print(f"\n  Config lines to be pushed:")
    print(f"  {'-' * 40}")
    for line in config_lines:
        print(f"    {line}")
    print(f"  {'-' * 40}")
    print(f"\n  Use 'Review Changes' to approve or reject.\n")

    return change_id


# ============================================================
# REVIEW CHANGES — View all pending changes
# ============================================================
def show_pending_changes():
    """Displays all changes that are waiting for approval."""
    log = load_change_log()
    pending = [c for c in log["changes"] if c["status"] == "PENDING"]

    if not pending:
        print("\n  ✅ No pending changes — all clear!\n")
        return False

    print(f"\n{'=' * 60}")
    print(f"  PENDING CHANGES ({len(pending)} waiting for review)")
    print(f"{'=' * 60}")

    for change in pending:
        print(f"\n  Change #{change['change_id']}")
        print(f"  Device:      {change['host']}")
        print(f"  Description: {change['description']}")
        print(f"  Proposed by: {change['proposed_by']}")
        print(f"  Proposed at: {change['proposed_at']}")
        print(f"  Config lines:")
        for line in change["config_lines"]:
            print(f"    {line}")
        print(f"  {'-' * 40}")

    return True


# ============================================================
# APPROVE & PUSH — Review, approve, and push a change
# ============================================================
def review_change(change_id, device):
    """
    Reviews a specific change. If approved, pushes it to the device.
    Saves the current config first for rollback purposes.
    """
    log = load_change_log()

    # Find the change
    change = None
    for c in log["changes"]:
        if c["change_id"] == change_id:
            change = c
            break

    if not change:
        print(f"\n  ❌ Change #{change_id} not found!\n")
        return

    if change["status"] != "PENDING":
        print(f"\n  ❌ Change #{change_id} is already {change['status']}\n")
        return

    # Show the change details
    print(f"\n{'=' * 60}")
    print(f"  REVIEWING CHANGE #{change_id}")
    print(f"{'=' * 60}")
    print(f"  Device:      {change['host']}")
    print(f"  Description: {change['description']}")
    print(f"  Proposed by: {change['proposed_by']}")
    print(f"\n  Config to be pushed:")
    print(f"  {'-' * 40}")
    for line in change["config_lines"]:
        print(f"    {line}")
    print(f"  {'-' * 40}")

    # Ask for approval
    print(f"\n  ⚠️  This will modify the device: {change['host']}")
    decision = input("  Approve and push? (yes/no): ").strip().lower()

    if decision == "yes":
        # Save current config for rollback BEFORE pushing
        print(f"\n  Saving current config for rollback...")
        rollback_config = get_current_config(device)
        change["rollback_config"] = rollback_config

        # Push the config
        print(f"  Pushing config to {change['host']}...")
        success = push_config(device, change["config_lines"])

        if success:
            change["status"] = "APPROVED & PUSHED"
            change["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            change["reviewed_by"] = "Asiah"
            change["pushed_at"] = change["reviewed_at"]
            save_change_log(log)
            print(f"\n  ✅ Change #{change_id} APPROVED and PUSHED successfully!")
            print(f"  Rollback config saved in case you need to revert.\n")
        else:
            change["status"] = "PUSH FAILED"
            save_change_log(log)
            print(f"\n  ❌ Push failed! Device was not modified.\n")

    elif decision == "no":
        change["status"] = "REJECTED"
        change["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        change["reviewed_by"] = "Asiah"
        save_change_log(log)
        print(f"\n  🚫 Change #{change_id} REJECTED. No changes were made.\n")

    else:
        print(f"\n  Invalid input. Change remains PENDING.\n")


# ============================================================
# PUSH CONFIG — Actually sends the config to the device
# ============================================================
def push_config(device, config_lines):
    """
    Pushes config lines to a device using Netmiko.
    Returns True if successful, False if it fails.
    """
    try:
        connection = ConnectHandler(**device)
        output = connection.send_config_set(config_lines)
        print(f"\n  Device output:")
        print(f"  {'-' * 40}")
        for line in output.split("\n"):
            print(f"    {line}")
        print(f"  {'-' * 40}")
        connection.disconnect()
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


# ============================================================
# GET CURRENT CONFIG — Pulls config before pushing (for rollback)
# ============================================================
def get_current_config(device):
    """Pulls the current running config for rollback purposes."""
    try:
        connection = ConnectHandler(**device)
        if "junos" in device["device_type"]:
            output = connection.send_command("show configuration")
        else:
            output = connection.send_command("show running-config")
        connection.disconnect()
        return output
    except Exception as e:
        print(f"  Warning: Could not save rollback config — {e}")
        return None


# ============================================================
# ROLLBACK — Revert a pushed change
# ============================================================
def rollback_change(change_id, device):
    """
    Rolls back an approved change by restoring the previous config.
    """
    log = load_change_log()

    # Find the change
    change = None
    for c in log["changes"]:
        if c["change_id"] == change_id:
            change = c
            break

    if not change:
        print(f"\n  ❌ Change #{change_id} not found!\n")
        return

    if "PUSHED" not in change["status"]:
        print(f"\n  ❌ Change #{change_id} was never pushed — nothing to roll back.\n")
        return

    if not change["rollback_config"]:
        print(f"\n  ❌ No rollback config saved for change #{change_id}.\n")
        return

    print(f"\n  ⚠️  Rolling back change #{change_id} on {change['host']}...")
    confirm = input("  Are you sure? (yes/no): ").strip().lower()

    if confirm == "yes":
        try:
            connection = ConnectHandler(**device)
            # Push the saved rollback config
            config_lines = change["rollback_config"].split("\n")
            connection.send_config_set(config_lines)
            connection.disconnect()

            change["status"] = "ROLLED BACK"
            save_change_log(log)
            print(f"\n  ✅ Change #{change_id} has been ROLLED BACK successfully!\n")
        except Exception as e:
            print(f"\n  ❌ Rollback failed: {e}\n")
    else:
        print(f"\n  Rollback cancelled.\n")


# ============================================================
# CHANGE HISTORY — View all changes (pending, approved, rejected)
# ============================================================
def show_change_history():
    """Shows the full history of all changes."""
    log = load_change_log()

    if not log["changes"]:
        print("\n  No changes recorded yet.\n")
        return

    print(f"\n{'=' * 60}")
    print(f"  CHANGE HISTORY ({len(log['changes'])} total)")
    print(f"{'=' * 60}")

    for change in log["changes"]:
        status_icon = {
            "PENDING": "⏳",
            "APPROVED & PUSHED": "✅",
            "REJECTED": "🚫",
            "PUSH FAILED": "❌",
            "ROLLED BACK": "↩️",
        }.get(change["status"], "❓")

        print(f"\n  {status_icon} Change #{change['change_id']} — {change['status']}")
        print(f"     Device:      {change['host']}")
        print(f"     Description: {change['description']}")
        print(f"     Proposed:    {change['proposed_at']} by {change['proposed_by']}")
        if change["reviewed_at"]:
            print(f"     Reviewed:    {change['reviewed_at']} by {change['reviewed_by']}")

    print()

