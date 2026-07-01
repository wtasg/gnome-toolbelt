import unittest
from unittest.mock import MagicMock
import sys
import os

# Add src folder to module lookup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from power_manager import PowerManager

class TestPowerManager(unittest.TestCase):
    def setUp(self):
        self.mock_proxy = MagicMock()
        self.power_mgr = PowerManager(proxy=self.mock_proxy)

    def test_get_active_profile_success(self):
        # Setup mock variant return value
        mock_val = MagicMock()
        mock_val.unpack.return_value = 'performance'
        self.mock_proxy.get_cached_property.return_value = mock_val

        profile = self.power_mgr.get_active_profile()
        self.assertEqual(profile, 'performance')
        self.mock_proxy.get_cached_property.assert_called_with('ActiveProfile')

    def test_get_active_profile_failure(self):
        # Trigger exception on property access
        self.mock_proxy.get_cached_property.side_effect = Exception("D-Bus connection lost")
        with self.assertLogs('power_manager', level='ERROR') as cm:
            profile = self.power_mgr.get_active_profile()
        self.assertEqual(profile, 'balanced')
        # Ensure an error about reading ActiveProfile was logged
        self.assertTrue(any('Error reading ActiveProfile' in m for m in cm.output))

    def test_set_active_profile_success(self):
        self.mock_proxy.call_sync.return_value = None
        
        success = self.power_mgr.set_active_profile('power-saver')
        self.assertTrue(success)
        self.mock_proxy.call_sync.assert_called_once()

    def test_set_active_profile_failure(self):
        self.mock_proxy.call_sync.side_effect = Exception("D-Bus access denied")
        with self.assertLogs('power_manager', level='ERROR') as cm:
            success = self.power_mgr.set_active_profile('balanced')
        self.assertFalse(success)
        # Ensure an error about setting the CPU profile was logged
        self.assertTrue(any('Error setting CPU profile' in m for m in cm.output))

if __name__ == '__main__':
    unittest.main()
