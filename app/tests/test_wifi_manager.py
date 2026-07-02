import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src folder to module lookup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from wifi_manager import WifiManager

class TestWifiManager(unittest.TestCase):
    def setUp(self):
        self.mock_bus = MagicMock()
        self.mock_nm_proxy = MagicMock()
        self.mock_settings_proxy = MagicMock()
        self.wifi_mgr = WifiManager(
            bus=self.mock_bus,
            nm_proxy=self.mock_nm_proxy,
            settings_proxy=self.mock_settings_proxy
        )

    def test_get_saved_wifi_connections_success(self):
        # Mock dependencies on instance directly
        self.wifi_mgr.get_available_ssids = MagicMock(return_value={b'MyWifi'})
        self.wifi_mgr.get_active_wifi = MagicMock(return_value=('uuid-1', '/active/1'))

        # Mock ListConnections returning a list of paths
        mock_list = MagicMock()
        mock_list.unpack.return_value = (['/path/1', '/path/2'],)
        self.mock_settings_proxy.call_sync.return_value = mock_list

        # Mock DBusProxy for connection path 1 (wifi)
        mock_conn1_proxy = MagicMock()
        mock_settings1 = MagicMock()
        mock_settings1.unpack.return_value = ({
            'connection': {
                'id': 'MyWifi',
                'uuid': 'uuid-1',
                'type': '802-11-wireless'
            },
            '802-11-wireless': {
                'ssid': [77, 121, 87, 105, 102, 105] # MyWifi
            }
        },)
        mock_conn1_proxy.call_sync.return_value = mock_settings1

        # Mock DBusProxy for connection path 2 (ethernet)
        mock_conn2_proxy = MagicMock()
        mock_settings2 = MagicMock()
        mock_settings2.unpack.return_value = ({
            'connection': {
                'id': 'Wired 1',
                'uuid': 'uuid-2',
                'type': '802-3-ethernet'
            }
        },)
        mock_conn2_proxy.call_sync.return_value = mock_settings2

        # We patch Gio.DBusProxy.new_sync to return our mocks
        def new_sync_mock(bus, flags, info, name, path, interface, cancel):
            if path == '/path/1':
                return mock_conn1_proxy
            elif path == '/path/2':
                return mock_conn2_proxy
            return MagicMock()

        with patch('gi.repository.Gio.DBusProxy.new_sync', side_effect=new_sync_mock):
            connections = self.wifi_mgr.get_saved_wifi_connections()

        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0]['id'], 'MyWifi')
        self.assertEqual(connections[0]['uuid'], 'uuid-1')
        self.assertEqual(connections[0]['path'], '/path/1')

    def test_get_saved_wifi_connections_filters_out_of_range(self):
        # SSID 'OutRange' is NOT in available_ssids
        self.wifi_mgr.get_available_ssids = MagicMock(return_value={b'MyWifi'})
        self.wifi_mgr.get_active_wifi = MagicMock(return_value=('uuid-1', '/active/1'))

        # Mock ListConnections returning a list of paths
        mock_list = MagicMock()
        mock_list.unpack.return_value = (['/path/1', '/path/3'],)
        self.mock_settings_proxy.call_sync.return_value = mock_list

        # Mock DBusProxy for connection path 1 (wifi, in range)
        mock_conn1_proxy = MagicMock()
        mock_settings1 = MagicMock()
        mock_settings1.unpack.return_value = ({
            'connection': {
                'id': 'MyWifi',
                'uuid': 'uuid-1',
                'type': '802-11-wireless'
            },
            '802-11-wireless': {
                'ssid': [77, 121, 87, 105, 102, 105] # MyWifi
            }
        },)
        mock_conn1_proxy.call_sync.return_value = mock_settings1

        # Mock DBusProxy for connection path 3 (wifi, out of range, not active)
        mock_conn3_proxy = MagicMock()
        mock_settings3 = MagicMock()
        mock_settings3.unpack.return_value = ({
            'connection': {
                'id': 'OutRangeWifi',
                'uuid': 'uuid-3',
                'type': '802-11-wireless'
            },
            '802-11-wireless': {
                'ssid': [79, 117, 116, 82, 97, 110, 103, 101] # OutRange
            }
        },)
        mock_conn3_proxy.call_sync.return_value = mock_settings3

        def new_sync_mock(bus, flags, info, name, path, interface, cancel):
            if path == '/path/1':
                return mock_conn1_proxy
            elif path == '/path/3':
                return mock_conn3_proxy
            return MagicMock()

        with patch('gi.repository.Gio.DBusProxy.new_sync', side_effect=new_sync_mock):
            connections = self.wifi_mgr.get_saved_wifi_connections()

        # Should only return MyWifi because OutRangeWifi is not in available_ssids nor active
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0]['id'], 'MyWifi')

    def test_get_available_ssids_success(self):
        # Mock GetDevices
        mock_dev_list = MagicMock()
        mock_dev_list.unpack.return_value = (['/device/1', '/device/2'],)
        self.mock_nm_proxy.call_sync.return_value = mock_dev_list

        # Mock properties for device 1 (Wi-Fi)
        mock_dev1_prop = MagicMock()
        mock_dev1_type = MagicMock()
        mock_dev1_type.unpack.return_value = (2,) # Wi-Fi
        mock_dev1_prop.call_sync.return_value = mock_dev1_type

        # Mock properties for device 2 (Ethernet)
        mock_dev2_prop = MagicMock()
        mock_dev2_type = MagicMock()
        mock_dev2_type.unpack.return_value = (1,) # Ethernet
        mock_dev2_prop.call_sync.return_value = mock_dev2_type

        # Mock Wireless interface for device 1
        mock_dev1_wifi = MagicMock()
        mock_ap_list = MagicMock()
        mock_ap_list.unpack.return_value = (['/ap/1'],)
        mock_dev1_wifi.call_sync.return_value = mock_ap_list

        # Mock properties for AP 1
        mock_ap1_prop = MagicMock()
        mock_ap1_ssid = MagicMock()
        mock_ap1_ssid.unpack.return_value = ([77, 121, 87, 105, 102, 105],) # MyWifi
        mock_ap1_prop.call_sync.return_value = mock_ap1_ssid

        def new_sync_mock(bus, flags, info, name, path, interface, cancel):
            if interface == 'org.freedesktop.DBus.Properties':
                if path == '/device/1':
                    return mock_dev1_prop
                elif path == '/device/2':
                    return mock_dev2_prop
                elif path == '/ap/1':
                    return mock_ap1_prop
            elif interface == 'org.freedesktop.NetworkManager.Device.Wireless':
                if path == '/device/1':
                    return mock_dev1_wifi
            return MagicMock()

        with patch('gi.repository.Gio.DBusProxy.new_sync', side_effect=new_sync_mock):
            ssids = self.wifi_mgr.get_available_ssids()

        self.assertEqual(ssids, {b'MyWifi'})

    def test_get_saved_wifi_connections_failure(self):
        self.mock_settings_proxy.call_sync.side_effect = Exception("D-Bus Settings not available")
        with self.assertLogs('wifi_manager', level='ERROR') as cm:
            connections = self.wifi_mgr.get_saved_wifi_connections()
        self.assertEqual(connections, [])
        self.assertTrue(any('Error retrieving saved Wi-Fi connections' in m for m in cm.output))

    def test_get_active_wifi_success(self):
        # Mock DBusProxy call_sync for properties
        mock_prop_proxy = MagicMock()
        mock_val = MagicMock()
        mock_val.unpack.return_value = (['/active/1'],)
        mock_prop_proxy.call_sync.return_value = mock_val

        # Mock for the active connection proxy
        mock_active_prop_proxy = MagicMock()
        
        def call_sync_active(name, var, flags, timeout, cancel):
            # Unpack var to see what property is requested
            prop_name = var.unpack()[1]
            ret = MagicMock()
            if prop_name == 'Type':
                ret.unpack.return_value = ('802-11-wireless',)
            elif prop_name == 'State':
                ret.unpack.return_value = (2,) # Activated
            elif prop_name == 'Uuid':
                ret.unpack.return_value = ('uuid-1',)
            return ret

        mock_active_prop_proxy.call_sync.side_effect = call_sync_active

        def new_sync_mock(bus, flags, info, name, path, interface, cancel):
            if interface == 'org.freedesktop.DBus.Properties':
                if path == '/org/freedesktop/NetworkManager':
                    return mock_prop_proxy
                elif path == '/active/1':
                    return mock_active_prop_proxy
            return MagicMock()

        with patch('gi.repository.Gio.DBusProxy.new_sync', side_effect=new_sync_mock):
            uuid, path = self.wifi_mgr.get_active_wifi()

        self.assertEqual(uuid, 'uuid-1')
        self.assertEqual(path, '/active/1')

    def test_get_active_wifi_failure(self):
        self.mock_nm_proxy.get_cached_property.return_value = None
        # We also mock Gio.DBusProxy.new_sync call raise exception
        def new_sync_mock(*args, **kwargs):
            m = MagicMock()
            m.call_sync.side_effect = Exception("Properties not available")
            return m

        with patch('gi.repository.Gio.DBusProxy.new_sync', side_effect=new_sync_mock):
            with self.assertLogs('wifi_manager', level='ERROR') as cm:
                uuid, path = self.wifi_mgr.get_active_wifi()
        self.assertIsNone(uuid)
        self.assertIsNone(path)
        self.assertTrue(any('Error retrieving active Wi-Fi connection' in m for m in cm.output))

    def test_activate_connection_success(self):
        self.mock_nm_proxy.call_sync.return_value = MagicMock()
        success = self.wifi_mgr.activate_connection('/path/1')
        self.assertTrue(success)
        self.mock_nm_proxy.call_sync.assert_called_once()

    def test_activate_connection_failure(self):
        self.mock_nm_proxy.call_sync.side_effect = Exception("Activation failed")
        with self.assertLogs('wifi_manager', level='ERROR') as cm:
            success = self.wifi_mgr.activate_connection('/path/1')
        self.assertFalse(success)
        self.assertTrue(any('Error activating Wi-Fi connection' in m for m in cm.output))

    def test_deactivate_connection_success(self):
        self.mock_nm_proxy.call_sync.return_value = MagicMock()
        success = self.wifi_mgr.deactivate_connection('/active/1')
        self.assertTrue(success)
        self.mock_nm_proxy.call_sync.assert_called_once()

    def test_deactivate_connection_failure(self):
        self.mock_nm_proxy.call_sync.side_effect = Exception("Deactivation failed")
        with self.assertLogs('wifi_manager', level='ERROR') as cm:
            success = self.wifi_mgr.deactivate_connection('/active/1')
        self.assertFalse(success)
        self.assertTrue(any('Error deactivating Wi-Fi connection' in m for m in cm.output))

    @patch('gi.repository.Gio.bus_get_sync')
    @patch('gi.repository.Gio.DBusProxy.new_sync')
    def test_wifi_manager_init_default_success(self, mock_new_sync, mock_bus_get_sync):
        mock_bus = MagicMock()
        mock_bus_get_sync.return_value = mock_bus
        
        mock_proxy1 = MagicMock()
        mock_proxy2 = MagicMock()
        mock_new_sync.side_effect = [mock_proxy1, mock_proxy2]
        
        mgr = WifiManager()
        self.assertEqual(mgr.bus, mock_bus)
        self.assertEqual(mgr.nm_proxy, mock_proxy1)
        self.assertEqual(mgr.settings_proxy, mock_proxy2)

    @patch('gi.repository.Gio.DBusProxy.new_sync')
    def test_wifi_manager_init_with_bus_only(self, mock_new_sync):
        mock_bus = MagicMock()
        mock_proxy1 = MagicMock()
        mock_proxy2 = MagicMock()
        mock_new_sync.side_effect = [mock_proxy1, mock_proxy2]
        
        mgr = WifiManager(bus=mock_bus)
        self.assertEqual(mgr.bus, mock_bus)
        self.assertEqual(mgr.nm_proxy, mock_proxy1)
        self.assertEqual(mgr.settings_proxy, mock_proxy2)

    @patch('gi.repository.Gio.bus_get_sync')
    @patch('gi.repository.Gio.DBusProxy.new_sync')
    def test_wifi_manager_init_partially_configured_fails(self, mock_new_sync, mock_bus_get_sync):
        mock_bus = MagicMock()
        mock_bus_get_sync.return_value = mock_bus
        mock_new_sync.side_effect = [MagicMock(), Exception("D-Bus proxy error")]
        
        mgr = WifiManager()
        self.assertIsNone(mgr.bus)
        self.assertIsNone(mgr.nm_proxy)
        self.assertIsNone(mgr.settings_proxy)

    @patch('gi.repository.Gio.bus_get_sync')
    def test_wifi_manager_init_missing_bus_fails(self, mock_bus_get_sync):
        mock_bus_get_sync.side_effect = Exception("System bus connection failed")
        mgr = WifiManager()
        self.assertIsNone(mgr.bus)
        self.assertIsNone(mgr.nm_proxy)
        self.assertIsNone(mgr.settings_proxy)

    def test_get_saved_wifi_connections_active_uuid_none(self):
        self.wifi_mgr.get_available_ssids = MagicMock(return_value=set())
        self.wifi_mgr.get_active_wifi = MagicMock(return_value=(None, None))

        mock_list = MagicMock()
        mock_list.unpack.return_value = (['/path/1'],)
        self.mock_settings_proxy.call_sync.return_value = mock_list

        mock_conn_proxy = MagicMock()
        mock_settings = MagicMock()
        mock_settings.unpack.return_value = ({
            'connection': {
                'id': 'MyWifi',
                'uuid': None,
                'type': '802-11-wireless'
            },
            '802-11-wireless': {
                'ssid': [77, 121, 87, 105, 102, 105]
            }
        },)
        mock_conn_proxy.call_sync.return_value = mock_settings

        with patch('gi.repository.Gio.DBusProxy.new_sync', return_value=mock_conn_proxy):
            connections = self.wifi_mgr.get_saved_wifi_connections()

        self.assertEqual(len(connections), 0)

    def test_deactivate_connection_invalid_path(self):
        success = self.wifi_mgr.deactivate_connection(None)
        self.assertFalse(success)
        success = self.wifi_mgr.deactivate_connection('/')
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
