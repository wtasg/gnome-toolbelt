import subprocess
import logging
import threading
import time
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

logger = logging.getLogger(__name__)

class IndicatorMenu(Gtk.Menu):
    def __init__(self, power_manager, theme_manager, indicator_updater, wifi_manager=None):
        super().__init__()
        self.power_manager = power_manager
        self.theme_manager = theme_manager
        self.wifi_manager = wifi_manager
        self.indicator_updater = indicator_updater
        self.updating_ui = False
        self._about_dialog = None
        self.wifi_changing_to_uuid = None
        self.wifi_changing_time = 0.0
        self.wifi_monitor_timer_id = None
        self._wifi_fetching = False

        logger.info("Building drop-down menu items...")
        self.build_menu()

        # Connect destroy signal to clean up timer
        self.connect('destroy', self.on_destroy)

        # Connect listeners to manager settings changes
        if self.power_manager:
            self.power_manager.connect_changed(self.on_power_profile_changed_externally)
        if self.theme_manager:
            self.theme_manager.connect_changed(self.on_theme_changed_externally)

        self.sync_all()
        self.connect('show', self.on_menu_show)

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

        # --- Wi-Fi Section ---
        if self.wifi_manager:
            wifi_menu_item = Gtk.MenuItem.new_with_label("Wi-Fi")
            self.wifi_submenu = Gtk.Menu()
            wifi_menu_item.set_submenu(self.wifi_submenu)
            self.append(wifi_menu_item)

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

    def on_menu_show(self, _menu):
        logger.info("Main menu shown. Refreshing Wi-Fi submenu...")
        self.refresh_wifi_submenu()

    def refresh_wifi_submenu(self):
        if not self.wifi_manager or not hasattr(self, 'wifi_submenu'):
            return
            
        if self._wifi_fetching:
            logger.debug("Wi-Fi fetch already in progress, skipping redundant refresh request.")
            return
            
        self._wifi_fetching = True
        
        def run_fetch():
            try:
                saved_nets = self.wifi_manager.get_saved_wifi_connections()
                active_uuid, active_path = self.wifi_manager.get_active_wifi()
                GLib.idle_add(self.on_wifi_fetch_completed, saved_nets, active_uuid, active_path)
            except Exception as e:
                logger.error("Error fetching Wi-Fi details in background: %s", e)
                GLib.idle_add(self.on_wifi_fetch_failed)
                
        threading.Thread(target=run_fetch, daemon=True).start()

    def on_wifi_fetch_completed(self, saved_nets, active_uuid, active_path):
        self._wifi_fetching = False
        if not hasattr(self, 'wifi_submenu'):
            return
            
        logger.info("Populating Wi-Fi submenu with fetched data...")
        # Clear previous menu items
        for child in self.wifi_submenu.get_children():
            self.wifi_submenu.remove(child)
            child.destroy()
            
        now = time.time()
        
        # Check changing state expiration/resolution
        if self.wifi_changing_time > 0:
            if now - self.wifi_changing_time >= 30:
                logger.info("Wi-Fi changing state timed out.")
                self.wifi_changing_to_uuid = None
                self.wifi_changing_time = 0.0
            elif active_uuid == self.wifi_changing_to_uuid:
                logger.info("Wi-Fi changing state resolved (connected to target).")
                self.wifi_changing_to_uuid = None
                self.wifi_changing_time = 0.0
            elif self.wifi_changing_to_uuid is None and active_uuid is None:
                logger.info("Wi-Fi changing state resolved (disconnected).")
                self.wifi_changing_to_uuid = None
                self.wifi_changing_time = 0.0
                
        is_changing = (self.wifi_changing_time > 0)
        effective_active_uuid = self.wifi_changing_to_uuid if is_changing else active_uuid
        
        # Prepend a Changing status item at the top of the submenu if in transition
        if is_changing:
            status_label = "Changing..." if self.wifi_changing_to_uuid is not None else "Disconnecting..."
            status_item = Gtk.MenuItem.new_with_label(status_label)
            status_item.set_sensitive(False)
            self.wifi_submenu.append(status_item)
            self.wifi_submenu.append(Gtk.SeparatorMenuItem())
            
        if not saved_nets:
            empty_item = Gtk.MenuItem.new_with_label("No saved Wi-Fi networks found")
            empty_item.set_sensitive(False)
            self.wifi_submenu.append(empty_item)
        else:
            self.updating_ui = True
            for net in saved_nets:
                is_active = (net['uuid'] == effective_active_uuid)
                
                label_text = net['id'] or net['uuid'] or "Unknown Network"
                if is_changing and net['uuid'] == self.wifi_changing_to_uuid:
                    label_text += " (changing...)"
                    
                item = Gtk.CheckMenuItem.new_with_label(label_text)
                item.set_active(is_active)
                item.set_sensitive(not is_changing)
                item.connect('activate', self.on_wifi_item_clicked, net['path'], net['uuid'])
                self.wifi_submenu.append(item)
            self.updating_ui = False
            
            # Display Disconnect item if active or if we are actively changing
            if active_path or (is_changing and self.wifi_changing_to_uuid is not None):
                self.wifi_submenu.append(Gtk.SeparatorMenuItem())
                
                disconnect_label = "Disconnect"
                if is_changing and self.wifi_changing_to_uuid is None:
                    disconnect_label = "Disconnecting..."
                    
                disconnect_item = Gtk.MenuItem.new_with_label(disconnect_label)
                if active_path:
                    disconnect_item.connect('activate', self.on_wifi_disconnect_clicked, active_path)
                else:
                    disconnect_item.set_sensitive(False)
                
                if is_changing and self.wifi_changing_to_uuid is None:
                    disconnect_item.set_sensitive(False)
                    
                self.wifi_submenu.append(disconnect_item)
                
        self.wifi_submenu.show_all()

    def on_wifi_fetch_failed(self):
        self._wifi_fetching = False

    def on_wifi_item_clicked(self, item, connection_path, connection_uuid):
        if self.updating_ui or not self.wifi_manager:
            return
            
        if item.get_active():
            logger.info("User requested activation of Wi-Fi: %s (UUID: %s)", connection_path, connection_uuid)
            
            # Start Changing state
            self.wifi_changing_to_uuid = connection_uuid
            self.wifi_changing_time = time.time()
            self.start_wifi_monitor_timer()
            
            # Disable other menu items and update clicked label
            self.updating_ui = True
            
            # Turn off checkmarks on all other Wi-Fi items and disable all items
            for child in self.wifi_submenu.get_children():
                if isinstance(child, Gtk.CheckMenuItem):
                    if child != item:
                        child.set_active(False)
                child.set_sensitive(False)
                
            original_label = item.get_label()
            item.set_label(f"Connecting to {original_label}...")
            
            self.updating_ui = False
            
            def run_activation():
                success = self.wifi_manager.activate_connection(connection_path)
                GLib.idle_add(self.on_activation_completed, success, original_label, item)
                
            threading.Thread(target=run_activation, daemon=True).start()

    def on_activation_completed(self, success, original_label, item):
        logger.info("Wi-Fi activation completed. Success: %s", success)
        item.set_label(original_label)
        if not success:
            self.wifi_changing_to_uuid = None
            self.wifi_changing_time = 0.0
            if self.wifi_monitor_timer_id is not None:
                GLib.source_remove(self.wifi_monitor_timer_id)
                self.wifi_monitor_timer_id = None
        self.refresh_wifi_submenu()

    def on_wifi_disconnect_clicked(self, item, active_connection_path):
        if not self.wifi_manager:
            return
            
        # If the path is not provided, try to resolve it now dynamically
        if not active_connection_path or active_connection_path == '/':
            _, active_connection_path = self.wifi_manager.get_active_wifi()
            
        if not active_connection_path or active_connection_path == '/':
            logger.warning("Cannot disconnect: no active Wi-Fi connection path found.")
            return

        logger.info("User requested deactivation of active connection: %s", active_connection_path)
        
        # Start Changing state (disconnecting)
        self.wifi_changing_to_uuid = None
        self.wifi_changing_time = time.time()
        self.start_wifi_monitor_timer()
        
        # Disable all items in the submenu
        for child in self.wifi_submenu.get_children():
            child.set_sensitive(False)
            
        original_label = item.get_label()
        item.set_label("Disconnecting...")
        
        def run_deactivation():
            success = self.wifi_manager.deactivate_connection(active_connection_path)
            GLib.idle_add(self.on_deactivation_completed, success, original_label, item)
            
        threading.Thread(target=run_deactivation, daemon=True).start()

    def on_deactivation_completed(self, success, original_label, item):
        logger.info("Wi-Fi deactivation completed. Success: %s", success)
        item.set_label(original_label)
        if not success:
            self.wifi_changing_to_uuid = None
            self.wifi_changing_time = 0.0
            if self.wifi_monitor_timer_id is not None:
                GLib.source_remove(self.wifi_monitor_timer_id)
                self.wifi_monitor_timer_id = None
        self.refresh_wifi_submenu()

    def start_wifi_monitor_timer(self):
        if self.wifi_monitor_timer_id is not None:
            return
        logger.info("Starting background Wi-Fi transition monitor timer...")
        self.wifi_monitor_timer_id = GLib.timeout_add_seconds(1, self.check_wifi_transition_status)

    def check_wifi_transition_status(self):
        if self.wifi_changing_time == 0:
            self.wifi_monitor_timer_id = None
            return False # Stop timer
            
        def bg_check():
            try:
                active_uuid, active_path = self.wifi_manager.get_active_wifi() if self.wifi_manager else (None, None)
                GLib.idle_add(self.on_transition_status_checked, active_uuid, active_path)
            except Exception as e:
                logger.error("Error in background transition status check: %s", e)

        threading.Thread(target=bg_check, daemon=True).start()
        return True # Keep timer running

    def on_transition_status_checked(self, active_uuid, active_path):
        if self.wifi_changing_time == 0:
            # Already resolved or cancelled in the meantime
            return
            
        now = time.time()
        resolved = False
        if now - self.wifi_changing_time >= 30:
            logger.info("Wi-Fi changing state timed out via monitor.")
            self.wifi_changing_to_uuid = None
            self.wifi_changing_time = 0.0
            resolved = True
        elif active_uuid == self.wifi_changing_to_uuid:
            logger.info("Wi-Fi changing state resolved (connected to target) via monitor.")
            self.wifi_changing_to_uuid = None
            self.wifi_changing_time = 0.0
            resolved = True
        elif self.wifi_changing_to_uuid is None and active_uuid is None:
            logger.info("Wi-Fi changing state resolved (disconnected) via monitor.")
            self.wifi_changing_to_uuid = None
            self.wifi_changing_time = 0.0
            resolved = True
            
        if resolved:
            self.refresh_wifi_submenu()
            if self.wifi_monitor_timer_id is not None:
                GLib.source_remove(self.wifi_monitor_timer_id)
                self.wifi_monitor_timer_id = None

    def on_destroy(self, _widget):
        logger.info("Destroying IndicatorMenu, cleaning up timers and callbacks.")
        if self.wifi_monitor_timer_id is not None:
            GLib.source_remove(self.wifi_monitor_timer_id)
            self.wifi_monitor_timer_id = None
