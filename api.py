
# api.py — SwytchAI REST API
from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime
import os
import json

from devices import all_devices, cisco_switch
from config_manager import pull_config, load_version_log
from config_pusher import (
    load_change_log, save_change_log, get_next_change_id,
    get_current_config, push_config as netmiko_push_config,
)
from users import load_user_database, ROLES, get_permissions
from notifications import (
    get_user_notifications, get_unread_count,
    notify_change_proposed, notify_change_approved, notify_change_rejected,
)
from audit import log_action
from ai_assistant import parse_request, generate_config, TEMPLATES

# Create a Blueprint so we can register API routes in app.py
api = Blueprint("api", __name__)

# ============================================================
# API KEY AUTH
# ============================================================
API_KEYS_FILE = "api_keys.json"


def load_api_keys():
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    return {"keys": []}


def save_api_keys(data):
    with open(API_KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def require_api_key(f):
    """Decorator that checks for a valid API key in the request header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({"error": "Missing API key. Include X-API-Key header."}), 401

        keys_data = load_api_keys()
        key_record = None
        for k in keys_data["keys"]:
            if k["key"] == api_key and k["active"]:
                key_record = k
                break

        if not key_record:
            return jsonify({"error": "Invalid or inactive API key."}), 401

        # Attach user info to request
        request.api_user = key_record["username"]
        request.api_role = key_record["role"]
        return f(*args, **kwargs)

    return decorated


def api_has_permission(permission):
    """Checks if the API user has a specific permission."""
    role = request.api_role
    perms = ROLES.get(role, {}).get("permissions", [])
    return permission in perms


# ============================================================
# HEALTH CHECK
# ============================================================
@api.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({
        "status": "ok",
        "app": "SwytchAI",
        "version": "1.0.0",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


# ============================================================
# DEVICES
# ============================================================
@api.route("/api/devices", methods=["GET"])
@require_api_key
def api_get_devices():
    devices = []
    for i, d in enumerate(all_devices):
        devices.append({
            "id": i,
            "host": d["host"],
            "vendor": d.get("vendor", "unknown"),
            "port": d.get("port", 22),
            "device_type": d.get("device_type", "unknown"),
        })
    return jsonify({"devices": devices, "count": len(devices)})


@api.route("/api/devices/<int:device_id>/pull", methods=["POST"])
@require_api_key
def api_pull_config(device_id):
    if not api_has_permission("pull_config"):
        return jsonify({"error": "Permission denied."}), 403

    if device_id >= len(all_devices):
        return jsonify({"error": "Device not found."}), 404

    device = all_devices[device_id]
    try:
        filename = pull_config(device)
        log_action(request.api_user, "API_PULL_CONFIG", "API pull", device["host"])
        return jsonify({
            "success": True,
            "message": f"Config pulled from {device['host']}",
            "filename": filename,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# CONFIGS
# ============================================================
@api.route("/api/configs/<path:host>", methods=["GET"])
@require_api_key
def api_get_config_versions(host):
    if not api_has_permission("view_versions"):
        return jsonify({"error": "Permission denied."}), 403

    log = load_version_log(host)
    return jsonify({
        "host": host,
        "versions": log.get("versions", []),
        "count": len(log.get("versions", [])),
    })


@api.route("/api/configs/<path:host>/version/<int:version>", methods=["GET"])
@require_api_key
def api_get_config_content(host, version):
    if not api_has_permission("view_versions"):
        return jsonify({"error": "Permission denied."}), 403

    filepath = f"saved_configs/{host}/v{version}.txt"
    if not os.path.exists(filepath):
        return jsonify({"error": f"Version {version} not found."}), 404

    with open(filepath, "r") as f:
        config_text = f.read()

    return jsonify({
        "host": host,
        "version": version,
        "config": config_text,
    })


# ============================================================
# CHANGES
# ============================================================
@api.route("/api/changes", methods=["GET"])
@require_api_key
def api_get_changes():
    if not api_has_permission("view_history"):
        return jsonify({"error": "Permission denied."}), 403

    status_filter = request.args.get("status", "")
    log = load_change_log()
    changes = log.get("changes", [])

    if status_filter:
        changes = [c for c in changes if status_filter.upper() in c["status"]]

    changes.reverse()
    return jsonify({"changes": changes, "count": len(changes)})


@api.route("/api/changes", methods=["POST"])
@require_api_key
def api_propose_change():
    if not api_has_permission("propose_change"):
        return jsonify({"error": "Permission denied."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required."}), 400

    config_lines = data.get("config_lines", [])
    description = data.get("description", "")

    if not config_lines:
        return jsonify({"error": "config_lines is required."}), 400

    if isinstance(config_lines, str):
        config_lines = config_lines.split("\n")

    change_id = get_next_change_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    users = load_user_database()
    proposer_name = users.get(request.api_user, {}).get("name", request.api_user)

    change_record = {
        "change_id": change_id,
        "host": cisco_switch["host"],
        "description": description,
        "config_lines": config_lines,
        "status": "PENDING",
        "proposed_at": timestamp,
        "proposed_by": proposer_name,
        "reviewed_at": None,
        "reviewed_by": None,
        "pushed_at": None,
        "rollback_config": None,
    }

    log = load_change_log()
    log["changes"].append(change_record)
    save_change_log(log)

    log_action(request.api_user, "API_PROPOSE_CHANGE", f"Change #{change_id}: {description}", cisco_switch["host"])
    notify_change_proposed(change_record, proposer_name)

    return jsonify({
        "success": True,
        "change_id": change_id,
        "status": "PENDING",
        "message": f"Change #{change_id} proposed successfully.",
    }), 201


@api.route("/api/changes/<int:change_id>/approve", methods=["POST"])
@require_api_key
def api_approve_change(change_id):
    if not api_has_permission("approve_change"):
        return jsonify({"error": "Permission denied."}), 403

    users = load_user_database()
    reviewer_name = users.get(request.api_user, {}).get("name", request.api_user)

    log = load_change_log()
    for change in log["changes"]:
        if change["change_id"] == change_id and change["status"] == "PENDING":
            try:
                rollback = get_current_config(cisco_switch)
                change["rollback_config"] = rollback
            except Exception:
                change["rollback_config"] = None

            try:
                success = netmiko_push_config(cisco_switch, change["config_lines"])
                if success:
                    change["status"] = "APPROVED & PUSHED"
                    change["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    change["reviewed_by"] = reviewer_name
                    change["pushed_at"] = change["reviewed_at"]
                    save_change_log(log)
                    log_action(request.api_user, "API_APPROVE_CHANGE", f"Approved #{change_id}", change["host"])
                    notify_change_approved(change, reviewer_name)
                    return jsonify({"success": True, "message": f"Change #{change_id} approved and pushed."})
                else:
                    change["status"] = "PUSH FAILED"
                    save_change_log(log)
                    return jsonify({"success": False, "error": "Push failed."}), 500
            except Exception as e:
                change["status"] = "PUSH FAILED"
                save_change_log(log)
                return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"error": f"Change #{change_id} not found or not pending."}), 404


@api.route("/api/changes/<int:change_id>/reject", methods=["POST"])
@require_api_key
def api_reject_change(change_id):
    if not api_has_permission("approve_change"):
        return jsonify({"error": "Permission denied."}), 403

    users = load_user_database()
    reviewer_name = users.get(request.api_user, {}).get("name", request.api_user)

    log = load_change_log()
    for change in log["changes"]:
        if change["change_id"] == change_id and change["status"] == "PENDING":
            change["status"] = "REJECTED"
            change["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            change["reviewed_by"] = reviewer_name
            save_change_log(log)
            log_action(request.api_user, "API_REJECT_CHANGE", f"Rejected #{change_id}", change["host"])
            notify_change_rejected(change, reviewer_name)
            return jsonify({"success": True, "message": f"Change #{change_id} rejected."})

    return jsonify({"error": f"Change #{change_id} not found or not pending."}), 404


# ============================================================
# AI ASSISTANT
# ============================================================
@api.route("/api/ai/generate", methods=["POST"])
@require_api_key
def api_ai_generate():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required."}), 400

    user_input = data.get("input", "")
    vendor = data.get("vendor", "cisco_ios")
    params = data.get("params", {})

    template_name = parse_request(user_input)
    if not template_name:
        return jsonify({"success": False, "message": f"Could not understand: '{user_input}'"}), 400

    template = TEMPLATES[template_name]

    if not params and template["params"]:
        return jsonify({
            "success": True,
            "needs_params": True,
            "template_name": template_name,
            "description": template["description"],
            "params_needed": template["params"],
        })

    config_lines = generate_config(template_name, vendor, params)
    if not config_lines:
        return jsonify({"success": False, "message": f"Vendor '{vendor}' not supported for this command."}), 400

    log_action(request.api_user, "API_AI_CONFIG", f"Generated: {template['description']}")

    return jsonify({
        "success": True,
        "template_name": template_name,
        "description": template["description"],
        "vendor": vendor,
        "config_lines": config_lines,
    })


# ============================================================
# NOTIFICATIONS
# ============================================================
@api.route("/api/notifications", methods=["GET"])
@require_api_key
def api_get_notifications():
    notifications = get_user_notifications(request.api_user)
    unread = get_unread_count(request.api_user)
    return jsonify({
        "notifications": notifications,
        "unread_count": unread,
        "total": len(notifications),
    })


# ============================================================
# API KEY MANAGEMENT
# ============================================================
@api.route("/api/keys/generate", methods=["POST"])
@require_api_key
def api_generate_key():
    if not api_has_permission("manage_users"):
        return jsonify({"error": "Permission denied. Manager or Admin role required."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required."}), 400

    username = data.get("username", "")
    label = data.get("label", "default")

    users = load_user_database()
    if username not in users:
        return jsonify({"error": f"User '{username}' not found."}), 404

    import secrets
    new_key = "swytch_" + secrets.token_hex(24)

    keys_data = load_api_keys()
    keys_data["keys"].append({
        "key": new_key,
        "username": username,
        "role": users[username]["role"],
        "label": label,
        "active": True,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "created_by": request.api_user,
    })
    save_api_keys(keys_data)

    log_action(request.api_user, "API_KEY_CREATED", f"Key for {username}: {label}")

    return jsonify({
        "success": True,
        "api_key": new_key,
        "username": username,
        "label": label,
        "message": "Save this key! It won't be shown again.",
    }), 201

