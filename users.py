
# users.py — User Roles, Permissions & Password Authentication
import hashlib
import json
import os


# ============================================================
# ROLE DEFINITIONS — What each role can do
# ============================================================

ROLES = {
    "admin": {
        "description": "Full access — manages users, devices, and all settings",
        "permissions": [
            "pull_config", "view_versions", "compare_configs",
            "propose_change", "approve_change", "push_config",
            "view_history", "manage_users", "manage_devices"
        ],
    },
    "manager": {
        "description": "Can approve/reject changes and view all configs",
        "permissions": [
            "pull_config", "view_versions", "compare_configs",
            "propose_change", "approve_change", "push_config",
            "view_history",
        ],
    },
    "team_lead": {
        "description": "Can propose changes and pull configs",
        "permissions": [
            "pull_config", "view_versions", "compare_configs",
            "propose_change", "view_history",
        ],
    },
    "technician": {
        "description": "Read-only access — can view configs and history",
        "permissions": [
            "pull_config", "view_versions", "view_history",
        ],
    },
}


# ============================================================
# PASSWORD HASHING — Never store passwords as plain text!
# ============================================================
import bcrypt

def hash_password(password):
    """Hashes a password using bcrypt (industry standard)."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, stored_hash):
    """Verifies a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        return False


# ============================================================
# USER DATABASE FILE — Store users in a JSON file
# ============================================================
USER_DB_PATH = "user_database.json"


def load_user_database():
    """Loads the user database from file. Creates default users if new."""
    if os.path.exists(USER_DB_PATH):
        with open(USER_DB_PATH, "r") as f:
            return json.load(f)

    # First time setup — create default users with default passwords
    default_users = {
        "asiah": {
            "name": "Asiah Davis",
            "role": "admin",
            "site": "PHX026",
            "password_hash": hash_password("admin123"),
            "must_change_password": True,
        },
        "arwa": {
            "name": "Arwa Hawwari",
            "role": "manager",
            "site": "PHX026",
            "password_hash": hash_password("manager123"),
            "must_change_password": True,
        },
        "tech1": {
            "name": "New Technician",
            "role": "technician",
            "site": "PHX026",
            "password_hash": hash_password("tech123"),
            "must_change_password": True,
        },
        "lead1": {
            "name": "Senior Tech",
            "role": "team_lead",
            "site": "PHX026",
            "password_hash": hash_password("lead123"),
            "must_change_password": True,
        },
    }

    save_user_database(default_users)
    print("\n  📋 First time setup — default users created!")
    print("  Default passwords are set. Users will be asked to change them.\n")
    return default_users


def save_user_database(users):
    """Saves the user database to file."""
    with open(USER_DB_PATH, "w") as f:
        json.dump(users, f, indent=4)


# ============================================================
# LOGIN — With password authentication
# ============================================================
def login():
    """Login with username and password. Returns username if successful."""
    users = load_user_database()

    print("\n  SwytchAI Login")
    print("  " + "-" * 30)

    # Allow 3 attempts
    for attempt in range(3):
        username = input("  Username: ").strip().lower()

        user = users.get(username)
        if not user:
            remaining = 2 - attempt
            print(f"  ❌ User not found! ({remaining} attempts remaining)")
            if remaining == 0:
                print("\n  🔒 Too many failed attempts. Access denied.\n")
                return None
            continue

        password = input("  Password: ").strip()

        if not verify_password(password, user["password_hash"]):
            remaining = 2 - attempt
            print(f"  ❌ Incorrect password! ({remaining} attempts remaining)")
            if remaining == 0:
                print("\n  🔒 Too many failed attempts. Access denied.\n")
                return None
            continue

        # Login successful!
        role = user["role"]
        role_info = ROLES[role]

        print(f"\n  ✅ Welcome, {user['name']}!")
        print(f"     Role: {role_info['description']}")
        print(f"     Site: {user['site']}")
        print()

        # Force password change on first login
        if user.get("must_change_password", False):
            print("  ⚠️  You must change your default password before continuing.")
            changed = change_password(username)
            if not changed:
                print("  ❌ Password change failed. Please try logging in again.\n")
                return None

        return username

    return None


# ============================================================
# CHANGE PASSWORD
# ============================================================
def change_password(username):
    """Lets a user change their password."""
    users = load_user_database()
    user = users.get(username)

    if not user:
        print("  ❌ User not found!")
        return False

    print()
    new_password = input("  Enter new password (min 6 characters): ").strip()

    if len(new_password) < 6:
        print("  ❌ Password must be at least 6 characters!")
        return False

    confirm_password = input("  Confirm new password: ").strip()

    if new_password != confirm_password:
        print("  ❌ Passwords don't match!")
        return False

    # Update the password
    user["password_hash"] = hash_password(new_password)
    user["must_change_password"] = False
    save_user_database(users)

    print("  ✅ Password changed successfully!\n")
    return True


# ============================================================
# PERMISSION CHECKER — Same as before
# ============================================================
def get_user(username):
    """Looks up a user by their username."""
    users = load_user_database()
    return users.get(username.lower())


def get_user_role(username):
    """Returns the role name for a user."""
    user = get_user(username)
    if user:
        return user["role"]
    return None


def get_permissions(username):
    """Gets permissions for a user — checks database first, then JSON fallback."""
    try:
        from database import db_get_user
        user = db_get_user(username)
        if user:
            role = user.get("role", "technician")
            return ROLES.get(role, {}).get("permissions", [])
    except Exception:
        pass
    # Fallback to JSON
    users = load_user_database()
    if username in users:
        role = users[username]["role"]
        return ROLES.get(role, {}).get("permissions", [])
    return []


def has_permission(username, permission):
    """Checks if a user has a specific permission."""
    return permission in get_permissions(username)


def check_permission(username, permission):
    """
    Checks permission and prints a message if denied.
    Returns True if allowed, False if denied.
    """
    if has_permission(username, permission):
        return True

    user = get_user(username)
    role_name = ROLES[user["role"]]["description"] if user else "Unknown"
    print(f"\n  🔒 ACCESS DENIED")
    print(f"     Your role ({role_name}) does not have '{permission}' permission.")
    print(f"     Contact a manager or admin for approval.\n")
    return False


# ============================================================
# ADD NEW USER — Only managers and admins can do this
# ============================================================
def add_user():
    """Creates a new user account. Only accessible by managers/admins."""
    users = load_user_database()

    print("\n  Add New User")
    print("  " + "-" * 30)

    username = input("  Username (login ID): ").strip().lower()

    if username in users:
        print(f"  ❌ User '{username}' already exists!\n")
        return

    name = input("  Full name: ").strip()
    site = input("  Site (e.g. PHX026): ").strip()

    print("\n  Available roles:")
    print("    1 — Technician")
    print("    2 — Team Lead")
    print("    3 — Manager")
    print("    4 — Admin")
    role_choice = input("  Select role (1-4): ").strip()

    role_map = {"1": "technician", "2": "team_lead", "3": "manager", "4": "admin"}
    role = role_map.get(role_choice)

    if not role:
        print("  ❌ Invalid role selection!\n")
        return

    # Create with a temporary password
    temp_password = f"temp_[PASSWORD]"

    users[username] = {
        "name": name,
        "role": role,
        "site": site,
        "password_hash": hash_password(temp_password),
        "must_change_password": True,
    }

    save_user_database(users)

    print(f"\n  ✅ User '{username}' created!")
    print(f"     Name: {name}")
    print(f"     Role: {ROLES[role]['description']}")
    print(f"     Site: {site}")
    print(f"     Temp password: {temp_password}")
    print(f"     (They'll be asked to change it on first login)\n")

