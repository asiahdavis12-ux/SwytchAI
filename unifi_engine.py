# unifi_engine.py — SwytchAI UniFi Controller Integration
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UniFiConnection:
    def __init__(self, host, username, password, port=8443, site="default", verify_ssl=False):
        self.base_url = f"https://{host}:{port}"
        self.site = site
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.login(username, password)

    def login(self, username, password):
        url = f"{self.base_url}/api/login"
        payload = {"username": username, "password": password}
        resp = self.session.post(url, json=payload)
        if resp.status_code != 200:
            raise ConnectionError(f"UniFi login failed: {resp.status_code}")

    def logout(self):
        self.session.post(f"{self.base_url}/api/logout")

    def get_devices(self):
        """Get all UniFi devices (switches, APs, gateways)"""
        url = f"{self.base_url}/api/s/{self.site}/stat/device"
        resp = self.session.get(url)
        return resp.json().get("data", [])

    def get_device_details(self, mac):
        """Get details for a specific device by MAC"""
        devices = self.get_devices()
        for device in devices:
            if device.get("mac") == mac.lower():
                return device
        return None

    def get_switch_ports(self, mac):
        """Get port configuration for a switch"""
        device = self.get_device_details(mac)
        if device:
            return device.get("port_table", [])
        return []

    def get_clients(self):
        """Get all connected clients"""
        url = f"{self.base_url}/api/s/{self.site}/stat/sta"
        resp = self.session.get(url)
        return resp.json().get("data", [])

    def get_networks(self):
        """Get all network/VLAN configs"""
        url = f"{self.base_url}/api/s/{self.site}/rest/networkconf"
        resp = self.session.get(url)
        return resp.json().get("data", [])

    def get_port_profiles(self):
        """Get port profiles"""
        url = f"{self.base_url}/api/s/{self.site}/rest/portconf"
        resp = self.session.get(url)
        return resp.json().get("data", [])

    def get_sites(self):
        """Get all sites (for MSPs managing multiple locations)"""
        url = f"{self.base_url}/api/self/sites"
        resp = self.session.get(url)
        return resp.json().get("data", [])

    def get_alarms(self):
        """Get active alarms"""
        url = f"{self.base_url}/api/s/{self.site}/stat/alarm"
        resp = self.session.get(url)
        return resp.json().get("data", [])

    def get_events(self, limit=50):
        """Get recent events"""
        url = f"{self.base_url}/api/s/{self.site}/stat/event"
        resp = self.session.get(url, params={"_limit": limit})
        return resp.json().get("data", [])

    def backup_config(self):
        """Trigger a config backup on the controller"""
        url = f"{self.base_url}/api/s/{self.site}/cmd/backup"
        payload = {"cmd": "backup"}
        resp = self.session.post(url, json=payload)
        return resp.json()

    def get_device_summary(self):
        """Get a summary of all devices for the dashboard"""
        devices = self.get_devices()
        summary = {
            "total": len(devices),
            "switches": 0,
            "access_points": 0,
            "gateways": 0,
            "online": 0,
            "offline": 0,
            "devices": []
        }
        for d in devices:
            dtype = d.get("type", "")
            if dtype == "usw":
                summary["switches"] += 1
            elif dtype == "uap":
                summary["access_points"] += 1
            elif dtype == "ugw":
                summary["gateways"] += 1

            if d.get("state", 0) == 1:
                summary["online"] += 1
            else:
                summary["offline"] += 1

            summary["devices"].append({
                "name": d.get("name", "Unknown"),
                "mac": d.get("mac", ""),
                "model": d.get("model", ""),
                "type": dtype,
                "ip": d.get("ip", "N/A"),
                "version": d.get("version", "N/A"),
                "uptime": d.get("uptime", 0),
                "status": "Online" if d.get("state", 0) == 1 else "Offline",
                "num_ports": d.get("port_table", []),
                "clients": d.get("num_sta", 0)
            })
        return summary


def connect_unifi(host, username, password, port=8443, site="default"):
    """Helper function to create a UniFi connection"""
    try:
        conn = UniFiConnection(host, username, password, port, site)
        return conn
    except Exception as e:
        raise ConnectionError(f"Failed to connect to UniFi Controller: {e}")
