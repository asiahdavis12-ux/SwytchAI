# plan_limits.py — SwytchAI Plan Enforcement

PLAN_LIMITS = {
    "free_trial": {
        "max_devices": 3,
        "max_users": 2,
        "features": ["basic_config", "view_audit"]
    },
    "starter": {
        "max_devices": 10,
        "max_users": 3,
        "features": ["basic_config", "ai_assistant", "approval_workflow", "version_tracking", "audit_trail", "notifications"]
    },
    "professional": {
        "max_devices": 50,
        "max_users": 15,
        "features": ["basic_config", "ai_assistant", "approval_workflow", "version_tracking", "audit_trail", "notifications", "bulk_ops", "scheduled_backups", "compliance", "templates", "webhooks", "api_access", "pdf_export"]
    },
    "enterprise": {
        "max_devices": 9999,
        "max_users": 9999,
        "features": ["all"]
    }
}


def get_plan_limits(plan_name):
    """Returns limits for a given plan."""
    return PLAN_LIMITS.get(plan_name, PLAN_LIMITS["starter"])


def check_user_limit(plan_name, current_user_count):
    """Checks if org can add more users."""
    limits = get_plan_limits(plan_name)
    if current_user_count >= limits["max_users"]:
        return False, f"Your {plan_name.title()} plan allows up to {limits['max_users']} users. Please upgrade to add more."
    return True, ""


def check_device_limit(plan_name, current_device_count):
    """Checks if org can add more devices."""
    limits = get_plan_limits(plan_name)
    if current_device_count >= limits["max_devices"]:
        return False, f"Your {plan_name.title()} plan allows up to {limits['max_devices']} devices. Please upgrade to add more."
    return True, ""


def check_feature_access(plan_name, feature):
    """Checks if a feature is available on the current plan."""
    limits = get_plan_limits(plan_name)
    if feature not in limits["features"]:
        return False, f"The '{feature}' feature is not available on your {plan_name.title()} plan. Please upgrade to access this feature."
    return True, ""


def get_usage_summary(plan_name, current_users, current_devices):
    """Returns a usage summary with limits."""
    limits = get_plan_limits(plan_name)
    return {
        "plan": plan_name,
        "users": {
            "current": current_users,
            "max": limits["max_users"],
            "percent": round((current_users / limits["max_users"]) * 100),
        },
        "devices": {
            "current": current_devices,
            "max": limits["max_devices"],
            "percent": round((current_devices / limits["max_devices"]) * 100),
        },
    }
