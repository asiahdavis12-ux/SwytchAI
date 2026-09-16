
# database.py — SwytchAI SQLite Database
import sqlite3
import os
from datetime import datetime

DATABASE_FILE = "swytchai.db"


def get_db():
    """Creates a connection to the database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # This lets us access columns by name
    return conn


def init_db():
  

    conn = get_db()
    cursor = conn.cursor()

    # ── USERS TABLE ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            site TEXT,
            password_hash TEXT,
            org_id INTEGER,
            email TEXT,
            totp_secret TEXT
        )
    ''')

    # — CHANGES TABLE —

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS changes (
            change_id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT NOT NULL,
            description TEXT NOT NULL,
            config_lines TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            proposed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            proposed_by TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by TEXT,
            pushed_at TEXT,
            rollback_config TEXT
        )
    ''')

    # ── NOTIFICATIONS TABLE ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            link TEXT,
            read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── AUDIT LOG TABLE ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            target TEXT DEFAULT '',
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── API KEYS TABLE ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            label TEXT DEFAULT 'default',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL
        )
    ''')

    # ── ORGANIZATIONS TABLE ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            org_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            owner_username TEXT NOT NULL,
            plan TEXT DEFAULT 'starter',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            trial_ends_at TEXT,
            subscription_status TEXT DEFAULT 'trialing',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')


    # ── UPDATE USERS TABLE — add org_id column if not exists ──
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN org_id INTEGER DEFAULT NULL")
    except Exception:
        pass

    # ── INVITATIONS TABLE ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            role TEXT DEFAULT 'technician',
            invite_code TEXT UNIQUE NOT NULL,
            accepted INTEGER DEFAULT 0,
            invited_by TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # ── DEVICES TABLE ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            hostname TEXT NOT NULL,
            host TEXT NOT NULL,
            vendor TEXT DEFAULT 'cisco_ios',
            username TEXT,
            password TEXT,
            added_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_resets (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    ''')

    # Add email column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
    except:
        pass  # Column already exists

    cursor.execute('''CREATE TABLE IF NOT EXISTS config_backups (
        backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER,
        org_id INTEGER,
        hostname TEXT,
        config_text TEXT,
        backup_type TEXT DEFAULT 'scheduled',
        status TEXT DEFAULT 'success',
        error_message TEXT DEFAULT '',
        created_at TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS backup_settings (
        org_id INTEGER PRIMARY KEY,
        enabled INTEGER DEFAULT 1,
        frequency TEXT DEFAULT 'daily',
        backup_hour INTEGER DEFAULT 2,
        backup_minute INTEGER DEFAULT 0,
        retention_days INTEGER DEFAULT 30,
        notify_on_success INTEGER DEFAULT 1,
        notify_on_failure INTEGER DEFAULT 1,
        updated_at TEXT,
        updated_by TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS branding (
        org_id INTEGER PRIMARY KEY,
        company_name TEXT DEFAULT '',
        logo_url TEXT DEFAULT '',
        primary_color TEXT DEFAULT '#00e5ff',
        secondary_color TEXT DEFAULT '#b388ff',
        accent_color TEXT DEFAULT '#69f0ae',
        background_color TEXT DEFAULT '#0a1929',
        card_color TEXT DEFAULT '#112240',
        sidebar_color TEXT DEFAULT '#0d1117',
        custom_css TEXT DEFAULT '',
        updated_at TEXT,
        updated_by TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS webhook_settings (
        org_id INTEGER PRIMARY KEY,
        platform TEXT DEFAULT '',
        webhook_url TEXT DEFAULT '',
        notify_config_push INTEGER DEFAULT 1,
        notify_config_approve INTEGER DEFAULT 1,
        notify_config_reject INTEGER DEFAULT 1,
        notify_backup_fail INTEGER DEFAULT 1,
        notify_new_user INTEGER DEFAULT 1,
        updated_at TEXT,
        updated_by TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS device_tags (
        tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER,
        tag TEXT,
        org_id INTEGER
    )''')

    conn.commit()
    conn.close()
    print("  ✅ Database initialized: swytchai.db")


# ============================================================
# USER FUNCTIONS
# ============================================================

def db_get_user(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {"username": row[0], "name": row[1], "role": row[2], "site": row[3], "password_hash": row[4], "org_id": row[5], "email": row[6], "totp_secret": row[7]}


def db_get_all_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
    conn.close()
    return [dict(u) for u in users]


def db_create_user(username, name, role, site, password_hash, org_id=None, email=""):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, name, role, site, password_hash, org_id, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, name, role, site, password_hash, org_id, email)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False
    finally:
        conn.close()


def db_delete_user(username):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def db_update_user_email(username, email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = ? WHERE username = ?", (email, username))
    conn.commit()
    conn.close()

# ============================================================
# CHANGES FUNCTIONS
# ============================================================
def db_get_changes(status=None):
    conn = get_db()
    if status:
        changes = conn.execute(
            "SELECT * FROM changes WHERE status LIKE ? ORDER BY change_id DESC",
            (f"%{status}%",),
        ).fetchall()
    else:
        changes = conn.execute("SELECT * FROM changes ORDER BY change_id DESC").fetchall()
    conn.close()
    result = []
    for c in changes:
        change = dict(c)
        change["config_lines"] = change["config_lines"].split("\n")
        result.append(change)
    return result


def db_get_change(change_id):
    conn = get_db()
    change = conn.execute("SELECT * FROM changes WHERE change_id = ?", (change_id,)).fetchone()
    conn.close()
    if change:
        change = dict(change)
        change["config_lines"] = change["config_lines"].split("\n")
        return change
    return None


def db_create_change(host, description, config_lines, proposed_by):
    conn = get_db()
    config_text = "\n".join(config_lines) if isinstance(config_lines, list) else config_lines
    cursor = conn.execute(
        "INSERT INTO changes (host, description, config_lines, proposed_by) VALUES (?, ?, ?, ?)",
        (host, description, config_text, proposed_by),
    )
    conn.commit()
    change_id = cursor.lastrowid
    conn.close()
    return change_id


def db_update_change_status(change_id, status, reviewed_by=None, rollback_config=None):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE changes SET status = ?, reviewed_at = ?, reviewed_by = ?, pushed_at = ? WHERE change_id = ?",
        (status, now, reviewed_by, now if "PUSHED" in status else None, change_id),
    )
    if rollback_config:
        conn.execute(
            "UPDATE changes SET rollback_config = ? WHERE change_id = ?",
            (rollback_config, change_id),
        )
    conn.commit()
    conn.close()


# ============================================================
# NOTIFICATION FUNCTIONS
# ============================================================
def db_create_notification(recipient, title, message, notif_type="info", link=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO notifications (recipient, title, message, type, link) VALUES (?, ?, ?, ?, ?)",
        (recipient, title, message, notif_type, link),
    )
    conn.commit()
    conn.close()


def db_get_notifications(username):
    conn = get_db()
    notifs = conn.execute(
        "SELECT * FROM notifications WHERE recipient = ? ORDER BY created_at DESC",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(n) for n in notifs]


def db_get_unread_count(username):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE recipient = ? AND read = 0",
        (username,),
    ).fetchone()[0]
    conn.close()
    return count


def db_mark_notification_read(notification_id):
    conn = get_db()
    conn.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()


def db_mark_all_notifications_read(username):
    conn = get_db()
    conn.execute("UPDATE notifications SET read = 1 WHERE recipient = ?", (username,))
    conn.commit()
    conn.close()


def db_delete_notification(notification_id):
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()


def db_clear_notifications(username):
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE recipient = ?", (username,))
    conn.commit()
    conn.close()


# ============================================================
# AUDIT FUNCTIONS
# ============================================================
def db_log_action(username, action, details="", target=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (username, action, details, target) VALUES (?, ?, ?, ?)",
        (username, action, details, target),
    )
    conn.commit()
    conn.close()


def db_get_audit_entries(username=None, action=None, limit=100):
    conn = get_db()
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []

    if username:
        query += " AND username = ?"
        params.append(username)
    if action:
        query += " AND action = ?"
        params.append(action)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    entries = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(e) for e in entries]


def db_get_all_actions():
    conn = get_db()
    actions = conn.execute("SELECT DISTINCT action FROM audit_log ORDER BY action").fetchall()
    conn.close()
    return [a["action"] for a in actions]


def db_get_all_users_in_log():
    conn = get_db()
    users = conn.execute("SELECT DISTINCT username FROM audit_log ORDER BY username").fetchall()
    conn.close()
    return [u["username"] for u in users]


# ============================================================
# API KEY FUNCTIONS
# ============================================================
def db_get_api_key(key):
    conn = get_db()
    record = conn.execute("SELECT * FROM api_keys WHERE key = ? AND active = 1", (key,)).fetchone()
    conn.close()
    if record:
        return dict(record)
    return None


def db_create_api_key(key, username, role, label, created_by):
    conn = get_db()
    conn.execute(
        "INSERT INTO api_keys (key, username, role, label, created_by) VALUES (?, ?, ?, ?, ?)",
        (key, username, role, label, created_by),
    )
    conn.commit()
    conn.close()


# ============================================================
# INITIALIZE ON IMPORT
# ============================================================

# ============================================================
# ORGANIZATION FUNCTIONS
# ============================================================
def db_create_org(org_name, slug, owner_username, plan="starter"):
    """Creates a new organization."""
    conn = get_db()
    plan_limits = {"starter": (5, 10), "professional": (25, 50), "enterprise": (999, 999)}
    max_users, max_devices = plan_limits.get(plan, (5, 10))

    from datetime import datetime, timedelta
    trial_end = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor = conn.execute(
            "INSERT INTO organizations (org_name, slug, owner_username, plan, max_users, max_devices, trial_ends_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (org_name, slug, owner_username, plan, max_users, max_devices, trial_end),
        )
        org_id = cursor.lastrowid
        conn.execute("UPDATE users SET org_id = ? WHERE username = ?", (org_id, owner_username))
        conn.commit()
        conn.close()
        return org_id
    except Exception:
        conn.close()
        return None


def db_get_org(org_id):
    """Gets an organization by ID."""
    conn = get_db()
    org = conn.execute("SELECT * FROM organizations WHERE org_id = ?", (org_id,)).fetchone()
    conn.close()
    if org:
        return dict(org)
    return None


def db_get_org_by_slug(slug):
    """Gets an organization by slug."""
    conn = get_db()
    org = conn.execute("SELECT * FROM organizations WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    if org:
        return dict(org)
    return None


def db_get_org_users(org_id):
    """Gets all users in an organization."""
    conn = get_db()
    users = conn.execute("SELECT * FROM users WHERE org_id = ? ORDER BY username", (org_id,)).fetchall()
    conn.close()
    return [dict(u) for u in users]


def db_get_org_user_count(org_id):
    """Gets the number of users in an organization."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users WHERE org_id = ?", (org_id,)).fetchone()[0]
    conn.close()
    return count


def db_update_org_plan(org_id, plan):
    """Updates an organization's plan and limits."""
    plan_limits = {"starter": (5, 10), "professional": (25, 50), "enterprise": (999, 999)}
    max_users, max_devices = plan_limits.get(plan, (5, 10))
    conn = get_db()
    conn.execute(
        "UPDATE organizations SET plan = ?, max_users = ?, max_devices = ? WHERE org_id = ?",
        (plan, max_users, max_devices, org_id),
    )
    conn.commit()
    conn.close()


def db_create_invitation(org_id, email, role, invite_code, invited_by):
    """Creates an invitation for a new team member."""
    conn = get_db()
    conn.execute(
        "INSERT INTO invitations (org_id, email, role, invite_code, invited_by) VALUES (?, ?, ?, ?, ?)",
        (org_id, email, role, invite_code, invited_by),
    )
    conn.commit()
    conn.close()


def db_get_invitation(invite_code):
    """Gets an invitation by code."""
    conn = get_db()
    inv = conn.execute("SELECT * FROM invitations WHERE invite_code = ? AND accepted = 0", (invite_code,)).fetchone()
    conn.close()
    if inv:
        return dict(inv)
    return None


def db_accept_invitation(invite_code):
    """Marks an invitation as accepted."""
    conn = get_db()
    conn.execute("UPDATE invitations SET accepted = 1 WHERE invite_code = ?", (invite_code,))
    conn.commit()
    conn.close()


def db_get_org_invitations(org_id):
    """Gets all pending invitations for an organization."""
    conn = get_db()
    invs = conn.execute("SELECT * FROM invitations WHERE org_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()
    conn.close()
    return [dict(i) for i in invs]
# ============================================================
# DEVICE FUNCTIONS (ORG-SCOPED)
# ============================================================
def db_add_device(org_id, hostname, host, vendor, username, password, added_by):
    """Adds a device to an organization."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO devices (org_id, hostname, host, vendor, username, password, added_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (org_id, hostname, host, vendor, username, password, added_by),
    )
    device_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return device_id


def db_get_org_devices(org_id):
    """Gets all devices for an organization."""
    conn = get_db()
    devices = conn.execute("SELECT * FROM devices WHERE org_id = ? ORDER BY hostname", (org_id,)).fetchall()
    conn.close()
    return [dict(d) for d in devices]


def db_get_device(device_id, org_id):
    """Gets a single device — only if it belongs to the org."""
    conn = get_db()
    device = conn.execute("SELECT * FROM devices WHERE device_id = ? AND org_id = ?", (device_id, org_id)).fetchone()
    conn.close()
    if device:
        return dict(device)
    return None


def db_delete_device(device_id, org_id):
    """Deletes a device — only if it belongs to the org."""
    conn = get_db()
    conn.execute("DELETE FROM devices WHERE device_id = ? AND org_id = ?", (device_id, org_id))
    conn.commit()
    conn.close()
# ============================================================
# TEAM MANAGEMENT FUNCTIONS
# ============================================================
def db_get_org_members(org_id):
    """Gets all users belonging to an organization."""
    conn = get_db()
    members = conn.execute("SELECT * FROM users WHERE org_id = ? ORDER BY name", (org_id,)).fetchall()
    conn.close()
    return [dict(m) for m in members]

def db_update_user_role(username, new_role):
    """Updates a user's role."""
    conn = get_db()
    conn.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
    conn.commit()
    conn.close()

def db_remove_user_from_org(username):
    """Removes a user from their organization."""
    conn = get_db()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
# ============================================================
# BILLING FUNCTIONS
# ============================================================
def db_update_org_stripe(org_id, stripe_customer_id, stripe_subscription_id):
    """Links Stripe customer and subscription to an org."""
    conn = get_db()
    conn.execute(
        "UPDATE organizations SET stripe_customer_id = ?, stripe_subscription_id = ? WHERE org_id = ?",
        (stripe_customer_id, stripe_subscription_id, org_id),
    )
    conn.commit()
    conn.close()

def db_update_org_plan(org_id, plan, subscription_status="active"):
    """Updates the org's plan and subscription status."""
    conn = get_db()
    conn.execute(
        "UPDATE organizations SET plan = ?, subscription_status = ? WHERE org_id = ?",
        (plan, subscription_status, org_id),
    )
    conn.commit()
    conn.close()

def db_get_org_billing(org_id):
    """Gets billing info for an org."""
    conn = get_db()
    org = conn.execute(
        "SELECT org_id, org_name, plan, stripe_customer_id, stripe_subscription_id, trial_ends_at, subscription_status, created_at FROM organizations WHERE org_id = ?",
        (org_id,),
    ).fetchone()
    conn.close()
    if org:
        return dict(org)
    return None
def db_get_webhook_settings(org_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM webhook_settings WHERE org_id = ?", (org_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"org_id": org_id, "platform": "", "webhook_url": "", "notify_config_push": 1, "notify_config_approve": 1, "notify_config_reject": 1, "notify_backup_fail": 1, "notify_new_user": 1}

def db_save_webhook_settings(org_id, platform, url, push, approve, reject, backup_fail, new_user, username):
    from datetime import datetime
    conn = get_db()
    conn.execute("""INSERT OR REPLACE INTO webhook_settings
        (org_id, platform, webhook_url, notify_config_push, notify_config_approve, notify_config_reject, notify_backup_fail, notify_new_user, updated_at, updated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (org_id, platform, url, push, approve, reject, backup_fail, new_user, datetime.utcnow().isoformat(), username))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("  Database setup complete!")

def db_create_reset_token(token, username):
    conn = get_db()
    cursor = conn.cursor()
    from datetime import datetime
    cursor.execute(
        "INSERT INTO password_resets (token, username, created_at) VALUES (?, ?, ?)",
        (token, username, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def db_get_reset_token(token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM password_resets WHERE token = ? AND used = 0", (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {"token": row[0], "username": row[1], "created_at": row[2], "used": row[3]}

def db_use_reset_token(token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def db_get_dashboard_stats(org_id):
    conn = get_db()
    cursor = conn.cursor()

def db_get_backup_settings(org_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backup_settings WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        cols = ["org_id", "enabled", "frequency", "backup_hour", "backup_minute", "retention_days", "notify_on_success", "notify_on_failure", "updated_at", "updated_by"]
        return dict(zip(cols, row))
    return {"org_id": org_id, "enabled": 1, "frequency": "daily", "backup_hour": 2, "backup_minute": 0, "retention_days": 30, "notify_on_success": 1, "notify_on_failure": 1}

def db_save_backup_settings(org_id, enabled, frequency, hour, minute, retention, notify_success, notify_fail, username):
    from datetime import datetime
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT OR REPLACE INTO backup_settings
        (org_id, enabled, frequency, backup_hour, backup_minute, retention_days, notify_on_success, notify_on_failure, updated_at, updated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (org_id, enabled, frequency, hour, minute, retention, notify_success, notify_fail, datetime.utcnow().isoformat(), username))
    conn.commit()

    conn.close()

def db_get_branding(org_id):
    conn = sqlite3.connect("swytchai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM branding WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        cols = ["org_id", "company_name", "logo_url", "primary_color", "secondary_color", "accent_color", "background_color", "card_color", "sidebar_color", "custom_css", "updated_at", "updated_by"]
        return dict(zip(cols, row))
    return {
        "org_id": org_id, "company_name": "", "logo_url": "",
        "primary_color": "#00e5ff", "secondary_color": "#b388ff",
        "accent_color": "#69f0ae", "background_color": "#0a1929",
        "card_color": "#112240", "sidebar_color": "#0d1117",
        "custom_css": ""
    }

def db_save_branding(org_id, data, username):
    from datetime import datetime
    conn = sqlite3.connect("swytchai.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT OR REPLACE INTO branding
        (org_id, company_name, logo_url, primary_color, secondary_color, accent_color, background_color, card_color, sidebar_color, custom_css, updated_at, updated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (org_id, data["company_name"], data["logo_url"], data["primary_color"], data["secondary_color"], data["accent_color"], data["background_color"], data["card_color"], data["sidebar_color"], data["custom_css"], datetime.utcnow().isoformat(), username))
    conn.commit()
    conn.close()

def db_get_dashboard_stats(org_id):
    conn = sqlite3.connect("swytchai.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM devices WHERE org_id = ?", (org_id,))
    total_devices = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE org_id = ?", (org_id,))
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM changes GROUP BY status")
    change_counts = {"pending": 0, "approved": 0, "rejected": 0}
    for row in cursor.fetchall():
        status = row[0].lower() if row[0] else ""
        if status in change_counts:
            change_counts[status] = row[1]

    cursor.execute("SELECT action, COUNT(*) FROM audit_log WHERE timestamp > datetime('now', '-7 days') GROUP BY action ORDER BY COUNT(*) DESC")
    activity_by_type = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT DATE(timestamp) as day, COUNT(*) FROM audit_log WHERE timestamp > datetime('now', '-7 days') GROUP BY day ORDER BY day")
    daily_activity = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT DATE(proposed_at) as day, COUNT(*) FROM changes WHERE proposed_at > datetime('now', '-30 days') GROUP BY day ORDER BY day")
    changes_over_time = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT vendor, COUNT(*) FROM devices WHERE org_id = ? GROUP BY vendor", (org_id,))
    vendor_distribution = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT username, COUNT(*) as actions FROM audit_log WHERE timestamp > datetime('now', '-7 days') GROUP BY username ORDER BY actions DESC LIMIT 5")
    top_users = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        "total_devices": total_devices,
        "total_users": total_users,
        "change_counts": change_counts,
        "activity_by_type": activity_by_type,
        "daily_activity": daily_activity,
        "changes_over_time": changes_over_time,
        "vendor_distribution": vendor_distribution,
        "top_users": top_users
    }
