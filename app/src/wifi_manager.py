import logging
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

logger = logging.getLogger(__name__)

class WifiManager:
    def __init__(self, bus=None, nm_proxy=None, settings_proxy=None):
        self.bus = bus
        self.nm_proxy = nm_proxy
        self.settings_proxy = settings_proxy
        
        if bus is None and nm_proxy is None:
            try:
                self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
                self.nm_proxy = Gio.DBusProxy.new_sync(
                    self.bus,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    'org.freedesktop.NetworkManager',
                    '/org/freedesktop/NetworkManager',
                    'org.freedesktop.NetworkManager',
                    None
                )
                self.settings_proxy = Gio.DBusProxy.new_sync(
                    self.bus,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    'org.freedesktop.NetworkManager',
                    '/org/freedesktop/NetworkManager/Settings',
                    'org.freedesktop.NetworkManager.Settings',
                    None
                )
                logger.info("Successfully connected to NetworkManager D-Bus service.")
            except Exception as e:
                logger.warning("Could not connect to NetworkManager D-Bus service: %s", e)
                self.nm_proxy = None
                self.settings_proxy = None

    def get_available_ssids(self):
        available_ssids = set()
        if not self.nm_proxy or not self.bus:
            return available_ssids
        try:
            devices_var = self.nm_proxy.call_sync(
                'GetDevices',
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            devices = devices_var.unpack()[0]
            for path in devices:
                try:
                    dev_prop = Gio.DBusProxy.new_sync(
                        self.bus,
                        Gio.DBusProxyFlags.NONE,
                        None,
                        'org.freedesktop.NetworkManager',
                        path,
                        'org.freedesktop.DBus.Properties',
                        None
                    )
                    dev_type_val = dev_prop.call_sync(
                        'Get',
                        GLib.Variant('(ss)', ('org.freedesktop.NetworkManager.Device', 'DeviceType')),
                        Gio.DBusCallFlags.NONE,
                        -1,
                        None
                    )
                    dev_type = dev_type_val.unpack()[0]
                    if dev_type == 2: # NM_DEVICE_TYPE_WIFI
                        dev_wifi = Gio.DBusProxy.new_sync(
                            self.bus,
                            Gio.DBusProxyFlags.NONE,
                            None,
                            'org.freedesktop.NetworkManager',
                            path,
                            'org.freedesktop.NetworkManager.Device.Wireless',
                            None
                        )
                        aps_var = dev_wifi.call_sync(
                            'GetAccessPoints',
                            None,
                            Gio.DBusCallFlags.NONE,
                            -1,
                            None
                        )
                        aps = aps_var.unpack()[0]
                        for ap_path in aps:
                            try:
                                ap_prop = Gio.DBusProxy.new_sync(
                                    self.bus,
                                    Gio.DBusProxyFlags.NONE,
                                    None,
                                    'org.freedesktop.NetworkManager',
                                    ap_path,
                                    'org.freedesktop.DBus.Properties',
                                    None
                                )
                                ssid_val = ap_prop.call_sync(
                                    'Get',
                                    GLib.Variant('(ss)', ('org.freedesktop.NetworkManager.AccessPoint', 'Ssid')),
                                    Gio.DBusCallFlags.NONE,
                                    -1,
                                    None
                                )
                                ssid_bytes = bytes(ssid_val.unpack()[0])
                                if ssid_bytes:
                                    available_ssids.add(ssid_bytes)
                            except Exception as ap_err:
                                logger.debug("Failed to query AP %s: %s", ap_path, ap_err)
                except Exception as dev_err:
                    logger.debug("Failed to query device %s: %s", path, dev_err)
        except Exception as e:
            logger.error("Error retrieving available SSIDs: %s", e)
        return available_ssids

    def get_saved_wifi_connections(self):
        if not self.settings_proxy or not self.bus:
            return []
        try:
            connections_var = self.settings_proxy.call_sync(
                'ListConnections',
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            connection_paths = connections_var.unpack()[0]
            
            # Query currently available access points and active network
            available_ssids = self.get_available_ssids()
            active_uuid, _ = self.get_active_wifi()
            
            wifi_connections = []
            for path in connection_paths:
                try:
                    conn_proxy = Gio.DBusProxy.new_sync(
                        self.bus,
                        Gio.DBusProxyFlags.NONE,
                        None,
                        'org.freedesktop.NetworkManager',
                        path,
                        'org.freedesktop.NetworkManager.Settings.Connection',
                        None
                    )
                    settings_var = conn_proxy.call_sync(
                        'GetSettings',
                        None,
                        Gio.DBusCallFlags.NONE,
                        -1,
                        None
                    )
                    settings = settings_var.unpack()[0]
                    conn_info = settings.get('connection', {})
                    conn_type = conn_info.get('type')
                    if conn_type == '802-11-wireless':
                        uuid = conn_info.get('uuid')
                        wifi_info = settings.get('802-11-wireless', {})
                        ssid_list = wifi_info.get('ssid')
                        
                        is_available = False
                        if ssid_list:
                            ssid_bytes = bytes(ssid_list)
                            if ssid_bytes in available_ssids:
                                is_available = True
                                
                        # Always include the currently active network, even if not scanned
                        if is_available or (uuid == active_uuid):
                            wifi_connections.append({
                                'id': conn_info.get('id'),
                                'uuid': uuid,
                                'path': path
                            })
                except Exception as e:
                    logger.debug("Failed to get settings for connection %s: %s", path, e)
            
            # Sort by name/id
            wifi_connections.sort(key=lambda x: x['id'].lower() if x['id'] else '')
            return wifi_connections
        except Exception as e:
            logger.error("Error retrieving saved Wi-Fi connections: %s", e)
            return []

    def get_active_wifi(self):
        # Returns (uuid, active_connection_path) or (None, None)
        if not self.nm_proxy or not self.bus:
            return None, None
        try:
            prop_proxy = Gio.DBusProxy.new_sync(
                self.bus,
                Gio.DBusProxyFlags.NONE,
                None,
                'org.freedesktop.NetworkManager',
                '/org/freedesktop/NetworkManager',
                'org.freedesktop.DBus.Properties',
                None
            )
            val = prop_proxy.call_sync(
                'Get',
                GLib.Variant('(ss)', ('org.freedesktop.NetworkManager', 'ActiveConnections')),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            active_paths = val.unpack()[0]
            for path in active_paths:
                try:
                    active_prop_proxy = Gio.DBusProxy.new_sync(
                        self.bus,
                        Gio.DBusProxyFlags.NONE,
                        None,
                        'org.freedesktop.NetworkManager',
                        path,
                        'org.freedesktop.DBus.Properties',
                        None
                    )
                    
                    def get_active_prop(name):
                        try:
                            v = active_prop_proxy.call_sync(
                                'Get',
                                GLib.Variant('(ss)', ('org.freedesktop.NetworkManager.Connection.Active', name)),
                                Gio.DBusCallFlags.NONE,
                                -1,
                                None
                            )
                            return v.unpack()[0]
                        except Exception:
                            return None
                    
                    conn_type = get_active_prop('Type')
                    state = get_active_prop('State')
                    if conn_type == '802-11-wireless' and state == 2: # Activated
                        uuid = get_active_prop('Uuid')
                        return uuid, path
                except Exception as e:
                    logger.debug("Failed to query active connection %s: %s", path, e)
            return None, None
        except Exception as e:
            logger.error("Error retrieving active Wi-Fi connection: %s", e)
            return None, None

    def activate_connection(self, connection_path):
        if not self.nm_proxy:
            return False
        try:
            logger.info("Activating Wi-Fi connection: %s", connection_path)
            self.nm_proxy.call_sync(
                'ActivateConnection',
                GLib.Variant('(ooo)', (connection_path, '/', '/')),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            return True
        except Exception as e:
            logger.error("Error activating Wi-Fi connection %s: %s", connection_path, e)
            return False

    def deactivate_connection(self, active_connection_path):
        if not self.nm_proxy:
            return False
        try:
            logger.info("Deactivating Wi-Fi connection: %s", active_connection_path)
            self.nm_proxy.call_sync(
                'DeactivateConnection',
                GLib.Variant('(o)', (active_connection_path,)),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            return True
        except Exception as e:
            logger.error("Error deactivating Wi-Fi connection %s: %s", active_connection_path, e)
            return False

    def close(self):
        self.bus = None
        self.nm_proxy = None
        self.settings_proxy = None
