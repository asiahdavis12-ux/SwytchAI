from dotenv import load_dotenv
load_dotenv()

import secrets
import pyotp
import qrcode
import base64
import io
from webhooks import notify_config_change
from database import db_get_webhook_settings, db_save_webhook_settings
from database import get_db
from reports import generate_compliance_pdf, generate_device_report_pdf
from compliance import COMPLIANCE_RULES, run_compliance_check
from scheduler import start_scheduler, run_backup_now, schedule_org_backup
from napalm_engine import check_device_health
from datetime import datetime, timedelta
from email_service import init_mail, email_change_proposed, email_change_approved, email_change_rejected, email_welcome, email_team_invite
from plan_limits import check_user_limit, check_device_limit, check_feature_access, get_usage_summary
from billing import PLANS, STRIPE_PUBLISHABLE_KEY, create_checkout_session, create_billing_portal_session
from database import (db_get_branding,db_save_branding,db_get_backup_settings,db_save_backup_settings,db_update_org_stripe,db_update_org_plan,db_get_org_billing
)

from security import sanitize_input, validate_username, validate_password, validate_config_lines, validate_description

from api import api
from audit import log_action, get_audit_entries, get_all_actions, get_all_users_in_log
from database import (
    init_db,get_db,db_get_user, db_get_all_users, db_create_user,
    db_get_changes, db_get_change, db_create_change, db_update_change_status,
    db_create_notification, db_get_notifications, db_get_unread_count,
    db_mark_notification_read, db_mark_all_notifications_read,
    db_delete_notification, db_clear_notifications,
    db_log_action, db_get_audit_entries,db_get_all_actions,db_get_dashboard_stats, db_get_all_users_in_log,
    db_create_org, db_get_org, db_get_org_by_slug, db_get_org_users, db_get_org_user_count,
    db_create_invitation, db_get_invitation, db_accept_invitation,
    db_add_device, db_get_org_devices, db_get_device, db_delete_device,
    db_get_org_members, db_update_user_role, db_remove_user_from_org,
    db_get_org_members, db_update_user_role, db_remove_user_from_org,
    db_update_user_email,db_create_reset_token,db_get_reset_token,db_use_reset_token,

)

from notifications import (
    get_user_notifications, get_unread_count, mark_as_read,
    mark_all_as_read, delete_notification, clear_all_notifications,
    notify_change_proposed, notify_change_approved, notify_change_rejected,
    notify_new_user,
)

# app.py — SwytchAI Flask Web Application
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from functools import wraps
from users import (
    load_user_database, save_user_database, hash_password,
    verify_password, ROLES, get_permissions
)
from config_manager import pull_config, show_versions, load_version_log, compare_configs
from config_pusher import (
    push_config as netmiko_push_config, get_current_config
)
from ai_assistant import parse_request, collect_params, generate_config, TEMPLATES
from devices import all_devices, cisco_switch
from napalm_engine import create_device, SUPPORTED_VENDORS
from datetime import datetime
import os
import json

# ============================================================
# FLASK APP SETUP
# ============================================================
app = Flask(__name__)
init_db()
init_mail(app)
start_scheduler(app)
app.secret_key = os.getenv("SWYTCHAI_SECRET_KEY", "swytchai-dev-key-change-in-production")
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
from datetime import timedelta
app.permanent_session_lifetime = timedelta(minutes=30)
app.register_blueprint(api)
@app.context_processor
def inject_globals():
    """Makes unread_count and branding available in all templates."""
    if "username" in session:
        org_id = session.get("org_id", 0)
        branding = db_get_branding(org_id) if org_id else {}
        return {
            "unread_count": db_get_unread_count(session["username"]),
            "brand": branding
        }
    return {"unread_count": 0, "brand": {}}


# ============================================================
# LOGIN REQUIRED DECORATOR
# ============================================================
def login_required(f):
    """Decorator that redirects to login if user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access SwytchAI.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission):
    """Decorator that checks if user has a specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username = session.get("username")
            if not username:
                return redirect(url_for("login"))
            permissions = get_permissions(username)
            if permission not in permissions:
                flash(f"Access denied. You don't have '{permission}' permission.", "danger")
                return redirect(url_for("onboarding"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# AUTH ROUTES
# ============================================================
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = db_get_user(username)
        if not user:
            flash("User not found!", "danger")
            return render_template("login.html")
        if not verify_password(password, user["password_hash"]):
            flash("Incorrect password!", "danger")
            return render_template("login.html")
        # Check if 2FA is enabled
        if user.get("totp_secret"):
            session["pending_2fa_user"] = username
            return redirect(url_for("verify_2fa"))

        session.permanent = True
        session["username"] = username
        session["name"] = user["name"]
        session["role"] = user["role"]
        session["site"] = user["site"]
        if user.get("org_id"):
            org = db_get_org(user["org_id"])
            if org:
                session["org_id"] = org["org_id"]
                session["org_name"] = org["org_name"]
        flash(f"Welcome back, {user['name']}!", "success")
        log_action(username, "LOGIN", "User logged in")
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    name = session.get("name", "")
    log_action(session.get("username", ""), "LOGOUT", "User logged out")
    session.clear()
    flash(f"Goodbye, {name}! You've been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/onboarding")
@login_required
def onboarding():
    return render_template("onboarding.html")

@app.route("/help")
@login_required
def help_page():
    return render_template("help.html")

# ============================================================
# DASHBOARD
# ============================================================
@app.route("/dashboard")
@login_required
def dashboard():
    import json
    org_id = session.get("org_id", 0)
    stats = db_get_dashboard_stats(org_id)
    if not stats:
        stats = {
            "total_devices": 0,
            "total_users": 0,
            "total_backups": 0,
            "change_counts": {"pending": 0, "approved": 0, "rejected": 0},
            "recent_activity": [],
            "activity_7_days": {},
            "actions_by_type": {}
        }
    return render_template("dashboard.html",
        stats=stats,
        stats_json=json.dumps(stats)
    )


# ============================================================
# DEVICES
# ============================================================
@app.route("/devices")
@login_required
@permission_required("pull_config")
def devices():
    org_id = session.get("org_id", 0)
    org_devices = db_get_org_devices(org_id)
    return render_template("devices.html", devices=org_devices)

@app.route("/devices/<int:device_id>/facts")
@login_required
@permission_required("pull_config")
def device_facts(device_id):
    org_id = session.get("org_id", 0)
    device_record = db_get_device(device_id, org_id)
    if not device_record:
        flash("Device not found!", "danger")
        return redirect(url_for("devices"))
    dd = {
        "host": device_record["host"],
        "username": device_record["username"],
        "password": device_record["password"],
        "vendor": device_record["vendor"],
    }
    facts = None
    error = None
    try:
        dev = create_device(dd)
        dev.connect()
        facts = dev.get_facts()
        dev.disconnect()
    except Exception as e:
        error = str(e)
    return render_template("device_facts.html", device=device_record, facts=facts, error=error, device_id=device_id)

@app.route("/devices/<int:device_id>/interfaces")
@login_required
@permission_required("pull_config")
def device_interfaces(device_id):
    org_id = session.get("org_id", 0)
    device_record = db_get_device(device_id, org_id)
    if not device_record:
        flash("Device not found!", "danger")
        return redirect(url_for("devices"))
    dd = {
        "host": device_record["host"],
        "username": device_record["username"],
        "password": device_record["password"],
        "vendor": device_record["vendor"],
    }
    interfaces = None
    error = None
    try:
        dev = create_device(dd)
        dev.connect()
        interfaces = dev.get_interfaces()
        dev.disconnect()
    except Exception as e:
        error = str(e)
    return render_template("device_interfaces.html", device=device_record, interfaces=interfaces, error=error, device_id=device_id)

@app.route("/devices/<int:device_id>/pull")
@login_required
@permission_required("pull_config")
def pull_device_config(device_id):
    org_id = session.get("org_id", 0)
    device_record = db_get_device(device_id, org_id)
    if not device_record:
        flash("Device not found!", "danger")
        return redirect(url_for("devices"))
    dd = {
        "host": device_record["host"],
        "username": device_record["username"],
        "password": device_record["password"],
        "device_type": device_record["vendor"],
    }
    try:
        filename = pull_config(dd)
        flash(f"Config pulled successfully! Saved to {filename}", "success")
        log_action(session["username"], "PULL_CONFIG", "Pulled config", device_record["host"])
    except Exception as e:
        flash(f"Failed to pull config: {e}", "danger")
    return redirect(url_for("devices"))

# ============================================================
# CONFIG VERSIONS
# ============================================================
@app.route("/configs")
@login_required
@permission_required("view_versions")
def configs():
    # Get version logs for all devices
    device_configs = []
    for device in all_devices:
        host = device["host"]
        log = load_version_log(host)
        device_configs.append({
            "host": host,
            "vendor": device.get("vendor", "unknown"),
            "versions": log.get("versions", []),
        })

    return render_template("configs.html", device_configs=device_configs)


@app.route("/configs/<path:host>/version/<int:version>")
@login_required
@permission_required("view_versions")
def view_config(host, version):
    filepath = f"saved_configs/{host}/v{version}.txt"
    config_text = ""

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            config_text = f.read()

    return render_template(
        "view_config.html",
        host=host,
        version=version,
        config_text=config_text,
    )


@app.route("/configs/<path:host>/diff/<int:v1>/<int:v2>")
@login_required
@permission_required("compare_configs")
def diff_configs(host, v1, v2):
    import difflib

    file_a = f"saved_configs/{host}/v{v1}.txt"
    file_b = f"saved_configs/{host}/v{v2}.txt"

    config_a = ""
    config_b = ""

    if os.path.exists(file_a):
        with open(file_a, "r") as f:
            config_a = f.readlines()
    if os.path.exists(file_b):
        with open(file_b, "r") as f:
            config_b = f.readlines()

    diff = list(difflib.unified_diff(
        config_a, config_b,
        fromfile=f"v{v1}", tofile=f"v{v2}",
        lineterm=""
    ))

    return render_template(
        "diff.html",
        host=host,
        v1=v1,
        v2=v2,
        diff=diff,
    )

@app.route("/devices/<int:device_id>/health")
@login_required
def device_health(device_id):
    import json
    org_id = session.get("org_id", 0)
    device = db_get_device(device_id, org_id)
    if not device or device.get("org_id") != org_id:
        flash("Device not found.", "danger")
        return redirect(url_for("devices_page"))
    
    device_dict = {
        "hostname": device["hostname"],
        "host": device["host"],
        "username": device["username"],
        "password": device["password"],
        "vendor": device["vendor"]
    }
    health = check_device_health(device_dict)
    conn2 = get_db()
    cursor2 = conn2.execute("SELECT * FROM device_tags WHERE device_id = ? AND org_id = ?", (device_id, session.get("org_id")))
    tags = [{"tag_id": row[0], "device_id": row[1], "tag": row[2]} for row in cursor2.fetchall()]
    conn2.close()
    return render_template("device_health.html", device=device, health=health, health_json=json.dumps(health), tags=tags)

@app.route("/api/health-check")
@login_required
def api_health_check():
    import json
    org_id = session.get("org_id", 0)
    devices = db_get_org_devices(org_id)
    results = []
    for device in devices:
        device_dict = {
            "hostname": device["hostname"],
            "host": device["host"],
            "username": device["username"],
            "password": device["password"],
            "vendor": device["vendor"]
        }
        health = check_device_health(device_dict)
        health["device_id"] = device["device_id"]
        results.append(health)
    return json.dumps(results), 200, {"Content-Type": "application/json"}


# ============================================================
# CHANGE WORKFLOW
# ============================================================
@app.route("/changes")
@login_required
@permission_required("view_history")
def changes():
    changes = db_get_changes()
    return render_template("changes.html", changes=changes)


@app.route("/changes/propose", methods=["GET", "POST"])
@login_required
@permission_required("propose_change")
def propose_change_web():
    if request.method == "POST":
        config_text = request.form.get("config_lines", "").strip()
        description = sanitize_input(request.form.get("description", "").strip())
        if not config_text:
            flash("Config lines cannot be empty!", "danger")
            return render_template("propose_change.html", devices=all_devices)
        config_lines = config_text.split("\n")
        proposer_name = session.get("name", "Unknown")
        change_id = db_create_change(cisco_switch["host"], description, config_lines, proposer_name)
        change_record = {"change_id": change_id, "host": cisco_switch["host"], "description": description, "config_lines": config_lines, "proposed_by": proposer_name}
        flash(f"Change #{change_id} proposed successfully!", "success")
        notify_change_proposed(change_record, proposer_name)
        log_action(session["username"], "PROPOSE_CHANGE", f"Change #{change_id}: {description}", cisco_switch["host"])
        print(f"[EMAIL TRIGGER] Change #{change_id} proposed — email would be sent to approvers")
        return redirect(url_for("changes"))
    return render_template("propose_change.html", devices=all_devices)

@app.route("/changes/<int:change_id>/approve", methods=["POST"])
@login_required
@permission_required("approve_change")
def approve_change(change_id):
    change = db_get_change(change_id)

    if not change or change["status"] != "PENDING":
        flash(f"Change #{change_id} not found or not pending.", "warning")
        return redirect(url_for("changes"))

    reviewer_name = session.get("name", "Unknown")

    try:
        rollback = get_current_config(cisco_switch)
    except Exception:
        rollback = None

    try:
        success = netmiko_push_config(cisco_switch, change["config_lines"])
        if success:
            db_update_change_status(change_id, "APPROVED & PUSHED", reviewer_name, rollback)
            flash(f"Change #{change_id} approved and pushed!", "success")
            notify_change_approved(change, reviewer_name)
            log_action(session["username"], "APPROVE_CHANGE", f"Approved change #{change_id}", change["host"])
            print(f"[EMAIL TRIGGER] Change #{change_id} approved — email would be sent to proposer")
        else:
            db_update_change_status(change_id, "PUSH FAILED", reviewer_name)
            flash(f"Change #{change_id} push failed!", "danger")
    except Exception as e:
        db_update_change_status(change_id, "PUSH FAILED", reviewer_name)
        flash(f"Push failed: {e}", "danger")

    return redirect(url_for("changes"))

@app.route("/changes/<int:change_id>/reject", methods=["POST"])
@login_required
@permission_required("approve_change")
def reject_change(change_id):
    change = db_get_change(change_id)

    if not change or change["status"] != "PENDING":
        flash(f"Change #{change_id} not found or not pending.", "warning")
        return redirect(url_for("changes"))

    reviewer_name = session.get("name", "Unknown")

    db_update_change_status(change_id, "REJECTED", reviewer_name)
    flash(f"Change #{change_id} rejected.", "warning")
    notify_change_rejected(change, reviewer_name)
    log_action(session["username"], "REJECT_CHANGE", f"Rejected change #{change_id}", change["host"])
    print(f"[EMAIL TRIGGER] Change #{change_id} rejected — email would be sent to proposer")
    return redirect(url_for("changes"))

# ============================================================
# AI ASSISTANT
# ============================================================
@app.route("/ai")
@login_required
@permission_required("propose_change")
def ai_assistant_page():
    commands = []
    for name, template in TEMPLATES.items():
        commands.append({
            "name": name,
            "description": template["description"],
            "keywords": template.get("keywords", [])[:3],
            "params": template.get("params", []),
        })
    return render_template("ai_assistant.html", commands=commands)


@app.route("/ai/generate", methods=["POST"])
@login_required
@permission_required("propose_change")
def ai_generate():
    data = request.get_json()
    user_input = data.get("input", "")
    vendor = data.get("vendor", "cisco_ios")
    params = data.get("params", {})

    # Parse the request
    template_name = parse_request(user_input)

    if not template_name:
        return jsonify({
            "success": False,
            "message": f"I'm not sure what you mean by '{user_input}'. Try 'help' to see available commands."
        })

    template = TEMPLATES[template_name]

    # If params weren't provided, ask for them
    if not params and template.get("params", []):
        return jsonify({
            "success": True,
            "needs_params": True,
            "template_name": template_name,
            "description": template["description"],
            "params_needed": template.get("params", []),
        })

    # Generate the config
    config_lines = generate_config(template_name, vendor, params)

    if not config_lines:
        return jsonify({
            "success": False,
            "message": f"Template '{template_name}' doesn't support vendor '{vendor}' yet."
        })

    return jsonify({
        "success": True,
        "needs_params": False,
        "template_name": template_name,
        "description": template["description"],
        "config_lines": config_lines,
        "vendor": vendor,
    })


# ============================================================
# USER MANAGEMENT
# ============================================================
@app.route("/users")
@login_required
@permission_required("manage_users")
def users_page():
    users_list = db_get_all_users()
    return render_template("users.html", users=users_list, roles=ROLES)
    
@app.route("/users/add", methods=["POST"])
@login_required
@permission_required("manage_users")
def add_user_web():
    if request.method == "POST":
        # Check user limit
        org_id = session.get("org_id", 0)
        conn = get_db()
        user_count = conn.execute("SELECT COUNT(*) FROM users WHERE org_id = ?", (org_id,)).fetchone()
        org = conn.execute("SELECT subscription_plan FROM organizations WHERE org_id = ?", (org_id,)).fetchone()
        plan_name = org if org else "free_trial"
        allowed, msg = check_user_limit(plan_name, user_count)
        if not allowed:
            flash(msg, "error")
            return redirect(url_for("admin_panel"))
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        site = request.form.get("site", "").strip()
        existing = db_get_user(username)
    if existing:
        flash(f"User '{username}' already exists!", "danger")
        return redirect(url_for("users_page"))

    temp_password = "temp_" + username + "[PASSWORD]"

    db_create_user(username, name, role, site, hash_password(temp_password))

    flash(f"User '{username}' created! Temp password: {temp_password}", "success")
    log_action(session["username"], "USER_CREATED", f"Created user: {username} ({role})", username)
    return redirect(url_for("users_page"))

@app.route("/notifications")
@login_required
def notifications_page():
    notifications = db_get_notifications(session["username"])
    return render_template("notifications.html", notifications=notifications)

@app.route("/notifications/<int:notification_id>/read")
@login_required
def read_notification(notification_id):
    db_mark_notification_read(notification_id)
    return redirect(url_for("notifications_page"))

@app.route("/notifications/read-all")
@login_required
def mark_all_read():
    db_mark_all_notifications_read(session["username"])
    return redirect(url_for("notifications_page"))

@app.route("/notifications/<int:notification_id>/delete")
@login_required
def delete_notif(notification_id):
    db_delete_notification(notification_id)
    return redirect(url_for("notifications_page"))

@app.route("/notifications/clear")
@login_required
def clear_notifications():
    db_clear_notifications(session["username"])
    return redirect(url_for("notifications_page"))

@app.route("/audit")
@login_required
@permission_required("view_history")
def audit_page():
    filter_user = request.args.get("user", "")
    filter_action = request.args.get("action", "")
    entries = db_get_audit_entries(username=filter_user if filter_user else None, action=filter_action if filter_action else None)
    return render_template("audit.html", entries=entries, users_in_log=db_get_all_users_in_log(), all_actions=db_get_all_actions(), filter_user=filter_user, filter_action=filter_action)

# ============================================================
# RUN THE APP
# ============================================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        org_name = request.form.get("org_name", "").strip()
        plan = request.form.get("plan", "starter")
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not org_name or not username or not name or not email or not password:
            flash("All fields are required!", "danger")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match!", "danger")
            return render_template("signup.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters!", "danger")
            return render_template("signup.html")
        existing = db_get_user(username)
        if existing:
            flash("Username already taken!", "danger")
            return render_template("signup.html")
        slug = org_name.lower().replace(" ", "-").replace(".", "")
        existing_org = db_get_org_by_slug(slug)
        if existing_org:
            flash("Organization name already taken!", "danger")
            return render_template("signup.html")
        success = db_create_user(username, name, "admin", "", hash_password(password), email=email)
        if not success:
            flash("Failed to create account!", "danger")
            return render_template("signup.html")
        org_id = db_create_org(org_name, slug, username, plan)
        if not org_id:
            flash("Failed to create organization!", "danger")
            return render_template("signup.html")
        flash("Welcome to SwytchAI! Your 14-day free trial has started.", "success")
        session.permanent = True
        session["username"] = username
        session["name"] = name
        session["role"] = "admin"
        session["org_id"] = org_id
        session["org_name"] = org_name
        log_action(username, "SIGNUP", f"Created organization: {org_name} ({plan} plan)")
        email_welcome(email, name, org_name)
        return redirect(url_for("dashboard"))
    return render_template("signup.html")
@app.route("/devices/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_devices")
def add_device_web():
     if request.method == "POST":
        # Check device limit
        org_id = session.get("org_id", 0)
        conn = get_db()
        device_count = conn.execute("SELECT COUNT(*) FROM devices WHERE org_id = ?", (org_id,)).fetchone()
        org = conn.execute("SELECT subscription_plan FROM organizations WHERE org_id = ?", (org_id,)).fetchone()
        plan_name = org if org else "free_trial"
        allowed, msg = check_device_limit(plan_name, device_count)
        if not allowed:
            flash(msg, "error")
            return redirect(url_for("devices"))
        org_id = session.get("org_id", 0)
        org = db_get_org_billing(org_id) or {}
        plan = org.get("plan", "starter")
        current_devices = len(db_get_org_devices(org_id))
        allowed, msg = check_device_limit(plan, current_devices)
        if not allowed:
            flash(msg, "danger")
            return redirect(url_for("devices"))
        hostname = request.form.get("hostname", "").strip()
        host = request.form.get("host", "").strip()
        vendor = request.form.get("vendor", "ios")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not hostname or not host or not username or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for("add_device_web"))
        db_add_device(org_id, hostname, host, vendor, username, password, session.get("username"))
        flash(f"Device '{hostname}' added!", "success")
        log_action(session["username"], "ADD_DEVICE", f"Added device: {hostname}")
        return redirect(url_for("devices"))
        return render_template("add_device.html")
@app.route("/devices/<int:device_id>/delete", methods=["POST"])
@login_required
@permission_required("manage_users")
def remove_device(device_id):
    org_id = session.get("org_id", 0)
    device = db_get_device(device_id, org_id)
    if not device:
        flash("Device not found!", "danger")
        return redirect(url_for("devices"))
    db_delete_device(device_id, org_id)
    flash(f"Device '{device['hostname']}' deleted!", "success")
    log_action(session["username"], "DELETE_DEVICE", f"Deleted device: {device['hostname']}")
    return redirect(url_for("devices"))

# ============================================================
# ADMIN PANEL
# ============================================================
@app.route("/admin")
@login_required
@permission_required("manage_users")
def admin_panel():
    org_id = session.get("org_id", 0)
    org = db_get_org(org_id) if org_id else None
    team_members = db_get_org_members(org_id)
    device_count = len(db_get_org_devices(org_id))
    return render_template("admin.html", org=org, team_members=team_members, device_count=device_count)

@app.route("/admin/invite", methods=["POST"])
@login_required
@permission_required("manage_users")
def invite_member():
    username = request.form.get("username", "").strip().lower()
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "technician")
    password = request.form.get("password", "")
    org_id = session.get("org_id", 0)
    org = db_get_org_billing(org_id) or {}
    plan = org.get("plan", "starter")
    current_users = len(db_get_org_members(org_id))
    allowed, msg = check_user_limit(plan, current_users)
    if not allowed:
        flash(msg, "danger")
        return redirect(url_for("admin_panel"))
    if not username or not name or not password:
        flash("All fields are required!", "danger")
        return redirect(url_for("admin_panel"))
    if len(password) < 8:
        flash("Password must be at least 8 characters!", "danger")
        return redirect(url_for("admin_panel"))
    existing = db_get_user(username)
    if existing:
        flash(f"Username '{username}' already taken!", "danger")
        return redirect(url_for("admin_panel"))
    db_create_user(username, name, role, "", hash_password(password), org_id)
    flash(f"'{name}' added as {role}!", "success")
    log_action(session["username"], "INVITE_MEMBER", f"Added {username} as {role}")
    email_team_invite("", name, session.get("org_name", ""), session.get("name", ""))
    return redirect(url_for("admin_panel"))

@app.route("/admin/role", methods=["POST"])
@login_required
@permission_required("manage_users")
def change_member_role():
    username = request.form.get("username", "")
    new_role = request.form.get("role", "technician")
    user = db_get_user(username)
    if not user or user.get("org_id") != session.get("org_id"):
        flash("User not found in your organization!", "danger")
        return redirect(url_for("admin_panel"))
    db_update_user_role(username, new_role)
    flash(f"'{username}' role changed to {new_role}!", "success")
    log_action(session["username"], "CHANGE_ROLE", f"Changed {username} to {new_role}")
    return redirect(url_for("admin_panel"))

@app.route("/admin/remove", methods=["POST"])
@login_required
@permission_required("manage_users")
def remove_member():
    username = request.form.get("username", "")
    user = db_get_user(username)
    if not user or user.get("org_id") != session.get("org_id"):
        flash("User not found in your organization!", "danger")
        return redirect(url_for("admin_panel"))
    if username == session.get("username"):
        flash("You can't remove yourself!", "danger")
        return redirect(url_for("admin_panel"))
    db_remove_user_from_org(username)
    flash(f"'{username}' removed from your organization.", "warning")
    log_action(session["username"], "REMOVE_MEMBER", f"Removed {username}")
    return redirect(url_for("admin_panel"))
# ============================================================
# CONTACT SALES (Enterprise)
# ============================================================
@app.route("/contact-sales", methods=["GET", "POST"])
def contact_sales():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        company = request.form.get("company", "").strip()
        job_title = request.form.get("job_title", "").strip()
        team_size = request.form.get("team_size", "")
        device_count = request.form.get("device_count", "")
        vendors = ", ".join(request.form.getlist("vendors"))
        message = request.form.get("message", "").strip()

        # Log the inquiry
        log_action("system", "ENTERPRISE_INQUIRY", f"From: {first_name} {last_name} ({email}) at {company} - Team: {team_size}, Devices: {device_count}, Vendors: {vendors}")

        # Send email notification to you
        try:
            from email_service import send_email
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a1929; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
                <h1 style="color: #b388ff;">🏢 New Enterprise Inquiry</h1>
                <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <p><strong>Name:</strong> {first_name} {last_name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Company:</strong> {company}</p>
                    <p><strong>Job Title:</strong> {job_title}</p>
                    <p><strong>Team Size:</strong> {team_size}</p>
                    <p><strong>Devices:</strong> {device_count}</p>
                    <p><strong>Vendors:</strong> {vendors}</p>
                    <p><strong>Message:</strong> {message or 'No message provided'}</p>
                </div>
                <p style="color: #78909c;">Reply directly to this lead at <a href="mailto:{email}" style="color: #00e5ff;">{email}</a></p>
            </div>
            """
            send_email(os.getenv("MAIL_USERNAME", ""), f"SwytchAI Enterprise Inquiry — {company}", body)
        except Exception as e:
            print(f"[CONTACT SALES EMAIL ERROR] {e}")

        print(f"[ENTERPRISE LEAD] {first_name} {last_name} | {email} | {company} | Team: {team_size} | Devices: {device_count} | Vendors: {vendors}")
        return render_template("contact_thanks.html")
    return render_template("contact_sales.html")

# ====# ============================================================
# PASSWORD RESET
# ============================================================
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()

        user = db_get_user(username)
        if user and user.get("email", "").lower() == email and email != "":
            # Generate token
            token = secrets.token_urlsafe(32)
            db_create_reset_token(token, username)

            # Build reset link
            reset_link = request.host_url + "reset-password/" + token

            # Try to send email
            try:
                from email_service import send_email
                body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a1929; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
                    <h1 style="color: #00e5ff;">Password Reset Request</h1>
                    <p>Hi {user['name']},</p>
                    <p>We received a request to reset your [PASSWORD] password. Click the button below to set a new password:</p>
                    <div style="text-align: center; margin: 2rem 0;">
                        <a href="{reset_link}" style="background: linear-gradient(135deg, #00e5ff, #00b8d4); color: #0a1929; padding: 0.75rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 700;">Reset Password</a>
                    </div>
                    <p style="color: #78909c; font-size: 0.85rem;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
                    <p style="color: #78909c; font-size: 0.85rem;">Reset link: {reset_link}</p>
                </div>
                """
                send_email(email, "[PASSWORD] — Password Reset", body)
                print(f"[PASSWORD RESET] Email sent to {email} for user {username}")
                print(f"[PASSWORD RESET LINK] {reset_link}")

            except Exception as e:
                print(f"[PASSWORD RESET] Email failed: {e}")
                print(f"[PASSWORD RESET] Manual reset link: {reset_link}")

            log_action("system", "PASSWORD_RESET_REQUEST", f"Reset requested for {username}")

        # Always show success message (don't reveal if user exists)
        flash("If that username and email match our records, a reset link has been sent.", "info")
        return redirect(url_for("forgot_password"))
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset = db_get_reset_token(token)

    if not reset:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("login"))

    # Check if token is older than 1 hour
    created = datetime.fromisoformat(reset["created_at"])
    if datetime.utcnow() - created > timedelta(hours=1):
        flash("This reset link has expired. Please request a new one.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("reset_password.html", token=token)

        # Update password
        from users import hash_password
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(password), reset["username"]))
        conn.commit()
        conn.close()

        # Mark token as used
        db_use_reset_token(token)

        log_action(reset["username"], "PASSWORD_RESET", "Password was reset via email link")
        flash("Password reset successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)

# ADMIN PASSWORD RESET
@app.route("/admin/reset-password", methods=["POST"])
@login_required
@permission_required("manage_users")
def admin_reset_password():
    username = request.form.get("username", "").strip().lower()
    new_password = request.form.get("new_password", "")

    if len(new_password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for("admin_panel"))

    user = db_get_user(username)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin_panel"))

    from users import hash_password
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(new_password), username))
    conn.commit()
    conn.close()

    log_action(session["username"], "ADMIN_RESET_PASSWORD", f"Reset password for {username}")
    flash(f"Password reset for {username}.", "success")
    return redirect(url_for("admin_panel"))

# ========================================================
# LEGAL PAGES
# ============================================================
@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/acceptable-use")
def acceptable_use():
    return render_template("acceptable_use.html")
# ============================================================
# BILLING
# ============================================================
@app.route("/billing")
@login_required
@permission_required("manage_users")
def billing_page():
    org_id = session.get("org_id", 0)
    billing = db_get_org_billing(org_id) or {}
    current_plan_key = billing.get("plan", "starter")
    current_plan = PLANS.get(current_plan_key, PLANS["starter"])
    return render_template("billing.html", billing=billing, plans=PLANS, current_plan=current_plan, current_plan_key=current_plan_key)

@app.route("/billing/subscribe", methods=["POST"])
@login_required
@permission_required("manage_users")
def subscribe():
    plan_key = request.form.get("plan", "starter")
    org_id = session.get("org_id", 0)
    username = session.get("username", "")
    success_url = request.host_url + "billing/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.host_url + "billing"
    checkout_session = create_checkout_session(plan_key, org_id, username, success_url, cancel_url)
    if checkout_session:
        return redirect(checkout_session.url)
    flash("Error creating checkout session. Please try again.", "danger")
    return redirect(url_for("billing_page"))

@app.route("/billing/success")
@login_required
def billing_success():
    import stripe as stripe_module
    session_id = request.args.get("session_id")
    if session_id:
        try:
            checkout = stripe_module.checkout.Session.retrieve(session_id)
            org_id = session.get("org_id", 0)
            metadata = checkout.metadata.to_dict() if hasattr(checkout.metadata, 'to_dict') else dict(checkout.metadata)
            plan_key = metadata.get("plan", "starter")
            db_update_org_stripe(org_id, checkout.customer, checkout.subscription)
            db_update_org_plan(org_id, plan_key, "active")
            flash(f"Successfully subscribed to {PLANS[plan_key]['name']}!", "success")
            log_action(session.get("username", ""), "SUBSCRIBE", f"Subscribed to {plan_key} plan")
        except Exception as e:
            flash(f"Error confirming subscription: {e}", "danger")
    return redirect(url_for("billing_page"))

@app.route("/billing/manage", methods=["GET","POST"])
@login_required
@permission_required("manage_users")
def manage_billing():
    org_id = session.get("org_id", 0)
    org = db_get_org(org_id)
    current_plan = org.get("subscription_plan", "free") if org else "free"
    return render_template("manage_subscription.html", current_plan=current_plan, plans=PLANS)
@permission_required("manage_users")
@app.route("/billing/change-plan", methods=["POST"])
@login_required
def change_plan():
    new_plan = request.form.get("new_plan", "").strip().lower()
    print(f"DEBUG: new_plan = '{new_plan}', PLANS keys = {list(PLANS.keys())}")
    org_id = session.get("org_id", 0)
    username = session.get("username", "")

    if new_plan == "enterprise":
        return redirect(url_for("contact_sales"))

    plan = PLANS.get(new_plan)
    if not plan or not plan.get("price_id"):
        flash("Invalid plan selected.", "error")
        return redirect(url_for("manage_billing"))

    # Send to Stripe checkout for payment
    try:
        session_obj = create_checkout_session(
            new_plan,
            org_id,
            username,
            success_url=request.host_url + "billing/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.host_url + "billing"
        )
        if session_obj:
            return redirect(session_obj.url)
        else:
            flash("Error connecting to payment. Please try again.", "error")
            return redirect(url_for("manage_billing"))
    except Exception as e:
        print(f"Stripe upgrade error: {e}")
        flash("Error processing upgrade. Please try again.", "error")
        return redirect(url_for("manage_billing"))

@app.route("/billing/cancel", methods=["POST"])
@login_required
@permission_required("manage_users")
def cancel_subscription():
    import sqlite3
    org_id = session.get("org_id", 0)
    conn = sqlite3.connect("swytchai.db")
    conn.execute("UPDATE organizations SET subscription_plan = 'free' WHERE org_id = ?", (org_id,))
    conn.commit()
    conn.close()
    flash("Subscription cancelled. Your account will remain active until the end of your billing period.", "warning")
    db_log_action(session.get("username", "unknown"), "cancel_subscription", "Cancelled subscription")
    return redirect(url_for("manage_billing"))


# ============================================================
# SCHEDULED BACKUPS
# ============================================================
@app.route("/backups")
@login_required
@permission_required("pull_config")
def backups_page():
    import sqlite3
    org_id = session.get("org_id", 0)
    conn = sqlite3.connect("swytchai.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM config_backups WHERE org_id = ? ORDER BY created_at DESC LIMIT 50", (org_id,))
    backups = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template("backups.html", backups=backups)

@app.route("/backups/run-now", methods=["POST"])
@login_required
@permission_required("manage_devices")
def run_backup_now_route():
    results = run_backup_now(app)
    if results["failed"] > 0:
        flash(f"Backup complete: {results['success']} success, {results['failed']} failed", "warning")
    else:
        flash(f"Backup complete: {results['success']} devices backed up!", "success")
    log_action(session["username"], "MANUAL_BACKUP", f"Manual backup: {results['success']} success, {results['failed']} failed")
    return redirect(url_for("backups_page"))

@app.route("/backups/<int:backup_id>/view")
@login_required
@permission_required("pull_config")
def view_backup(backup_id):
    import sqlite3
    org_id = session.get("org_id", 0)
    conn = sqlite3.connect("swytchai.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM config_backups WHERE backup_id = ? AND org_id = ?", (backup_id, org_id))
    backup = cursor.fetchone()
    conn.close()
    if not backup:
        flash("Backup not found.", "danger")
        return redirect(url_for("backups_page"))
    return render_template("view_backup.html", backup=dict(backup))

@app.route("/backups/<int:backup_id>/download")
@login_required
@permission_required("pull_config")
def download_backup(backup_id):
    import sqlite3
    from flask import Response
    org_id = session.get("org_id", 0)
    conn = sqlite3.connect("swytchai.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM config_backups WHERE backup_id = ? AND org_id = ?", (backup_id, org_id))
    backup = cursor.fetchone()
    conn.close()
    if not backup:
        flash("Backup not found.", "danger")
        return redirect(url_for("backups_page"))
    backup = dict(backup)
    filename = f"{backup['hostname']}_{backup['created_at'][:10]}.txt"
    return Response(
        backup["config_text"],
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/backups/export-all")
@login_required
@permission_required("manage_devices")
def export_all_backups():
    import sqlite3, io, zipfile
    from flask import Response
    org_id = session.get("org_id", 0)
    conn = sqlite3.connect("swytchai.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM config_backups WHERE org_id = ? AND status = 'success' ORDER BY created_at DESC", (org_id,))
    backups = [dict(row) for row in cursor.fetchall()]
    conn.close()
    if not backups:
        flash("No backups to export.", "warning")
        return redirect(url_for("backups_page"))
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for backup in backups:
            filename = f"{backup['hostname']}/{backup['created_at'][:19].replace(':', '-')}.txt"
            zf.writestr(filename, backup["config_text"])
    zip_buffer.seek(0)
    from datetime import datetime
    export_name = f"swytchai_backups_{datetime.utcnow().strftime('%Y%m%d')}.zip"
    log_action(session["username"], "EXPORT_BACKUPS", f"Exported {len(backups)} backups as ZIP")
    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={export_name}"}
    )

# ============================================================
# BACKUP SETTINGS
# ============================================================
@app.route("/backups/settings", methods=["GET", "POST"])
@login_required
@permission_required("manage_devices")
def backup_settings():
    org_id = session.get("org_id", 0)

    if request.method == "POST":
        enabled = 1 if request.form.get("enabled") else 0
        frequency = request.form.get("frequency", "daily")
        hour = int(request.form.get("backup_hour", 2))
        minute = int(request.form.get("backup_minute", 0))
        retention = int(request.form.get("retention_days", 30))
        notify_success = 1 if request.form.get("notify_on_success") else 0
        notify_fail = 1 if request.form.get("notify_on_failure") else 0

        db_save_backup_settings(org_id, enabled, frequency, hour, minute, retention, notify_success, notify_fail, session.get("username"))

        if enabled:
            schedule_org_backup(app, org_id, frequency, hour, minute)
        flash("Backup settings saved!", "success")
        log_action(session["username"], "BACKUP_SETTINGS", f"Updated: {frequency} at {hour:02d}:{minute:02d}, retention {retention} days")
        return redirect(url_for("backup_settings"))

    settings = db_get_backup_settings(org_id)
    return render_template("backup_settings.html", settings=settings)

# ============================================================
# WHITE-LABEL BRANDING
# ============================================================
@app.route("/admin/branding", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def branding_settings():
    org_id = session.get("org_id", 0)

    if request.method == "POST":
        data = {
            "company_name": request.form.get("company_name", "").strip(),
            "logo_url": request.form.get("logo_url", "").strip(),
            "primary_color": request.form.get("primary_color", "#00e5ff"),
            "secondary_color": request.form.get("secondary_color", "#b388ff"),
            "accent_color": request.form.get("accent_color", "#69f0ae"),
            "background_color": request.form.get("background_color", "#0a1929"),
            "card_color": request.form.get("card_color", "#112240"),
            "sidebar_color": request.form.get("sidebar_color", "#0d1117"),
            "custom_css": request.form.get("custom_css", "").strip(),
        }
        db_save_branding(org_id, data, session.get("username"))
        flash("Branding saved! Refresh to see changes.", "success")
        log_action(session["username"], "UPDATE_BRANDING", f"Updated branding: {data['company_name']}")
        return redirect(url_for("branding_settings"))

    branding = db_get_branding(org_id)
    return render_template("branding.html", branding=branding)

# ============================================================
# BULK OPERATIONS
# ============================================================
@app.route("/devices/bulk", methods=["GET", "POST"])
@login_required
@permission_required("pull_config")
def bulk_operations():
    org_id = session.get("org_id", 0)
    devices = db_get_org_devices(org_id)

    if request.method == "POST":
        selected_ids = request.form.getlist("device_ids")
        action = request.form.get("action", "")
        results = []

        for did in selected_ids:
            device = db_get_device(int(did), org_id)
            if not device:
                continue

            device_dict = {
                "hostname": device["hostname"],
                "host": device["host"],
                "vendor": device["vendor"],
                "username": device["username"],
                "password": device["password"]
            }

            if action == "pull_config":
                try:
                    from napalm_engine import create_device
                    dev = create_device(device_dict)
                    dev.connect()
                    config = dev.get_config()
                    dev.disconnect()
                    results.append({"device": device["hostname"], "status": "success", "message": "Config pulled successfully"})
                    log_action(session["username"], "BULK_PULL_CONFIG", f"Pulled config from {device['hostname']}")
                except Exception as e:
                    results.append({"device": device["hostname"], "status": "error", "message": str(e)})

            elif action == "health_check":
                try:
                    from napalm_engine import create_device
                    dev = create_device(device_dict)
                    dev.connect()
                    facts = dev.get_facts()
                    dev.disconnect()
                    results.append({"device": device["hostname"], "status": "success", "message": f"Online — {facts.get('model', 'Unknown')}"})
                    log_action(session["username"], "BULK_HEALTH_CHECK", f"Health check on {device['hostname']}")
                except Exception as e:
                    results.append({"device": device["hostname"], "status": "error", "message": str(e)})

            elif action == "backup":
                try:
                    from napalm_engine import create_device
                    dev = create_device(device_dict)
                    dev.connect()
                    config = dev.get_config()
                    dev.disconnect()
                    results.append({"device": device["hostname"], "status": "success", "message": "Backup saved"})
                    log_action(session["username"], "BULK_BACKUP", f"Backed up {device['hostname']}")
                except Exception as e:
                    results.append({"device": device["hostname"], "status": "error", "message": str(e)})

        return render_template("bulk_operations.html", devices=devices, results=results, selected_action=action)

    return render_template("bulk_operations.html", devices=devices, results=None, selected_action="")

# ============================================================
# CONFIG TEMPLATES
# ============================================================
TEMPLATES = {
    "vlan": {
        "name": "Create VLAN",
        "icon": "🏷️",
        "description": "Create a new VLAN with name and ID",
        "fields": ["vlan_id", "vlan_name"],
        "labels": {"vlan_id": "VLAN ID (1-4094)", "vlan_name": "VLAN Name"},
        "placeholders": {"vlan_id": "e.g. 200", "vlan_name": "e.g. Engineering"},
        "generate": lambda d: f"vlan {d['vlan_id']}\n name {d['vlan_name']}\n no shutdown"
    },
    "acl": {
        "name": "Access Control List",
        "icon": "🔒",
        "description": "Create a standard or extended ACL",
        "fields": ["acl_number", "action", "source_ip", "wildcard"],
        "labels": {"acl_number": "ACL Number", "action": "Action", "source_ip": "Source IP", "wildcard": "Wildcard Mask"},
        "placeholders": {"acl_number": "e.g. 100", "action": "permit or deny", "source_ip": "e.g. 192.168.1.0", "wildcard": "e.g. 0.0.0.255"},
        "generate": lambda d: f"access-list {d['acl_number']} {d['action']} {d['source_ip']} {d['wildcard']}"
    },
    "snmp": {
        "name": "SNMP Community",
        "icon": "📡",
        "description": "Configure SNMP community string for monitoring",
        "fields": ["community", "permission"],
        "labels": {"community": "Community String", "permission": "Permission"},
        "placeholders": {"community": "e.g. MyCompany_RO", "permission": "RO or RW"},
        "generate": lambda d: f"snmp-server community {d['community']} {d['permission']}"
    },
    "interface": {
        "name": "Interface Config",
        "icon": "🔌",
        "description": "Configure an interface with IP and description",
        "fields": ["interface", "ip_address", "subnet_mask", "description"],
        "labels": {"interface": "Interface", "ip_address": "IP Address", "subnet_mask": "Subnet Mask", "description": "Description"},
        "placeholders": {"interface": "e.g. GigabitEthernet0/1", "ip_address": "e.g. 10.0.1.1", "subnet_mask": "e.g. 255.255.255.0", "description": "e.g. Uplink to Core"},
        "generate": lambda d: f"interface {d['interface']}\n description {d['description']}\n ip address {d['ip_address']} {d['subnet_mask']}\n no shutdown"
    },
    "static_route": {
        "name": "Static Route",
        "icon": "🛤️",
        "description": "Add a static route to the routing table",
        "fields": ["network", "mask", "next_hop"],
        "labels": {"network": "Destination Network", "mask": "Subnet Mask", "next_hop": "Next Hop IP"},
        "placeholders": {"network": "e.g. 10.10.0.0", "mask": "e.g. 255.255.0.0", "next_hop": "e.g. 192.168.1.1"},
        "generate": lambda d: f"ip route {d['network']} {d['mask']} {d['next_hop']}"
    },
    "ntp": {
        "name": "NTP Server",
        "icon": "🕐",
        "description": "Configure NTP server for time synchronization",
        "fields": ["ntp_server"],
        "labels": {"ntp_server": "NTP Server IP"},
        "placeholders": {"ntp_server": "e.g. [IP_ADDRESS]"},
        "generate": lambda d: f"ntp server {d['ntp_server']}"
    },
    "banner": {
        "name": "Login Banner",
        "icon": "📢",
        "description": "Set a login banner message for the device",
        "fields": ["banner_text"],
        "labels": {"banner_text": "Banner Message"},
        "placeholders": {"banner_text": "e.g. Unauthorized access is prohibited"},
        "generate": lambda d: f"banner motd # {d['banner_text']} #"
    },
    "syslog": {
        "name": "Syslog Server",
        "icon": "📝",
        "description": "Configure remote syslog server for logging",
        "fields": ["syslog_server", "log_level"],
        "labels": {"syslog_server": "Syslog Server IP", "log_level": "Log Level (0-7)"},
        "placeholders": {"syslog_server": "e.g. 10.0.0.50", "log_level": "e.g. 6"},
        "generate": lambda d: f"logging host {d['syslog_server']}\nlogging trap {d['log_level']}"
    }
}

@app.route("/templates")
@login_required
def config_templates():
    return render_template("config_templates.html", templates=TEMPLATES)

@app.route("/templates/<template_id>", methods=["GET", "POST"])
@login_required
def use_template(template_id):
    if template_id not in TEMPLATES:
        flash("Template not found.", "error")
        return redirect(url_for("config_templates"))

    template = TEMPLATES[template_id]

    if request.method == "POST":
        data = {}
        for field in template["fields"]:
            val = request.form.get(field, "").strip()
            if not val:
                flash(f"Please fill in all fields.", "error")
                return render_template("use_template.html", template=template, template_id=template_id, config=None)
            data[field] = sanitize_input(val)

        config = template["generate"](data)
        log_action(session["username"], "TEMPLATE_USED", f"Used template: {template['name']}")
        return render_template("use_template.html", template=template, template_id=template_id, config=config)

    return render_template("use_template.html", template=template, template_id=template_id, config=None)

# ============================================================
# COMPLIANCE CHECKING
# ============================================================
@app.route("/compliance")
@login_required
def compliance_page():
    org_id = session.get("org_id", 0)
    devices = db_get_org_devices(org_id)
    return render_template("compliance.html", devices=devices, rules=COMPLIANCE_RULES, report=None)

@app.route("/compliance/scan", methods=["POST"])
@login_required
def compliance_scan():
    org_id = session.get("org_id", 0)
    devices = db_get_org_devices(org_id)
    device_id = request.form.get("device_id", "")
    selected_rules = request.form.getlist("rules")

    if not device_id:
        flash("Please select a device.", "error")
        return redirect(url_for("compliance_page"))

    device = db_get_device(int(device_id), org_id)
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for("compliance_page"))

    # Try to pull live config
    try:
        from napalm_engine import create_device
        device_dict = {
            "hostname": device["hostname"],
            "host": device["host"],
            "vendor": device["vendor"],
            "username": device["username"],
            "password": device["password"]
        }
        dev = create_device(device_dict)
        dev.connect()
        config = dev.get_config()
        dev.disconnect()
        config_text = config.get("running", "")
    except Exception:
        # Fallback: use last saved config if available
        config_text = ""

    if not config_text:
        flash("Could not retrieve config. Add a sample config to test.", "error")
        return redirect(url_for("compliance_page"))

    report = run_compliance_check(config_text, selected_rules if selected_rules else None)
    report["device"] = device["hostname"]
    log_action(session["username"], "COMPLIANCE_SCAN", f"Scanned {device['hostname']} — Score: {report['score']}%")
    session["last_compliance_report"] = report

    return render_template("compliance.html", devices=devices, rules=COMPLIANCE_RULES, report=report)

@app.route("/compliance/demo", methods=["POST"])
@login_required
def compliance_demo():
    org_id = session.get("org_id", 0)
    devices = db_get_org_devices(org_id)

    sample_config = """
hostname CoreSwitch01
service password-encryption
enable secret 5 $1$abc$xyz
ip ssh version 2
banner motd # Authorized Access Only #
line vty 0 4
 transport input ssh
ntp server pool.ntp.org
logging host 10.0.0.50
logging trap informational
"""
    report = run_compliance_check(sample_config)
    report["device"] = "Demo — Sample Config"
    log_action(session["username"], "COMPLIANCE_DEMO", f"Ran demo compliance scan — Score: {report['score']}%")
    session["last_compliance_report"] = report

    return render_template("compliance.html", devices=devices, rules=COMPLIANCE_RULES, report=report)

# ============================================================
# REPORTS & PDF EXPORT
# ============================================================
@app.route("/reports")
@login_required
def reports_page():
    return render_template("reports.html")

@app.route("/reports/compliance-pdf", methods=["POST"])
@login_required
def download_compliance_pdf():
    report_data = session.get("last_compliance_report")
    if not report_data:
        flash("No compliance report found. Run a scan first.", "error")
        return redirect(url_for("compliance_page"))

    org = db_get_org(session.get("org_id", 0))
    org_name = org["org_name"] if org else "SwytchAI"

    pdf_buffer = generate_compliance_pdf(report_data, org_name)
    log_action(session["username"], "REPORT_DOWNLOAD", "Downloaded compliance PDF report")

    from flask import send_file
    return send_file(pdf_buffer, as_attachment=True, download_name=f"SwytchAI_Compliance_Report_{datetime.now().strftime('%Y%m%d')}.pdf", mimetype="application/pdf")

@app.route("/reports/devices-pdf")
@login_required
def download_devices_pdf():
    org_id = session.get("org_id", 0)
    devices = db_get_org_devices(org_id)
    org = db_get_org(org_id)
    org_name = org["org_name"] if org else "SwytchAI"

    pdf_buffer = generate_device_report_pdf(devices, org_name)
    log_action(session["username"], "REPORT_DOWNLOAD", "Downloaded device inventory PDF report")

    from flask import send_file
    return send_file(pdf_buffer, as_attachment=True, download_name=f"SwytchAI_Device_Report_{datetime.now().strftime('%Y%m%d')}.pdf", mimetype="application/pdf")

# ============================================================
# TWO-FACTOR AUTHENTICATION (2FA)
# ============================================================
@app.route("/settings/2fa", methods=["GET"])
@login_required
def setup_2fa():
    username = session["username"]
    user = db_get_user(username)
    has_2fa = bool(user.get("totp_secret"))
    return render_template("setup_2fa.html", has_2fa=has_2fa)

@app.route("/settings/2fa/enable", methods=["POST"])
@login_required
def enable_2fa():
    username = session["username"]
    secret = pyotp.random_base32()

    # Save secret to database
    conn = get_db()
    conn.execute("UPDATE users SET totp_secret = ? WHERE username = ?", (secret, username))
    conn.commit()
    conn.close()

    # Generate QR code
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=username, issuer_name="SwytchAI")

    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    log_action(username, "2FA_ENABLED", "Enabled two-factor authentication")
    return render_template("setup_2fa.html", has_2fa=True, qr_code=qr_b64, secret=secret, just_enabled=True)

@app.route("/settings/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    username = session["username"]
    conn = get_db()
    conn.execute("UPDATE users SET totp_secret = NULL WHERE username = ?", (username,))
    conn.commit()
    conn.close()

    log_action(username, "2FA_DISABLED", "Disabled two-factor authentication")
    flash("2FA has been disabled.", "info")
    return redirect(url_for("setup_2fa"))

@app.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    if "pending_2fa_user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        username = session["pending_2fa_user"]
        user = db_get_user(username)

        if not user or not user.get("totp_secret"):
            flash("2FA error. Please try logging in again.", "error")
            session.pop("pending_2fa_user", None)
            return redirect(url_for("login"))

            # Check if 2FA is enabled
            if user.get("totp_secret"):
                session["pending_2fa_user"] = user["username"]
                return redirect(url_for("verify_2fa"))

            session["username"] = user["username"]
            session["role"] = user["role"]
            session["org_id"] = user.get("org_id", 0)
            session["name"] = user.get("name", "")

        totp = pyotp.TOTP(user["totp_secret"])
        if totp.verify(code, valid_window=1):
            session.pop("pending_2fa_user", None)
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["org_id"] = user.get("org_id", 0)
            session["name"] = user.get("name", "")
            log_action(username, "LOGIN_2FA", "Logged in with 2FA verification")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid code. Please try again.", "error")

    return render_template("verify_2fa.html")

@app.route("/activity")
@login_required
def activity_dashboard():
    org_id = session.get("org_id")
    if not org_id:
        flash("No organization found.", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    # Team member activity (last 30 days)
    cursor.execute("""
        SELECT username, action, COUNT(*) as count
        FROM audit_log
        WHERE timestamp > datetime('now', '-30 days')
        GROUP BY username, action
        ORDER BY count DESC
    """)
    member_actions = {}
    for row in cursor.fetchall():
        user = row[0]
        if user not in member_actions:
            member_actions[user] = {"total": 0, "actions": {}}
        member_actions[user]["actions"][row[1]] = row[2]
        member_actions[user]["total"] += row[2]

    # Daily activity trend (last 30 days)
    cursor.execute("""
        SELECT DATE(timestamp) as day, COUNT(*) as count
        FROM audit_log
        WHERE timestamp > datetime('now', '-30 days')
        GROUP BY day ORDER BY day
    """)
    daily_trend = {row[0]: row[1] for row in cursor.fetchall()}

    # Top actions
    cursor.execute("""
        SELECT action, COUNT(*) as count
        FROM audit_log
        WHERE timestamp > datetime('now', '-30 days')
        GROUP BY action ORDER BY count DESC LIMIT 10
    """)
    top_actions = {row[0]: row[1] for row in cursor.fetchall()}

    # Recent activity feed
    cursor.execute("""
        SELECT username, action, details, target, timestamp
        FROM audit_log
        ORDER BY timestamp DESC LIMIT 50
    """)
    recent = [{"username": r[0], "action": r[1], "details": r[2], "target": r[3], "timestamp": r[4]} for r in cursor.fetchall()]

    # Config change stats
    cursor.execute("SELECT status, COUNT(*) FROM changes GROUP BY status")
    change_stats = {row[0].lower(): row[1] for row in cursor.fetchall()}

    # Most active hours
    cursor.execute("""
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
        FROM audit_log
        WHERE timestamp > datetime('now', '-30 days')
        GROUP BY hour ORDER BY hour
    """)
    hourly_activity = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return render_template("activity.html",
        member_actions=member_actions,
        daily_trend=daily_trend,
        top_actions=top_actions,
        recent=recent,
        change_stats=change_stats,
        hourly_activity=hourly_activity
    )

@app.route("/webhooks", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def webhook_settings():
    org_id = session.get("org_id")
    if not org_id:
        flash("No organization found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        platform = request.form.get("platform", "")
        url = request.form.get("webhook_url", "").strip()
        push = 1 if request.form.get("notify_push") else 0
        approve = 1 if request.form.get("notify_approve") else 0
        reject = 1 if request.form.get("notify_reject") else 0
        backup_fail = 1 if request.form.get("notify_backup") else 0
        new_user = 1 if request.form.get("notify_user") else 0

        db_save_webhook_settings(org_id, platform, url, push, approve, reject, backup_fail, new_user, session["username"])
        log_action(session["username"], "WEBHOOK_UPDATE", f"Updated webhook settings: {platform}")
        flash("Webhook settings saved!", "success")

    settings = db_get_webhook_settings(org_id)
    return render_template("webhooks.html", settings=settings)

@app.route("/webhooks/test", methods=["POST"])
@login_required
@permission_required("manage_users")
def test_webhook():
    org_id = session.get("org_id")
    settings = db_get_webhook_settings(org_id)
    if settings["webhook_url"]:
        success = notify_config_change(settings["webhook_url"], settings["platform"], session["username"], "TEST", details="This is a test notification from SwytchAI!")
        if success:
            flash("Test notification sent!", "success")
        else:
            flash("Failed to send. Check your webhook URL.", "danger")
    else:
        flash("No webhook URL configured.", "warning")
    return redirect(url_for("webhook_settings"))

@app.route("/api/docs")
def api_docs():
    return render_template("api_docs.html")

@app.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return render_template("search.html", query="", results={})

    org_id = session.get("org_id")
    conn = get_db()
    results = {}

    # Search devices
    cursor = conn.execute("SELECT * FROM devices WHERE org_id = ?", (org_id,))
    cols = [desc[0] for desc in cursor.description]
    devices = [dict(zip(cols, row)) for row in cursor.fetchall()]
    matched_devices = [d for d in devices if query in str(d.get("hostname","")).lower() or query in str(d.get("host","")).lower() or query in str(d.get("vendor","")).lower()]
    if matched_devices:
        results["devices"] = matched_devices

    # Search changes
    cursor = conn.execute("SELECT * FROM changes")
    cols = [desc[0] for desc in cursor.description]
    changes = [dict(zip(cols, row)) for row in cursor.fetchall()]
    matched_changes = [c for c in changes if query in str(c.get("description","")).lower() or query in str(c.get("host","")).lower() or query in str(c.get("proposed_by","")).lower() or query in str(c.get("config_lines","")).lower()]
    if matched_changes:
        results["changes"] = matched_changes

    # Search audit log
    cursor = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 200")
    cols = [desc[0] for desc in cursor.description]
    logs = [dict(zip(cols, row)) for row in cursor.fetchall()]
    matched_logs = [l for l in logs if query in str(l.get("username","")).lower() or query in str(l.get("action","")).lower() or query in str(l.get("details","")).lower() or query in str(l.get("target","")).lower()]
    if matched_logs:
        results["audit"] = matched_logs[:20]

    # Search users (admin only)
    if session.get("role") in ["admin", "org_admin"]:
        cursor = conn.execute("SELECT * FROM users WHERE org_id = ?", (org_id,))
        cols = [desc[0] for desc in cursor.description]
        users = [dict(zip(cols, row)) for row in cursor.fetchall()]
        matched_users = [u for u in users if query in str(u.get("username","")).lower() or query in str(u.get("name","")).lower() or query in str(u.get("email","")).lower()]
        if matched_users:
            results["users"] = matched_users

    conn.close()
    return render_template("search.html", query=query, results=results)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = db_get_user(session["username"])
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_info":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            if name and email:
                conn = get_db()
                conn.execute("UPDATE users SET name = ?, email = ? WHERE username = ?", (name, email, session["username"]))
                conn.commit()
                conn.close()
                session["name"] = name
                log_action(session["username"], "PROFILE_UPDATE", "Updated name and email")
                flash("Profile updated!", "success")

        elif action == "change_password":
            current = request.form.get("current_password", "")
            new_pass = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not bcrypt.checkpw(current.encode("utf-8"), user["password_hash"].encode("utf-8")):
                flash("Current password is incorrect.", "danger")
            elif new_pass != confirm:
                flash("New passwords don't match.", "danger")
            elif len(new_pass) < 8:
                flash("Password must be at least 8 characters.", "danger")
            else:
                hashed = bcrypt.hashpw(new_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                conn = get_db()
                conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed, session["username"]))
                conn.commit()
                conn.close()
                log_action(session["username"], "PASSWORD_CHANGE", "Changed password via profile")
                flash("Password changed!", "success")

        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)

@app.route("/audit/export")
@login_required
@permission_required("manage_users")
def export_audit():
    import csv
    conn = get_db()
    cursor = conn.execute("SELECT username, action, details, target, timestamp FROM audit_log ORDER BY timestamp DESC")
    cols = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    for row in rows:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=swytchai_audit_log.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route("/devices/<int:device_id>/tags", methods=["POST"])
@login_required
def add_device_tag(device_id):
    tag = request.form.get("tag", "").strip().lower()
    org_id = session.get("org_id")
    if tag:
        conn = get_db()
        conn.execute("INSERT INTO device_tags (device_id, tag, org_id) VALUES (?, ?, ?)", (device_id, tag, org_id))
        conn.commit()
        conn.close()
        log_action(session["username"], "TAG_ADDED", f"Added tag '{tag}' to device {device_id}")
        flash(f"Tag '{tag}' added!", "success")
    return redirect(url_for("device_facts", device_id=device_id))

@app.route("/devices/<int:device_id>/tags/<int:tag_id>/delete", methods=["POST"])
@login_required
def delete_device_tag(device_id, tag_id):
    org_id = session.get("org_id")
    conn = get_db()
    conn.execute("DELETE FROM device_tags WHERE tag_id = ? AND org_id = ?", (tag_id, org_id))
    conn.commit()
    conn.close()
    log_action(session["username"], "TAG_REMOVED", f"Removed tag from device {device_id}")
    flash("Tag removed!", "success")
    return redirect(url_for("device_facts", device_id=device_id))

@app.route("/devices/filter")
@login_required
def filter_devices_by_tag():
    tag = request.args.get("tag", "").strip().lower()
    org_id = session.get("org_id")
    conn = get_db()

    cursor = conn.execute("""
        SELECT DISTINCT d.* FROM devices d
        JOIN device_tags dt ON d.device_id = dt.device_id
        WHERE dt.tag = ? AND d.org_id = ?
    """, (tag, org_id))
    cols = [desc[0] for desc in cursor.description]
    devices = [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Get all tags for this org
    cursor = conn.execute("SELECT DISTINCT tag FROM device_tags WHERE org_id = ?", (org_id,))
    all_tags = [row[0] for row in cursor.fetchall()]
    conn.close()

    return render_template("devices_filtered.html", devices=devices, tag=tag, all_tags=all_tags)

@app.route("/devices/<int:device_id>/unifi")
@login_required
def unifi_dashboard(device_id):
    org_id = session.get("org_id")
    conn = get_db()
    cursor = conn.execute("SELECT * FROM devices WHERE device_id = ? AND org_id = ?", (device_id, org_id))
    cols = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash("Device not found.", "danger")
        return redirect(url_for("devices"))
    device = dict(zip(cols, row))

    try:
        from unifi_engine import connect_unifi
        unifi = connect_unifi(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=int(device.get("port", 8443))
        )
        summary = unifi.get_device_summary()
        networks = unifi.get_networks()
        alarms = unifi.get_alarms()
        unifi.logout()
        return render_template("unifi_dashboard.html", device=device, summary=summary, networks=networks, alarms=alarms)
    except Exception as e:
        flash(f"UniFi connection error: {e}", "danger")
        return redirect(url_for("devices"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)



