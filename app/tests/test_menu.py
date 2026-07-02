import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

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
        
        def mock_thread_init(target, daemon):
            nonlocal target_fn
            target_fn = target
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
        def mock_thread_init(target, daemon):
            nonlocal target_fn
            target_fn = target
            return MagicMock()
            
        with patch('threading.Thread', side_effect=mock_thread_init):
            self.menu.check_wifi_transition_status()
            self.assertTrue(self.menu._wifi_monitor_check_inflight)
            
            # Run target_fn which will raise an exception inside try and be caught, then finally resets it.
            with patch('gi.repository.GLib.idle_add') as mock_idle_add:
                target_fn()
                
            self.assertFalse(self.menu._wifi_monitor_check_inflight)

if __name__ == '__main__':
    unittest.main()
