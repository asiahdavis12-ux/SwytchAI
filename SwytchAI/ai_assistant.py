
# ai_assistant.py — AI Config Assistant for SwytchAI
# Generates network configs from plain English commands

# ============================================================
# CONFIG TEMPLATES — Common network tasks by vendor
# ============================================================
# Each template is a function that takes parameters and returns
# the correct config lines for that vendor.

TEMPLATES = {

    # ──────────────────────────────────────────────────────────
    # VLAN MANAGEMENT
    # ──────────────────────────────────────────────────────────
    "create_vlan": {
        "description": "Create a VLAN with a name",
        "keywords": ["create vlan", "add vlan", "new vlan", "make vlan"],
        "params": ["vlan_id", "vlan_name"],
        "configs": {
            "cisco_ios": lambda p: [
                f"vlan {p['vlan_id']}",
                f" name {p['vlan_name']}",
            ],
            "cisco_nxos": lambda p: [
                f"vlan {p['vlan_id']}",
                f" name {p['vlan_name']}",
            ],
            "juniper": lambda p: [
                f"set vlans {p['vlan_name']} vlan-id {p['vlan_id']}",
            ],
            "arista": lambda p: [
                f"vlan {p['vlan_id']}",
                f" name {p['vlan_name']}",
            ],
        },
    },

    "delete_vlan": {
        "description": "Delete a VLAN",
        "keywords": ["delete vlan", "remove vlan", "no vlan"],
        "params": ["vlan_id"],
        "configs": {
            "cisco_ios": lambda p: [
                f"no vlan {p['vlan_id']}",
            ],
            "cisco_nxos": lambda p: [
                f"no vlan {p['vlan_id']}",
            ],
            "juniper": lambda p: [
                f"delete vlans VLAN{p['vlan_id']}",
            ],
            "arista": lambda p: [
                f"no vlan {p['vlan_id']}",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # INTERFACE CONFIGURATION
    # ──────────────────────────────────────────────────────────
    "configure_interface_ip": {
        "description": "Set an IP address on an interface",
        "keywords": ["set ip", "assign ip", "configure ip", "ip address", "add ip"],
        "params": ["interface", "ip_address", "subnet_mask"],
        "configs": {
            "cisco_ios": lambda p: [
                f"interface {p['interface']}",
                f" ip address {p['ip_address']} {p['subnet_mask']}",
                f" no shutdown",
            ],
            "cisco_nxos": lambda p: [
                f"interface {p['interface']}",
                f" ip address {p['ip_address']}/{p['subnet_mask']}",
                f" no shutdown",
            ],
            "juniper": lambda p: [
                f"set interfaces {p['interface']} unit 0 family inet address {p['ip_address']}/{p['subnet_mask']}",
            ],
            "arista": lambda p: [
                f"interface {p['interface']}",
                f" ip address {p['ip_address']}/{p['subnet_mask']}",
                f" no shutdown",
            ],
        },
    },

    "shutdown_interface": {
        "description": "Shut down an interface",
        "keywords": ["shutdown interface", "shut interface", "disable interface", "shut down"],
        "params": ["interface"],
        "configs": {
            "cisco_ios": lambda p: [
                f"interface {p['interface']}",
                f" shutdown",
            ],
            "cisco_nxos": lambda p: [
                f"interface {p['interface']}",
                f" shutdown",
            ],
            "juniper": lambda p: [
                f"set interfaces {p['interface']} disable",
            ],
            "arista": lambda p: [
                f"interface {p['interface']}",
                f" shutdown",
            ],
        },
    },

    "enable_interface": {
        "description": "Enable (no shutdown) an interface",
        "keywords": ["enable interface", "no shut", "bring up", "activate interface", "no shutdown"],
        "params": ["interface"],
        "configs": {
            "cisco_ios": lambda p: [
                f"interface {p['interface']}",
                f" no shutdown",
            ],
            "cisco_nxos": lambda p: [
                f"interface {p['interface']}",
                f" no shutdown",
            ],
            "juniper": lambda p: [
                f"delete interfaces {p['interface']} disable",
            ],
            "arista": lambda p: [
                f"interface {p['interface']}",
                f" no shutdown",
            ],
        },
    },

    "set_interface_description": {
        "description": "Set a description on an interface",
        "keywords": ["interface description", "set description", "describe interface", "label interface"],
        "params": ["interface", "description"],
        "configs": {
            "cisco_ios": lambda p: [
                f"interface {p['interface']}",
                f" description {p['description']}",
            ],
            "cisco_nxos": lambda p: [
                f"interface {p['interface']}",
                f" description {p['description']}",
            ],
            "juniper": lambda p: [
                f"set interfaces {p['interface']} description \"{p['description']}\"",
            ],
            "arista": lambda p: [
                f"interface {p['interface']}",
                f" description {p['description']}",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # ACCESS PORT CONFIGURATION
    # ──────────────────────────────────────────────────────────
    "set_access_port": {
        "description": "Configure a port as an access port on a specific VLAN",
        "keywords": ["access port", "access vlan", "assign port to vlan", "switchport access"],
        "params": ["interface", "vlan_id"],
        "configs": {
            "cisco_ios": lambda p: [
                f"interface {p['interface']}",
                f" switchport mode access",
                f" switchport access vlan {p['vlan_id']}",
                f" no shutdown",
            ],
            "cisco_nxos": lambda p: [
                f"interface {p['interface']}",
                f" switchport",
                f" switchport mode access",
                f" switchport access vlan {p['vlan_id']}",
                f" no shutdown",
            ],
            "juniper": lambda p: [
                f"set interfaces {p['interface']} unit 0 family ethernet-switching interface-mode access",
                f"set interfaces {p['interface']} unit 0 family ethernet-switching vlan members VLAN{p['vlan_id']}",
            ],
            "arista": lambda p: [
                f"interface {p['interface']}",
                f" switchport mode access",
                f" switchport access vlan {p['vlan_id']}",
                f" no shutdown",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # TRUNK PORT CONFIGURATION
    # ──────────────────────────────────────────────────────────
    "set_trunk_port": {
        "description": "Configure a port as a trunk",
        "keywords": ["trunk port", "trunk", "set trunk", "configure trunk", "switchport trunk"],
        "params": ["interface", "allowed_vlans"],
        "configs": {
            "cisco_ios": lambda p: [
                f"interface {p['interface']}",
                f" switchport trunk encapsulation dot1q",
                f" switchport mode trunk",
                f" switchport trunk allowed vlan {p['allowed_vlans']}",
                f" no shutdown",
            ],
            "cisco_nxos": lambda p: [
                f"interface {p['interface']}",
                f" switchport",
                f" switchport mode trunk",
                f" switchport trunk allowed vlan {p['allowed_vlans']}",
                f" no shutdown",
            ],
            "juniper": lambda p: [
                f"set interfaces {p['interface']} unit 0 family ethernet-switching interface-mode trunk",
                f"set interfaces {p['interface']} unit 0 family ethernet-switching vlan members [{p['allowed_vlans']}]",
            ],
            "arista": lambda p: [
                f"interface {p['interface']}",
                f" switchport mode trunk",
                f" switchport trunk allowed vlan {p['allowed_vlans']}",
                f" no shutdown",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # LOOPBACK INTERFACE
    # ──────────────────────────────────────────────────────────
    "create_loopback": {
        "description": "Create a loopback interface with an IP",
        "keywords": ["create loopback", "add loopback", "loopback", "new loopback"],
        "params": ["loopback_id", "ip_address", "subnet_mask"],
        "configs": {
            "cisco_ios": lambda p: [
                f"interface Loopback{p['loopback_id']}",
                f" ip address {p['ip_address']} {p['subnet_mask']}",
                f" no shutdown",
            ],
            "cisco_nxos": lambda p: [
                f"interface loopback{p['loopback_id']}",
                f" ip address {p['ip_address']}/{p['subnet_mask']}",
                f" no shutdown",
            ],
            "juniper": lambda p: [
                f"set interfaces lo0 unit {p['loopback_id']} family inet address {p['ip_address']}/{p['subnet_mask']}",
            ],
            "arista": lambda p: [
                f"interface Loopback{p['loopback_id']}",
                f" ip address {p['ip_address']}/{p['subnet_mask']}",
                f" no shutdown",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # HOSTNAME
    # ──────────────────────────────────────────────────────────
    "set_hostname": {
        "description": "Change the device hostname",
        "keywords": ["set hostname", "change hostname", "hostname", "rename device", "device name"],
        "params": ["hostname"],
        "configs": {
            "cisco_ios": lambda p: [
                f"hostname {p['hostname']}",
            ],
            "cisco_nxos": lambda p: [
                f"hostname {p['hostname']}",
            ],
            "juniper": lambda p: [
                f"set system host-name {p['hostname']}",
            ],
            "arista": lambda p: [
                f"hostname {p['hostname']}",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # BANNER
    # ──────────────────────────────────────────────────────────
    "set_banner": {
        "description": "Set the login banner (MOTD)",
        "keywords": ["set banner", "banner", "motd", "login message", "login banner"],
        "params": ["message"],
        "configs": {
            "cisco_ios": lambda p: [
                f"banner motd # {p['message']} #",
            ],
            "cisco_nxos": lambda p: [
                f"banner motd # {p['message']} #",
            ],
            "juniper": lambda p: [
                f"set system login message \"{p['message']}\"",
            ],
            "arista": lambda p: [
                f"banner motd",
                f"{p['message']}",
                f"EOF",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # STATIC ROUTE
    # ──────────────────────────────────────────────────────────
    "add_static_route": {
        "description": "Add a static route",
        "keywords": ["static route", "add route", "ip route", "create route"],
        "params": ["network", "mask", "next_hop"],
        "configs": {
            "cisco_ios": lambda p: [
                f"ip route {p['network']} {p['mask']} {p['next_hop']}",
            ],
            "cisco_nxos": lambda p: [
                f"ip route {p['network']}/{p['mask']} {p['next_hop']}",
            ],
            "juniper": lambda p: [
                f"set routing-options static route {p['network']}/{p['mask']} next-hop {p['next_hop']}",
            ],
            "arista": lambda p: [
                f"ip route {p['network']}/{p['mask']} {p['next_hop']}",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # DNS
    # ──────────────────────────────────────────────────────────
    "set_dns": {
        "description": "Configure DNS server",
        "keywords": ["set dns", "dns server", "name server", "configure dns"],
        "params": ["dns_server"],
        "configs": {
            "cisco_ios": lambda p: [
                f"ip name-server {p['dns_server']}",
            ],
            "cisco_nxos": lambda p: [
                f"ip name-server {p['dns_server']}",
            ],
            "juniper": lambda p: [
                f"set system name-server {p['dns_server']}",
            ],
            "arista": lambda p: [
                f"ip name-server {p['dns_server']}",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # NTP
    # ──────────────────────────────────────────────────────────
    "set_ntp": {
        "description": "Configure NTP server",
        "keywords": ["set ntp", "ntp server", "configure ntp", "time server"],
        "params": ["ntp_server"],
        "configs": {
            "cisco_ios": lambda p: [
                f"ntp server {p['ntp_server']}",
            ],
            "cisco_nxos": lambda p: [
                f"ntp server {p['ntp_server']}",
            ],
            "juniper": lambda p: [
                f"set system ntp server {p['ntp_server']}",
            ],
            "arista": lambda p: [
                f"ntp server {p['ntp_server']}",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # SNMP
    # ──────────────────────────────────────────────────────────
    "set_snmp_community": {
        "description": "Configure SNMP community string",
        "keywords": ["snmp community", "set snmp", "configure snmp", "snmp string"],
        "params": ["community_string", "access_type"],
        "configs": {
            "cisco_ios": lambda p: [
                f"snmp-server community {p['community_string']} {p['access_type']}",
            ],
            "cisco_nxos": lambda p: [
                f"snmp-server community {p['community_string']} {p['access_type']}",
            ],
            "juniper": lambda p: [
                f"set snmp community {p['community_string']} authorization {p['access_type']}",
            ],
            "arista": lambda p: [
                f"snmp-server community {p['community_string']} {p['access_type']}",
            ],
        },
    },

    # ──────────────────────────────────────────────────────────
    # SAVE CONFIG
    # ──────────────────────────────────────────────────────────
    "save_config": {
        "description": "Save the running config to startup",
        "keywords": ["save config", "write memory", "copy running", "save running", "wr mem"],
        "params": [],
        "configs": {
            "cisco_ios": lambda p: [
                "write memory",
            ],
            "cisco_nxos": lambda p: [
                "copy running-config startup-config",
            ],
            "juniper": lambda p: [
                "commit",
            ],
            "arista": lambda p: [
                "write memory",
            ],
        },
    },
}


# ============================================================
# AI PARSER — Understands what you're asking for
# ============================================================
def parse_request(user_input):
    """
    Takes a plain English request and figures out which template to use.
    Returns the matching template name or None if no match.
    """
    user_input_lower = user_input.lower().strip()

    # Score each template by how many keywords match
    best_match = None
    best_score = 0

    for template_name, template in TEMPLATES.items():
        for keyword in template["keywords"]:
            if keyword in user_input_lower:
                # Longer keyword matches are more specific = better
                score = len(keyword)
                if score > best_score:
                    best_score = score
                    best_match = template_name

    return best_match


# ============================================================
# PARAMETER COLLECTOR — Asks for missing info
# ============================================================
def collect_params(template_name):
    """
    Asks the user for the required parameters for a template.
    Returns a dictionary of parameter values.
    """
    template = TEMPLATES[template_name]
    params = {}

    # Friendly parameter names for the prompts
    param_prompts = {
        "vlan_id": "VLAN ID (e.g. 200)",
        "vlan_name": "VLAN name (e.g. ENGINEERING)",
        "interface": "Interface (e.g. GigabitEthernet1)",
        "ip_address": "IP address (e.g. 192.168.1.1)",
        "subnet_mask": "Subnet mask (e.g. 255.255.255.0)",
        "description": "Description text",
        "hostname": "New hostname",
        "message": "Banner message text",
        "network": "Network address (e.g. 10.0.0.0)",
        "mask": "Network mask (e.g. 255.255.255.0)",
        "next_hop": "Next hop IP (e.g. 192.168.1.254)",
        "dns_server": "DNS server IP (e.g. 8.8.8.8)",
        "ntp_server": "NTP server IP (e.g. 216.239.35.0)",
        "community_string": "SNMP community string",
        "access_type": "Access type (RO or RW)",
        "loopback_id": "Loopback number (e.g. 0, 1, 99)",
        "allowed_vlans": "Allowed VLANs (e.g. 100,200,300 or all)",
    }

    if template["params"]:
        print(f"\n  I need a few details:\n")
        for param in template["params"]:
            prompt = param_prompts.get(param, param)
            value = input(f"    {prompt}: ").strip()
            params[param] = value

    return params


# ============================================================
# CONFIG GENERATOR — Builds the config lines
# ============================================================
def generate_config(template_name, vendor, params):
    """
    Generates vendor-specific config lines from a template.
    Returns a list of config line strings.
    """
    template = TEMPLATES[template_name]
    vendor_configs = template["configs"]

    if vendor not in vendor_configs:
        print(f"\n  ❌ Template '{template_name}' doesn't support vendor '{vendor}' yet.")
        print(f"     Supported: {list(vendor_configs.keys())}\n")
        return None

    # Generate the config lines
    config_lines = vendor_configs[vendor](params)
    return config_lines


# ============================================================
# MAIN AI ASSISTANT FUNCTION — The brains of SwytchAI
# ============================================================
def ai_config_assistant(vendor="cisco_ios"):
    """
    The AI config assistant. Takes plain English input,
    figures out what you want, generates the config.
    Returns config lines ready for the approval workflow.
    """
    print(f"\n  {'=' * 55}")
    print(f"  SwytchAI AI Config Assistant")
    print(f"  {'=' * 55}")
    print(f"  Vendor: {vendor}")
    print(f"  Tell me what you want to configure in plain English.")
    print(f"  Type 'help' to see available commands.")
    print(f"  Type 'done' to exit the assistant.")
    print(f"  {'=' * 55}\n")

    while True:
        user_input = input("  🤖 SwytchAI > ").strip()

        if not user_input:
            continue

        if user_input.lower() == "done":
            print("\n  AI Assistant closed.\n")
            return None

        if user_input.lower() == "help":
            show_available_commands()
            continue

        # Try to parse the request
        template_name = parse_request(user_input)

        if not template_name:
            print(f"\n  🤔 I'm not sure what you mean by '{user_input}'")
            print(f"  Try rephrasing, or type 'help' to see what I can do.\n")
            continue

        template = TEMPLATES[template_name]
        print(f"\n  ✅ Got it! I'll help you: {template['description']}")

        # Collect required parameters
        params = collect_params(template_name)

        # Generate the config
        config_lines = generate_config(template_name, vendor, params)

        if not config_lines:
            continue

        # Show the generated config
        print(f"\n  {'─' * 50}")
        print(f"  Generated Config ({vendor}):")
        print(f"  {'─' * 50}")
        for line in config_lines:
            print(f"    {line}")
        print(f"  {'─' * 50}")

        # Ask what to do with it
        print(f"\n  What would you like to do with this config?")
        print(f"    1 — Send to approval workflow (propose change)")
        print(f"    2 — Generate another config")
        print(f"    3 — Discard and exit")
        print()

        action = input("  Choice (1-3): ").strip()

        if action == "1":
            # Return the config for the approval workflow
            description = input("  Brief description: ").strip()
            return {
                "config_lines": config_lines,
                "description": description,
                "template": template_name,
            }
        elif action == "2":
            print()
            continue
        else:
            print("\n  Config discarded.\n")
            return None


# ============================================================
# HELP — Shows all available commands
# ============================================================
def show_available_commands():
    """Displays all commands the AI assistant understands."""
    print(f"\n  {'=' * 55}")
    print(f"  Available Commands — What You Can Ask Me")
    print(f"  {'=' * 55}")
    print()

    categories = {
        "VLAN Management": ["create_vlan", "delete_vlan"],
        "Interface Config": [
            "configure_interface_ip", "shutdown_interface",
            "enable_interface", "set_interface_description"
        ],
        "Port Config": ["set_access_port", "set_trunk_port"],
        "Routing": ["add_static_route", "create_loopback"],
        "Device Settings": ["set_hostname", "set_banner", "set_dns", "set_ntp"],
        "Monitoring": ["set_snmp_community"],
        "Operations": ["save_config"],
    }

    for category, template_names in categories.items():
        print(f"  {category}:")
        for name in template_names:
            template = TEMPLATES[name]
            keywords = ", ".join(template["keywords"][:3])
            print(f"    • {template['description']}")
            print(f"      Try saying: \"{keywords}\"")
        print()

    print(f"  {'=' * 55}")
    print(f"  Just type naturally — I'll figure out what you need!\n")

