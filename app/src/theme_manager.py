import logging
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio

logger = logging.getLogger(__name__)

class ThemeManager:
    def __init__(self, settings=None):
        self.on_changed_callback = None
        self._changed_handler_id = None
        if settings is not None:
            self.theme_settings = settings
            logger.info("ThemeManager initialized with mock GSettings.")
        else:
            try:
                self.theme_settings = Gio.Settings.new('org.gnome.desktop.interface')
                logger.info("Successfully connected to org.gnome.desktop.interface GSettings schema.")
            except Exception as e:
                logger.warning("org.gnome.desktop.interface GSettings schema not found: %s", e)
                self.theme_settings = None

        if self.theme_settings:
            try:
                self._changed_handler_id = self.theme_settings.connect('changed::color-scheme', self._on_setting_changed)
            except Exception:
                self._changed_handler_id = None

    def get_color_scheme(self):
        if not self.theme_settings:
            logger.warning("Attempted to read color-scheme but GSettings schema is unavailable. Returning 'default'.")
            return 'default'
        try:
            scheme = self.theme_settings.get_string('color-scheme')
            logger.info("Active color-scheme theme variant read: %s", scheme)
            return scheme
        except Exception as e:
            logger.error("Error reading color-scheme GSettings: %s", e)
            return 'default'

    def set_color_scheme(self, scheme):
        if not self.theme_settings:
            logger.warning("Attempted to set color-scheme to %s but GSettings schema is unavailable.", scheme)
            return False
        try:
            logger.info("Writing color-scheme GSettings: %s", scheme)
            self.theme_settings.set_string('color-scheme', scheme)
            logger.info("Color-scheme successfully updated to %s.", scheme)
            return True
        except Exception as e:
            logger.error("Error setting color scheme to %s: %s", scheme, e)
            return False

    def connect_changed(self, callback):
        self.on_changed_callback = callback

    def close(self):
        """Clean up any signal handlers or references held by the ThemeManager."""
        try:
            if self.theme_settings and self._changed_handler_id:
                try:
                    self.theme_settings.disconnect(self._changed_handler_id)
                except Exception:
                    pass
                self._changed_handler_id = None
        finally:
            self.on_changed_callback = None
            self.theme_settings = None

    def _on_setting_changed(self, settings, key):
        if key == 'color-scheme':
            try:
                val = settings.get_string(key)
            except Exception as e:
                logger.error("Error reading updated GSettings value on changed signal: %s", e)
                val = 'default'
            
            logger.info("Received GSettings color-scheme changed notification: %s", val)
            if self.on_changed_callback:
                self.on_changed_callback(val)
