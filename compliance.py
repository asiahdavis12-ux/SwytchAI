# compliance.py — SwytchAI Compliance Engine

COMPLIANCE_RULES = {
    "password_encryption": {
        "name": "Password Encryption",
        "icon": "🔐",
        "severity": "critical",
        "description": "Ensure password encryption is enabled",
        "check": lambda config: "service password-encryption" in config,
        "fix": "service password-encryption"
    },
    "ssh_enabled": {
        "name": "SSH Enabled",
        "icon": "🔒",
        "severity": "critical",
        "description": "Ensure SSH is configured for remote access",
        "check": lambda config: "ip ssh version 2" in config or "ip ssh version" in config,
        "fix": "ip ssh version 2"
    },
    "no_telnet": {
        "name": "Telnet Disabled",
        "icon": "🚫",
        "severity": "high",
        "description": "Ensure Telnet is disabled (use SSH only)",
        "check": lambda config: "transport input ssh" in config,
        "fix": "line vty 0 4\n transport input ssh"
    },
    "banner_set": {
        "name": "Login Banner",
        "icon": "📢",
        "severity": "medium",
        "description": "Ensure a login banner is configured",
        "check": lambda config: "banner motd" in config or "banner login" in config,
        "fix": "banner motd # Unauthorized access is prohibited #"
    },
    "ntp_configured": {
        "name": "NTP Configured",
        "icon": "🕐",
        "severity": "medium",
        "description": "Ensure NTP server is configured for time sync",
        "check": lambda config: "ntp server" in config,
        "fix": "ntp server pool.ntp.org"
    },
    "logging_enabled": {
        "name": "Logging Enabled",
        "icon": "📝",
        "severity": "high",
        "description": "Ensure syslog logging is configured",
        "check": lambda config: "logging" in config and "logging host" in config,
        "fix": "logging host 10.0.0.50\nlogging trap informational"
    },
    "no_cdp": {
        "name": "CDP Disabled",
        "icon": "🛡️",
        "severity": "low",
        "description": "Disable CDP to prevent topology discovery",
        "check": lambda config: "no cdp run" in config,
        "fix": "no cdp run"
    },
    "enable_secret": {
        "name": "Enable Secret Set",
        "icon": "🔑",
        "severity": "critical",
        "description": "Ensure enable secret is configured (not enable password)",
        "check": lambda config: "enable secret" in config,
        "fix": "enable secret 0 YourSecretHere"
    }
}

def run_compliance_check(config_text, selected_rules=None):
    results = []
    rules_to_check = selected_rules or list(COMPLIANCE_RULES.keys())

    for rule_id in rules_to_check:
        if rule_id not in COMPLIANCE_RULES:
            continue
        rule = COMPLIANCE_RULES[rule_id]
        passed = rule["check"](config_text)
        results.append({
            "rule_id": rule_id,
            "name": rule["name"],
            "icon": rule["icon"],
            "severity": rule["severity"],
            "description": rule["description"],
            "passed": passed,
            "fix": rule["fix"] if not passed else None
        })

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    score = int((passed / total) * 100) if total > 0 else 0

    return {
        "results": results,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "score": score
    }
