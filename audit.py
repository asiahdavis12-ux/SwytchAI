
# audit.py — SwytchAI Audit Logging System
import json
import os
from datetime import datetime

AUDIT_FILE = "audit_log.json"


def load_audit_log():
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, "r") as f:
            return json.load(f)
    return {"entries": []}


def save_audit_log(data):
    with open(AUDIT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log_action(username, action, details="", target=""):
    """
    Logs an action to the audit trail.

    Args:
        username:  Who performed the action
        action:    What they did (e.g. "LOGIN", "PULL_CONFIG")
        details:   Extra info about the action
        target:    What was affected (e.g. device host, change ID)
    """
    data = load_audit_log()

    entry_id = 1
    if data["entries"]:
        entry_id = max(e["id"] for e in data["entries"]) + 1

    entry = {
        "id": entry_id,
        "username": username,
        "action": action,
        "details": details,
        "target": target,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    data["entries"].append(entry)
    save_audit_log(data)
    return entry


def get_audit_entries(username=None, action=None, limit=100):
    """
    Gets audit entries with optional filters.

    Args:
        username:  Filter by user (optional)
        action:    Filter by action type (optional)
        limit:     Max entries to return
    """
    data = load_audit_log()
    entries = data["entries"]

    if username:
        entries = [e for e in entries if e["username"] == username]

    if action:
        entries = [e for e in entries if e["action"] == action]

    # Return newest first
    entries.sort(key=lambda x: x["timestamp"], reverse=True)
    return entries[:limit]


def get_all_actions():
    """Returns a list of all unique action types in the log."""
    data = load_audit_log()
    actions = set(e["action"] for e in data["entries"])
    return sorted(actions)


def get_all_users_in_log():
    """Returns a list of all users who have entries in the log."""
    data = load_audit_log()
    users = set(e["username"] for e in data["entries"])
    return sorted(users)

