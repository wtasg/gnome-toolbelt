import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time
import json
import tempfile
from pathlib import Path

# Add src folder to module lookup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from menu import IndicatorMenu

class TestIndicatorMenu(unittest.TestCase):
    def setUp(self):
        self.mock_power_manager = MagicMock()
        self.mock_power_manager.get_active_profile.return_value = 'balanced'
        
        self.mock_theme_manager = MagicMock()
        self.mock_theme_manager.get_color_scheme.return_value = 'default'
        
        self.mock_indicator_updater = MagicMock()
        self.mock_wifi_manager = MagicMock()
        
        # Patch show_all to do nothing during initialization
        with patch('gi.repository.Gtk.Menu.show_all'):
            self.menu = IndicatorMenu(
                power_manager=self.mock_power_manager,
                theme_manager=self.mock_theme_manager,
                indicator_updater=self.mock_indicator_updater,
                wifi_manager=self.mock_wifi_manager
            )

    def test_menu_init(self):
        self.assertEqual(self.menu.power_manager, self.mock_power_manager)
        self.assertEqual(self.menu.theme_manager, self.mock_theme_manager)
        self.assertEqual(self.menu.wifi_manager, self.mock_wifi_manager)
        self.assertFalse(self.menu._wifi_monitor_check_inflight)

    def test_check_wifi_transition_status_no_timer(self):
        # If wifi_changing_time is 0, check_wifi_transition_status returns False and sets timer_id to None
        self.menu.wifi_changing_time = 0.0
        self.menu.wifi_monitor_timer_id = 999
        
        keep_timer = self.menu.check_wifi_transition_status()
        self.assertFalse(keep_timer)
        self.assertIsNone(self.menu.wifi_monitor_timer_id)

    @patch('threading.Thread')
    def test_check_wifi_transition_status_inflight_prevention(self, mock_thread_class):
        self.menu.wifi_changing_time = time.time()
        
        # 1. When not inflight, calling check_wifi_transition_status should set inflight to True and start thread
        self.menu._wifi_monitor_check_inflight = False
        keep_timer = self.menu.check_wifi_transition_status()
        
        self.assertTrue(keep_timer)
        self.assertTrue(self.menu._wifi_monitor_check_inflight)
        mock_thread_class.assert_called_once()
        
        # Reset mock
        mock_thread_class.reset_mock()
        
        # 2. When inflight is already True, calling check_wifi_transition_status should return True and NOT spawn a thread
        keep_timer = self.menu.check_wifi_transition_status()
        self.assertTrue(keep_timer)
        self.assertTrue(self.menu._wifi_monitor_check_inflight)
        mock_thread_class.assert_not_called()

    def test_check_wifi_transition_status_thread_finally_clears_inflight(self):
        self.menu.wifi_changing_time = time.time()
        self.menu._wifi_monitor_check_inflight = False
        
        # We want to test that the target bg_check function runs and sets inflight to False in finally block.
        # Let's mock threading.Thread to run the target synchronously.
        target_fn = None
        
        def mock_thread_init(*args, **kwargs):
            nonlocal target_fn
            target_fn = kwargs.get('target')
            return MagicMock()
            
        with patch('threading.Thread', side_effect=mock_thread_init):
            self.menu.check_wifi_transition_status()
            self.assertTrue(self.menu._wifi_monitor_check_inflight)
            
            # Now invoke the target function bg_check synchronously.
            # bg_check will call get_active_wifi, then GLib.idle_add.
            with patch('gi.repository.GLib.idle_add') as mock_idle_add:
                target_fn()
                
            # After target runs, inflight should be reset to False
            self.assertFalse(self.menu._wifi_monitor_check_inflight)

    def test_check_wifi_transition_status_thread_exception_clears_inflight(self):
        self.menu.wifi_changing_time = time.time()
        self.menu._wifi_monitor_check_inflight = False
        
        # Test that even if get_active_wifi raises an exception, the finally block still runs and clears the flag.
        self.mock_wifi_manager.get_active_wifi.side_effect = Exception("D-Bus failure")
        
        target_fn = None
        def mock_thread_init(*args, **kwargs):
            nonlocal target_fn
            target_fn = kwargs.get('target')
            return MagicMock()
            
        with patch('threading.Thread', side_effect=mock_thread_init):
            self.menu.check_wifi_transition_status()
            self.assertTrue(self.menu._wifi_monitor_check_inflight)
            
            # Run target_fn which will raise an exception inside try and be caught, then finally resets it.
            with patch('gi.repository.GLib.idle_add') as mock_idle_add:
                target_fn()
                
            self.assertFalse(self.menu._wifi_monitor_check_inflight)

    @patch('menu.Path.home')
    @patch('gi.repository.Gtk.Menu.get_children')
    def test_refresh_shortcuts_submenu_empty_drawers(self, mock_get_children, mock_home):
        """Test that shortcuts submenu handles missing or empty drawers config."""
        temp_dir = tempfile.TemporaryDirectory()
        mock_home.return_value = Path(temp_dir.name)
        
        # No drawers config file
        mock_get_children.return_value = []
        
        with patch.object(self.menu, 'shortcuts_submenu'):
            self.menu.refresh_shortcuts_submenu()
            # Should not raise exception
            temp_dir.cleanup()

    @patch('menu.Path.home')
    @patch('gi.repository.Gtk.MenuItem')
    @patch('gi.repository.Gtk.Menu')
    @patch('gi.repository.Gtk.SeparatorMenuItem')
    def test_refresh_shortcuts_submenu_with_drawers(self, mock_sep_item, mock_menu_class, mock_menu_item_class, mock_home):
        """Test that shortcuts submenu populates with drawers and shortcuts."""
        temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(temp_dir.name)
        mock_home.return_value = temp_path
        
        # Create test drawers config
        config_file = temp_path / '.config' / 'gnome-toolbelt' / 'drawers.json'
        config_file.parent.mkdir(parents=True, exist_ok=True)
        test_drawers = {
            'Dev': [
                {'name': 'Terminal', 'command': 'gnome-terminal', 'icon': None},
                {'name': 'Editor', 'command': 'code', 'icon': 'code'}
            ],
            'Work': [
                {'name': 'Firefox', 'command': 'firefox', 'icon': 'firefox'}
            ]
        }
        with open(config_file, 'w') as f:
            json.dump(test_drawers, f)
        
        # Mock menu items and submenu
        mock_drawer_item = MagicMock()
        mock_drawer_submenu = MagicMock()
        mock_shortcut_item = MagicMock()
        
        mock_menu_item_class.side_effect = [mock_drawer_item, mock_shortcut_item, mock_shortcut_item, mock_drawer_item, mock_shortcut_item, MagicMock()]
        mock_menu_class.return_value = mock_drawer_submenu
        mock_sep_item.return_value = MagicMock()
        
        with patch.object(self.menu, 'shortcuts_submenu') as mock_submenu:
            mock_submenu.get_children.return_value = []
            self.menu.refresh_shortcuts_submenu()
            
            # Verify append was called (drawers + separator + manage item)
            self.assertTrue(mock_submenu.append.called)
        
        temp_dir.cleanup()

    def test_on_shortcut_clicked_executes_command(self):
        """Test that clicking a shortcut executes its command."""
        with patch('subprocess.Popen') as mock_popen:
            self.menu.on_shortcut_clicked(MagicMock(), 'firefox')
            mock_popen.assert_called_once_with('firefox'.split())

    def test_on_shortcut_clicked_handles_command_with_args(self):
        """Test that shortcut with arguments is executed correctly."""
        with patch('subprocess.Popen') as mock_popen:
            command = 'code /home/user/project'
            self.menu.on_shortcut_clicked(MagicMock(), command)
            mock_popen.assert_called_once_with(command.split())

    def test_on_shortcut_clicked_exception_handling(self):
        """Test that exceptions during shortcut execution are handled gracefully."""
        with patch('subprocess.Popen', side_effect=Exception("Command not found")):
            # Should not raise exception
            self.menu.on_shortcut_clicked(MagicMock(), 'nonexistent-command')

if __name__ == '__main__':
    unittest.main()
