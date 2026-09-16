# test_unifi.py — Mock tests for UniFi integration
import unittest
from unittest.mock import patch, MagicMock
from unifi_engine import UniFiConnection, connect_unifi


class TestUniFiEngine(unittest.TestCase):

    @patch("unifi_engine.requests.Session")
    def test_login_success(self, mock_session):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_session.return_value.post.return_value = mock_resp
        mock_session.return_value.verify = False

        conn = UniFiConnection("192.168.1.1", "admin", "password")
        self.assertIsNotNone(conn)

    @patch("unifi_engine.requests.Session")
    def test_login_failure(self, mock_session):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_session.return_value.post.return_value = mock_resp
        mock_session.return_value.verify = False

        with self.assertRaises(ConnectionError):
            UniFiConnection("192.168.1.1", "admin", "wrongpass")

    @patch("unifi_engine.requests.Session")
    def test_get_devices(self, mock_session):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_devices = MagicMock()
        mock_devices.json.return_value = {
            "data": [
                {"mac": "[MAC_ADDRESS]", "name": "Office Switch", "type": "usw", "state": 1, "ip": "192.168.1.10", "model": "USW-24-POE", "version": "6.5.59", "uptime": 86400, "num_sta": 15, "port_table": []},
                {"mac": "[MAC_ADDRESS]", "name": "Lobby AP", "type": "uap", "state": 1, "ip": "192.168.1.20", "model": "U6-LR", "version": "6.5.62", "uptime": 172800, "num_sta": 30, "port_table": []}
            ]
        }
        mock_session.return_value.post.return_value = mock_login
        mock_session.return_value.get.return_value = mock_devices
        mock_session.return_value.verify = False

        conn = UniFiConnection("192.168.1.1", "admin", "password")
        devices = conn.get_devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["name"], "Office Switch")

    @patch("unifi_engine.requests.Session")
    def test_get_device_summary(self, mock_session):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_devices = MagicMock()
        mock_devices.json.return_value = {
            "data": [
                {"mac": "[MAC_ADDRESS]", "name": "Switch 1", "type": "usw", "state": 1, "ip": "10.0.0.1", "model": "USW-48", "version": "6.5.59", "uptime": 86400, "num_sta": 10, "port_table": []},
                {"mac": "[MAC_ADDRESS]", "name": "AP 1", "type": "uap", "state": 1, "ip": "10.0.0.2", "model": "U6-Pro", "version": "6.5.62", "uptime": 172800, "num_sta": 25, "port_table": []},
                {"mac": "[MAC_ADDRESS]", "name": "Gateway", "type": "ugw", "state": 0, "ip": "[IP_ADDRESS]", "model": "UDM-Pro", "version": "3.1.16", "uptime": 0, "num_sta": 0, "port_table": []}
            ]
        }
        mock_session.return_value.post.return_value = mock_login
        mock_session.return_value.get.return_value = mock_devices
        mock_session.return_value.verify = False

        conn = UniFiConnection("192.168.1.1", "admin", "password")
        summary = conn.get_device_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["switches"], 1)
        self.assertEqual(summary["access_points"], 1)
        self.assertEqual(summary["gateways"], 1)
        self.assertEqual(summary["online"], 2)
        self.assertEqual(summary["offline"], 1)

    @patch("unifi_engine.requests.Session")
    def test_get_networks(self, mock_session):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_networks = MagicMock()
        mock_networks.json.return_value = {
            "data": [
                {"name": "Default", "vlan_enabled": False, "ip_subnet": "192.168.1.0/24"},
                {"name": "Guest", "vlan_enabled": True, "vlan": 100, "ip_subnet": "10.0.100.0/24"}
            ]
        }
        mock_session.return_value.post.return_value = mock_login
        mock_session.return_value.get.return_value = mock_networks
        mock_session.return_value.verify = False

        conn = UniFiConnection("192.168.1.1", "admin", "password")
        networks = conn.get_networks()
        self.assertEqual(len(networks), 2)
        self.assertEqual(networks[1]["name"], "Guest")


if __name__ == "__main__":
    unittest.main()
