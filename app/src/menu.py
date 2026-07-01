import subprocess
import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

logger = logging.getLogger(__name__)

class IndicatorMenu(Gtk.Menu):
    def __init__(self, power_manager, theme_manager, indicator_updater):
        super().__init__()
        self.power_manager = power_manager
        self.theme_manager = theme_manager
        self.indicator_updater = indicator_updater
        self.updating_ui = False
        self._about_dialog = None

        logger.info("Building drop-down menu items...")
        self.build_menu()

        # Connect listeners to manager settings changes
        if self.power_manager:
            self.power_manager.connect_changed(self.on_power_profile_changed_externally)
        if self.theme_manager:
            self.theme_manager.connect_changed(self.on_theme_changed_externally)

        self.sync_all()

    def build_menu(self):
        # --- CPU Profile Section ---
        cpu_menu_item = Gtk.MenuItem.new_with_label("CPU Profile")
        cpu_submenu = Gtk.Menu()
        cpu_menu_item.set_submenu(cpu_submenu)

        self.cpu_items = {}
        profiles = ['performance', 'balanced', 'power-saver']
        labels = {
            'performance': 'Performance',
            'balanced': 'Balanced (Normal)',
            'power-saver': 'Power Saver'
        }

        for p in profiles:
            item = Gtk.CheckMenuItem.new_with_label(labels[p])
            item.connect('activate', self.on_cpu_item_clicked, p)
            cpu_submenu.append(item)
            self.cpu_items[p] = item

        self.append(cpu_menu_item)

        # --- Theme Section ---
        theme_menu_item = Gtk.MenuItem.new_with_label("Appearance")
        theme_submenu = Gtk.Menu()
        theme_menu_item.set_submenu(theme_submenu)

        self.theme_items = {}
        themes = ['prefer-dark', 'prefer-light', 'default']
        theme_labels = {
            'prefer-dark': 'Dark Mode',
            'prefer-light': 'Light Mode',
            'default': 'System Default'
        }

        for t in themes:
            item = Gtk.CheckMenuItem.new_with_label(theme_labels[t])
            item.connect('activate', self.on_theme_item_clicked, t)
            theme_submenu.append(item)
            self.theme_items[t] = item

        self.append(theme_menu_item)

        # --- Separator ---
        self.append(Gtk.SeparatorMenuItem())

        # --- Other Tasks Section ---
        power_settings_item = Gtk.MenuItem.new_with_label("Power Settings")
        power_settings_item.connect('activate', self.open_power_settings)
        self.append(power_settings_item)

        sys_monitor_item = Gtk.MenuItem.new_with_label("System Monitor")
        sys_monitor_item.connect('activate', self.open_system_monitor)
        self.append(sys_monitor_item)

        # --- Separator ---
        self.append(Gtk.SeparatorMenuItem())

        # --- About ---
        about_item = Gtk.MenuItem.new_with_label("About")
        about_item.connect('activate', self.show_about_dialog)
        self.append(about_item)

        # --- Quit ---
        quit_item = Gtk.MenuItem.new_with_label("Quit")
        quit_item.connect('activate', self.quit)
        self.append(quit_item)

        self.show_all()

    # --- Callbacks ---

    def on_cpu_item_clicked(self, item, profile_name):
        if self.updating_ui or not self.power_manager:
            return
        
        if item.get_active():
            logger.info("CPU profile menu selection: %s", profile_name)
            success = self.power_manager.set_active_profile(profile_name)
            if not success:
                logger.warning("Failed to set CPU profile, syncing UI back to current state.")
                self.sync_power_ui()
        else:
            if self.power_manager.get_active_profile() == profile_name:
                self.sync_power_ui()

    def on_theme_item_clicked(self, item, theme_name):
        if self.updating_ui or not self.theme_manager:
            return

        if item.get_active():
            logger.info("Theme menu selection: %s", theme_name)
            success = self.theme_manager.set_color_scheme(theme_name)
            if not success:
                logger.warning("Failed to set theme variant, syncing UI back to current state.")
                self.sync_theme_ui()
        else:
            if self.theme_manager.get_color_scheme() == theme_name:
                self.sync_theme_ui()

    def on_power_profile_changed_externally(self, new_profile):
        logger.info("External change in CPU profile detected. Scheduling UI sync...")
        GLib.idle_add(self.sync_power_ui)

    def on_theme_changed_externally(self, new_theme):
        logger.info("External change in theme detected. Scheduling UI sync...")
        GLib.idle_add(self.sync_theme_ui)

    # --- UI Sync ---

    def sync_power_ui(self):
        if not self.power_manager:
            return
        
        active = self.power_manager.get_active_profile()
        logger.info("Syncing CPU Profile checkmark UI with: %s", active)
        self.updating_ui = True
        for p, item in self.cpu_items.items():
            item.set_active(p == active)
        self.updating_ui = False
        
        self.indicator_updater(active)

    def sync_theme_ui(self):
        if not self.theme_manager:
            return

        active = self.theme_manager.get_color_scheme()
        logger.info("Syncing Appearance checkmark UI with: %s", active)
        self.updating_ui = True
        for t, item in self.theme_items.items():
            item.set_active(t == active)
        self.updating_ui = False

    def sync_all(self):
        self.sync_power_ui()
        self.sync_theme_ui()

    # --- Utility Launchers ---

    def open_power_settings(self, _item):
        try:
            logger.info("Spawning Power Settings (gnome-control-center power)...")
            subprocess.Popen(["gnome-control-center", "power"])
        except Exception as e:
            logger.error("Error opening power settings: %s", e)

    def open_system_monitor(self, _item):
        try:
            logger.info("Spawning System Monitor (gnome-system-monitor)...")
            subprocess.Popen(["gnome-system-monitor"])
        except Exception as e:
            logger.error("Error opening system monitor: %s", e)

    def show_about_dialog(self, _item):
        if self._about_dialog:
            logger.info("About Dialog instance already active. Presenting existing window.")
            self._about_dialog.present()
            return

        logger.info("Creating new About Dialog instance.")
        about = Gtk.AboutDialog()
        about.set_program_name("Toolbelt")
        about.set_version("1.0.0")
        about.set_comments("A simple utility to switch CPU power profiles and theme appearance from the GNOME top bar.")
        about.set_website("https://github.com/wtasg/gnome-toolbelt")
        about.set_authors(["Anubhav Saini (github.com/wtasg)"])
        about.set_logo_icon_name("preferences-system-power-symbolic")
        
        def on_response(dialog, response_id):
            logger.info("Destroying About Dialog.")
            dialog.destroy()
            self._about_dialog = None

        about.connect("response", on_response)
        about.show()
        self._about_dialog = about

    def quit(self, _item):
        logger.info("Quit item activated. Terminating GTK loop.")
        Gtk.main_quit()
