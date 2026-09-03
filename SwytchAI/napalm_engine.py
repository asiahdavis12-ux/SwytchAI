
# napalm_engine.py — Multi-Vendor Abstraction Layer using NAPALM
from napalm import get_network_driver
from datetime import datetime
import os
import json


# ============================================================
# VENDOR MAP — Maps friendly names to NAPALM driver names
# ============================================================
VENDOR_MAP = {
    "cisco_ios":    "ios",
    "cisco_nxos":   "nxos",
    "cisco_iosxr":  "iosxr",
    "juniper":      "junos",
    "arista":       "eos",
}

SUPPORTED_VENDORS = list(VENDOR_MAP.keys())


# ============================================================
# NAPALM DEVICE CLASS — Universal interface for any vendor
# ============================================================
class SwytchDevice:
    """
    This is the abstraction layer — the 'universal remote'.
    No matter what vendor the device is, you use the same
    methods: connect(), get_facts(), get_config(), push_config(), etc.
    NAPALM handles the vendor-specific translation behind the scenes.
    """

    def __init__(self, host, username, password, vendor, port=22, optional_args=None):
        self.host = host
        self.username = username
        self.password = password
        self.vendor = vendor
        self.port = port
        self.connection = None

        # Get the right NAPALM driver for this vendor
        driver_name = VENDOR_MAP.get(vendor)
        if not driver_name:
            raise ValueError(
                f"Unsupported vendor: '{vendor}'\n"
                f"Supported vendors: {SUPPORTED_VENDORS}"
            )

        # Set up optional connection arguments
        if optional_args is None:
            optional_args = {}
        optional_args["port"] = port

        # Create the NAPALM driver (but don't connect yet)
        driver = get_network_driver(driver_name)
        self.device = driver(
            hostname=host,
            username=username,
            password=password,
            optional_args=optional_args,
        )

    # ----------------------------------------------------------
    # CONNECTION
    # ----------------------------------------------------------
    def connect(self):
        """Opens a connection to the device."""
        print(f"  Connecting to {self.host} ({self.vendor})...")
        self.device.open()
        print(f"  ✅ Connected!")

    def disconnect(self):
        """Closes the connection."""
        self.device.close()
        print(f"  Disconnected from {self.host}")

    # ----------------------------------------------------------
    # GET DEVICE FACTS — Works the same on ANY vendor
    # ----------------------------------------------------------
    def get_facts(self):
        """
        Returns basic device info as a clean dictionary.
        Same output format whether it's Cisco, Juniper, or Arista!
        """
        facts = self.device.get_facts()
        return {
            "hostname": facts.get("hostname", "Unknown"),
            "vendor": facts.get("vendor", self.vendor),
            "model": facts.get("model", "Unknown"),
            "serial": facts.get("serial_number", "Unknown"),
            "os_version": facts.get("os_version", "Unknown"),
            "uptime": facts.get("uptime", 0),
            "interfaces": facts.get("interface_list", []),
        }

    # ----------------------------------------------------------
    # GET INTERFACES — Unified interface info across vendors
    # ----------------------------------------------------------
    def get_interfaces(self):
        """
        Returns interface details for the device.
        Same format regardless of vendor!
        """
        return self.device.get_interfaces()

    # ----------------------------------------------------------
    # GET INTERFACE IPs — IP addresses on all interfaces
    # ----------------------------------------------------------
    def get_interface_ips(self):
        """Returns IP addresses assigned to each interface."""
        return self.device.get_interfaces_ip()

    # ----------------------------------------------------------
    # GET CONFIG — Pull the running/startup config
    # ----------------------------------------------------------
    def get_config(self, config_type="running"):
        """
        Pulls the device config.
        config_type can be: 'running', 'startup', or 'candidate'
        Returns a dictionary with all three config types.
        """
        configs = self.device.get_config()
        if config_type == "running":
            return configs.get("running", "")
        elif config_type == "startup":
            return configs.get("startup", "")
        elif config_type == "candidate":
            return configs.get("candidate", "")
        return configs

    # ----------------------------------------------------------
    # GET ARP TABLE — ARP entries from the device
    # ----------------------------------------------------------
    def get_arp_table(self):
        """Returns the ARP table as a list of dictionaries."""
        return self.device.get_arp_table()

    # ----------------------------------------------------------
    # GET MAC TABLE — MAC address table
    # ----------------------------------------------------------
    def get_mac_table(self):
        """Returns the MAC address table."""
        return self.device.get_mac_address_table()

    # ----------------------------------------------------------
    # GET LLDP NEIGHBORS — See what's connected to each port
    # ----------------------------------------------------------
    def get_neighbors(self):
        """Returns LLDP/CDP neighbor information."""
        return self.device.get_lldp_neighbors()

    # ----------------------------------------------------------
    # GET ENVIRONMENT — CPU, memory, temperature, fans, power
    # ----------------------------------------------------------
    def get_environment(self):
        """Returns device health info (CPU, memory, temp, etc.)."""
        return self.device.get_environment()

    # ----------------------------------------------------------
    # COMPARE CONFIG — Shows diff between running and candidate
    # ----------------------------------------------------------
    def compare_config(self, config_lines):
        """
        Loads a candidate config and shows what WOULD change
        without actually applying it. Perfect for pre-approval review!
        """
        # Load the config as a candidate (not applied yet)
        config_text = "\n".join(config_lines)
        self.device.load_merge_candidate(config=config_text)

        # Get the diff — what would change?
        diff = self.device.compare_config()
        return diff

    # ----------------------------------------------------------
    # PUSH CONFIG — Apply config with commit/rollback support
    # ----------------------------------------------------------
    def push_config(self, config_lines):
        """
        Pushes config to the device using NAPALM's merge method.
        This is safer than raw Netmiko because NAPALM supports
        commit/rollback on supported platforms.
        """
        config_text = "\n".join(config_lines)

        # Load as candidate
        self.device.load_merge_candidate(config=config_text)

        # Show what will change
        diff = self.device.compare_config()
        print(f"\n  Changes to be applied:")
        print(f"  {'-' * 40}")
        if diff:
            for line in diff.split("\n"):
                print(f"    {line}")
        else:
            print("    No changes detected")
        print(f"  {'-' * 40}")

        # Commit the changes
        self.device.commit_config()
        print("  ✅ Config committed successfully!")

        return diff

    # ----------------------------------------------------------
    # ROLLBACK — Revert the last committed change
    # ----------------------------------------------------------
    def rollback(self):
        """
        Rolls back the last config change.
        Only works on platforms that support it (Juniper, Arista, NX-OS).
        """
        self.device.rollback()
        print("  ↩️  Config rolled back to previous state!")

    # ----------------------------------------------------------
    # DISCARD CANDIDATE — Cancel a pending config change
    # ----------------------------------------------------------
    def discard_config(self):
        """Discards the candidate config without applying it."""
        self.device.discard_config()
        print("  🗑️  Candidate config discarded.")

    # ----------------------------------------------------------
    # PING — Test connectivity from the device
    # ----------------------------------------------------------
    def ping(self, destination):
        """Pings a destination from the device."""
        return self.device.ping(destination)


# ============================================================
# DEVICE FACTORY — Creates SwytchDevice from a device dictionary
# ============================================================
def create_device(device_dict):
    """
    Takes a device dictionary (like from devices.py)
    and returns a SwytchDevice object.
    """
    return SwytchDevice(
        host=device_dict["host"],
        username=device_dict["username"],
        password=device_dict["password"],
        vendor=device_dict["vendor"],
        port=device_dict.get("port", 22),
        optional_args=device_dict.get("optional_args"),
    )


# ============================================================
# PRINT DEVICE INFO — Nicely formatted device summary
# ============================================================
def print_device_info(facts):
    """Prints device facts in a clean, readable format."""
    print(f"\n  {'=' * 50}")
    print(f"  DEVICE INFORMATION")
    print(f"  {'=' * 50}")
    print(f"  Hostname:    {facts['hostname']}")
    print(f"  Vendor:      {facts['vendor']}")
    print(f"  Model:       {facts['model']}")
    print(f"  Serial:      {facts['serial']}")
    print(f"  OS Version:  {facts['os_version']}")
    print(f"  Uptime:      {format_uptime(facts['uptime'])}")
    print(f"  Interfaces:  {len(facts['interfaces'])}")
    print(f"  {'=' * 50}\n")


def format_uptime(seconds):
    """Converts uptime seconds to a human-readable format."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    return f"{days}d {hours}h {minutes}m"

