
# main.py — SwytchAI with AI Config Assistant
from devices import all_devices, cisco_switch
from config_manager import pull_config, show_versions, compare_configs
from config_pusher import (
    propose_change,
    show_pending_changes,
    review_change,
    rollback_change,
    show_change_history,
)
from users import login, check_permission, get_user, change_password, add_user, ROLES
from napalm_engine import create_device, print_device_info, SUPPORTED_VENDORS
from ai_assistant import ai_config_assistant


def print_banner():
    print()
    print("=" * 50)
    print("  SwytchAI — Network Config Manager")
    print("  Multi-Vendor | AI-Powered | Secure")
    print("=" * 50)
    print()


def print_menu(username):
    user = get_user(username)
    role = user["role"]
    role_desc = ROLES[role]["description"]

    print(f"  Logged in as: {user['name']} ({role_desc})")
    print(f"  {'-' * 46}")
    print()
    print("  ── Config Management ──")
    print("  1  — Pull configs from all devices")
    print("  2  — View saved versions for a device")
    print("  3  — Compare two config versions (diff)")
    print()
    print("  ── Change Workflow ──")
    print("  4  — Propose a config change (manual)")
    print("  5  — Review & approve pending changes")
    print("  6  — View change history")
    print("  7  — Rollback a pushed change")
    print()
    print("  ── AI Assistant ──")
    print("  8  — 🤖 AI Config Assistant (plain English)")
    print()
    print("  ── NAPALM Multi-Vendor Tools ──")
    print("  9  — Get device facts (any vendor)")
    print("  10 — View interfaces")
    print("  11 — View LLDP/CDP neighbors")
    print("  12 — Check device health (CPU/Mem/Temp)")
    print("  13 — View ARP table")
    print("  14 — Preview config change (dry run)")
    print()
    print("  ── Account ──")
    print("  15 — Change my password")
    print("  16 — Add a new user")
    print("  17 — Switch user")
    print("  18 — Exit")
    print()


def select_device():
    """Lets the user pick which device to work with."""
    if len(all_devices) == 1:
        print(f"  Using device: {all_devices[0]['host']}")
        return all_devices[0]

    print("\n  Available devices:")
    print(f"  {'-' * 40}")
    for i, device in enumerate(all_devices, 1):
        print(f"    {i} — {device['host']} ({device['vendor']})")
    print()

    try:
        choice = int(input("  Select device number: ").strip())
        if 1 <= choice <= len(all_devices):
            return all_devices[choice - 1]
    except ValueError:
        pass

    print("  ❌ Invalid selection!")
    return None


def run_napalm_command(device_dict, command_name, command_func):
    """Helper that handles connect/disconnect/errors for NAPALM commands."""
    try:
        device = create_device(device_dict)
        device.connect()
        result = command_func(device)
        device.disconnect()
        return result
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        print(f"  This might mean the device doesn't support this command,")
        print(f"  or the connection timed out. Try again.\n")
        return None


def main():
    print_banner()

    # Login first
    username = login()
    if not username:
        return

    while True:
        print_menu(username)
        choice = input("  Enter your choice (1-18): ").strip()

        # ── CONFIG MANAGEMENT ──

        if choice == "1":
            if not check_permission(username, "pull_config"):
                continue
            print()
            for device in all_devices:
                try:
                    pull_config(device)
                    print(f"  ✅ Success: {device['host']}")
                except Exception as e:
                    print(f"  ❌ Failed: {device['host']} — {e}")
                print()

        elif choice == "2":
            if not check_permission(username, "view_versions"):
                continue
            print()
            host = input("  Enter device hostname: ").strip()
            show_versions(host)
            print()

        elif choice == "3":
            if not check_permission(username, "compare_configs"):
                continue
            print()
            host = input("  Enter device hostname: ").strip()
            show_versions(host)
            v1 = int(input("  Enter first version number: ").strip())
            v2 = int(input("  Enter second version number: ").strip())
            compare_configs(host, v1, v2)
            print()

        # ── CHANGE WORKFLOW ──

        elif choice == "4":
            if not check_permission(username, "propose_change"):
                continue
            print()
            print("  Enter the config lines you want to push.")
            print("  Type each line and press Enter.")
            print("  Type 'done' when finished.")
            print()

            config_lines = []
            while True:
                line = input("  config> ")
                if line.strip().lower() == "done":
                    break
                config_lines.append(line)

            if config_lines:
                description = input("\n  Brief description of this change: ").strip()
                propose_change(cisco_switch, config_lines, description)
            else:
                print("\n  No config lines entered. Change cancelled.\n")

        elif choice == "5":
            if not check_permission(username, "approve_change"):
                continue
            has_pending = show_pending_changes()
            if has_pending:
                try:
                    cid = int(input("\n  Enter change ID to review (0 to skip): ").strip())
                    if cid > 0:
                        review_change(cid, cisco_switch)
                except ValueError:
                    print("\n  Invalid input.\n")

        elif choice == "6":
            if not check_permission(username, "view_history"):
                continue
            show_change_history()

        elif choice == "7":
            if not check_permission(username, "rollback_change"):
                continue
            show_change_history()
            try:
                cid = int(input("\n  Enter change ID to rollback (0 to skip): ").strip())
                if cid > 0:
                    rollback_change(cid, cisco_switch)
            except ValueError:
                print("\n  Invalid input.\n")

        # ── AI ASSISTANT ──

        elif choice == "8":
            if not check_permission(username, "propose_change"):
                continue

            # Get the vendor from the selected device
            device_dict = select_device()
            if not device_dict:
                continue

            vendor = device_dict.get("vendor", "cisco_ios")

            # Launch the AI assistant
            result = ai_config_assistant(vendor=vendor)

            if result:
                # AI generated a config — send it to the approval workflow
                propose_change(
                    device_dict,
                    result["config_lines"],
                    f"[AI Generated] {result['description']}"
                )

        # ── NAPALM MULTI-VENDOR TOOLS ──

        elif choice == "9":
            if not check_permission(username, "pull_config"):
                continue
            device_dict = select_device()
            if device_dict:
                def get_facts(device):
                    facts = device.get_facts()
                    print_device_info(facts)
                    return facts
                run_napalm_command(device_dict, "get_facts", get_facts)

        elif choice == "10":
            if not check_permission(username, "pull_config"):
                continue
            device_dict = select_device()
            if device_dict:
                def get_interfaces(device):
                    interfaces = device.get_interfaces()
                    print(f"\n  {'=' * 60}")
                    print(f"  INTERFACES ({len(interfaces)} total)")
                    print(f"  {'=' * 60}")
                    print(f"  {'Interface':<30} {'Status':<10} {'Speed':<10}")
                    print(f"  {'-' * 50}")
                    for name, info in interfaces.items():
                        status = "✅ UP" if info.get("is_up") else "❌ DOWN"
                        speed = f"{info.get('speed', 0)} Mbps"
                        print(f"  {name:<30} {status:<10} {speed:<10}")
                    print()
                    return interfaces
                run_napalm_command(device_dict, "get_interfaces", get_interfaces)

        elif choice == "11":
            if not check_permission(username, "pull_config"):
                continue
            device_dict = select_device()
            if device_dict:
                def get_neighbors(device):
                    neighbors = device.get_neighbors()
                    print(f"\n  {'=' * 60}")
                    print(f"  LLDP/CDP NEIGHBORS")
                    print(f"  {'=' * 60}")
                    if not neighbors:
                        print("  No neighbors found.")
                    for interface, neighbor_list in neighbors.items():
                        for neighbor in neighbor_list:
                            print(f"  Local Port:  {interface}")
                            print(f"  Remote Host: {neighbor.get('hostname', 'Unknown')}")
                            print(f"  Remote Port: {neighbor.get('port', 'Unknown')}")
                            print(f"  {'-' * 40}")
                    print()
                    return neighbors
                run_napalm_command(device_dict, "get_neighbors", get_neighbors)

        elif choice == "12":
            if not check_permission(username, "pull_config"):
                continue
            device_dict = select_device()
            if device_dict:
                def get_health(device):
                    env = device.get_environment()
                    print(f"\n  {'=' * 60}")
                    print(f"  DEVICE HEALTH")
                    print(f"  {'=' * 60}")
                    cpu = env.get("cpu", {})
                    if cpu:
                        print(f"\n  CPU Usage:")
                        for core, usage in cpu.items():
                            pct = usage.get("%usage", 0)
                            bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
                            print(f"    {core}: [{bar}] {pct}%")
                    memory = env.get("memory", {})
                    if memory:
                        used = memory.get("used_ram", 0)
                        total = memory.get("available_ram", 0) + used
                        if total > 0:
                            pct = (used / total) * 100
                            bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
                            print(f"\n  Memory:")
                            print(f"    [{bar}] {pct:.1f}%")
                            print(f"    Used: {used // 1024 // 1024} MB / {total // 1024 // 1024} MB")
                    temp = env.get("temperature", {})
                    if temp:
                        print(f"\n  Temperature:")
                        for sensor, data in temp.items():
                            current = data.get("temperature", 0)
                            is_alert = data.get("is_alert", False)
                            status = "⚠️ ALERT" if is_alert else "✅ Normal"
                            print(f"    {sensor}: {current}°C {status}")
                    power = env.get("power", {})
                    if power:
                        print(f"\n  Power Supplies:")
                        for ps, data in power.items():
                            status = "✅ OK" if data.get("status") else "❌ FAILED"
                            print(f"    {ps}: {status}")
                    fans = env.get("fans", {})
                    if fans:
                        print(f"\n  Fans:")
                        for fan, data in fans.items():
                            status = "✅ OK" if data.get("status") else "❌ FAILED"
                            print(f"    {fan}: {status}")
                    print(f"\n  {'=' * 60}\n")
                    return env
                run_napalm_command(device_dict, "get_health", get_health)

        elif choice == "13":
            if not check_permission(username, "pull_config"):
                continue
            device_dict = select_device()
            if device_dict:
                def get_arp(device):
                    arp = device.get_arp_table()
                    print(f"\n  {'=' * 60}")
                    print(f"  ARP TABLE ({len(arp)} entries)")
                    print(f"  {'=' * 60}")
                    print(f"  {'IP Address':<20} {'MAC Address':<20} {'Interface':<20}")
                    print(f"  {'-' * 55}")
                    for entry in arp:
                        ip = entry.get("ip", "")
                        mac = entry.get("mac", "")
                        intf = entry.get("interface", "")
                        print(f"  {ip:<20} {mac:<20} {intf:<20}")
                    print()
                    return arp
                run_napalm_command(device_dict, "get_arp", get_arp)

        elif choice == "14":
            if not check_permission(username, "propose_change"):
                continue
            device_dict = select_device()
            if device_dict:
                print()
                print("  Enter config lines to preview (dry run).")
                print("  This will NOT apply any changes.")
                print("  Type 'done' when finished.")
                print()
                config_lines = []
                while True:
                    line = input("  config> ")
                    if line.strip().lower() == "done":
                        break
                    config_lines.append(line)
                if config_lines:
                    def preview(device):
                        diff = device.compare_config(config_lines)
                        print(f"\n  {'=' * 60}")
                        print(f"  DRY RUN PREVIEW — What WOULD change:")
                        print(f"  {'=' * 60}")
                        if diff:
                            for line in diff.split("\n"):
                                print(f"    {line}")
                        else:
                            print("    No changes would be made.")
                        print(f"  {'=' * 60}")
                        print(f"  ℹ️  This was a preview only. Nothing was changed.\n")
                        device.discard_config()
                        return diff
                    run_napalm_command(device_dict, "preview", preview)

        # ── ACCOUNT ──

        elif choice == "15":
            change_password(username)

        elif choice == "16":
            if not check_permission(username, "manage_users"):
                continue
            add_user()

        elif choice == "17":
            print()
            username = login()
            if not username:
                return

        elif choice == "18":
            user = get_user(username)
            print(f"\n  SwytchAI shutting down. Catch you later, {user['name']}! ✌️\n")
            break

        else:
            print("\n  Invalid choice — please enter 1-18\n")


if __name__ == "__main__":
    main()

