
# devices.py — Secure Device Inventory (credentials from .env file)
import os
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

# ============================================================
# CISCO DEVICES
# ============================================================
cisco_sandbox = {
    "host": os.getenv("CISCO_HOST"),
    "username": os.getenv("CISCO_USERNAME"),
    "password": os.getenv("CISCO_PASSWORD"),
    "vendor": "cisco_ios",
    "port": int(os.getenv("CISCO_PORT", 22)),

    # Netmiko format for backward compatibility
    "device_type": "cisco_ios",
}

# Uncomment when you have more devices
# juniper_device = {
#     "host": os.getenv("JUNIPER_HOST"),
#     "username": os.getenv("JUNIPER_USERNAME"),
#     "password": os.getenv("JUNIPER_PASSWORD"),
#     "vendor": "juniper",
#     "port": 22,
#     "device_type": "junos",
# }

# ============================================================
# ACTIVE DEVICE LIST
# ============================================================
all_devices = [cisco_sandbox]

# Quick reference for single-device operations
cisco_switch = cisco_sandbox

