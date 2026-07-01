import logging
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

logger = logging.getLogger(__name__)

class PowerManager:
    def __init__(self, proxy=None):
        self.on_changed_callback = None
        self._properties_changed_handler_id = None
        if proxy is not None:
            self.power_proxy = proxy
            logger.info("PowerManager initialized with mock D-Bus proxy.")
        else:
            try:
                self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
                self.power_proxy = Gio.DBusProxy.new_sync(
                    self.bus,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    'net.hadess.PowerProfiles',
                    '/net/hadess/PowerProfiles',
                    'net.hadess.PowerProfiles',
                    None
                )
                logger.info("Successfully connected to net.hadess.PowerProfiles D-Bus service.")
            except Exception as e:
                logger.warning("Could not connect to net.hadess.PowerProfiles D-Bus service: %s", e)
                self.power_proxy = None

        if self.power_proxy:
            # keep the handler id so we can disconnect on shutdown to avoid leaks
            try:
                self._properties_changed_handler_id = self.power_proxy.connect('g-properties-changed', self._on_properties_changed)
            except Exception:
                # Some proxies may not support signal connections (mock objects)
                self._properties_changed_handler_id = None

    def get_active_profile(self):
        if not self.power_proxy:
            logger.warning("Attempted to read CPU profile but D-Bus proxy is unavailable. Returning 'balanced' default.")
            return 'balanced'
        try:
            active_variant = self.power_proxy.get_cached_property('ActiveProfile')
            profile = active_variant.unpack() if active_variant else 'balanced'
            logger.info("Active CPU profile read: %s", profile)
            return profile
        except Exception as e:
            logger.error("Error reading ActiveProfile D-Bus property: %s", e)
            return 'balanced'

    def set_active_profile(self, profile):
        if not self.power_proxy:
            logger.warning("Attempted to set CPU profile to %s but D-Bus proxy is unavailable.", profile)
            return False
        try:
            logger.info("Requesting CPU profile change via D-Bus: %s", profile)
            self.power_proxy.call_sync(
                'org.freedesktop.DBus.Properties.Set',
                GLib.Variant('(ssv)', ('net.hadess.PowerProfiles', 'ActiveProfile', GLib.Variant('s', profile))),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            logger.info("CPU profile successfully set to %s via D-Bus.", profile)
            return True
        except Exception as e:
            logger.error("Error setting CPU profile to %s: %s", profile, e)
            return False

    def connect_changed(self, callback):
        self.on_changed_callback = callback

    def close(self):
        """Clean up any signal handlers or references held by the PowerManager."""
        try:
            if self.power_proxy and self._properties_changed_handler_id:
                try:
                    self.power_proxy.disconnect(self._properties_changed_handler_id)
                except Exception:
                    # Best-effort: ignore failures during cleanup
                    pass
                self._properties_changed_handler_id = None
        finally:
            # Release references to help GC
            self.on_changed_callback = None
            self.power_proxy = None
            self.bus = None

    def _on_properties_changed(self, proxy, changed_properties, invalidated_properties):
        changed_dict = changed_properties.unpack()
        if 'ActiveProfile' in changed_dict:
            new_profile = changed_dict['ActiveProfile']
            logger.info("Received D-Bus ActiveProfile change notification: %s", new_profile)
            if self.on_changed_callback:
                self.on_changed_callback(new_profile)
