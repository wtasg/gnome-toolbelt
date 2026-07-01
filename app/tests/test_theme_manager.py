import unittest
from unittest.mock import MagicMock
import sys
import os

# Add src folder to module lookup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from theme_manager import ThemeManager

class TestThemeManager(unittest.TestCase):
    def setUp(self):
        self.mock_settings = MagicMock()
        self.theme_mgr = ThemeManager(settings=self.mock_settings)

    def test_get_color_scheme_success(self):
        self.mock_settings.get_string.return_value = 'prefer-dark'
        
        scheme = self.theme_mgr.get_color_scheme()
        self.assertEqual(scheme, 'prefer-dark')
        self.mock_settings.get_string.assert_called_with('color-scheme')

    def test_get_color_scheme_failure(self):
        self.mock_settings.get_string.side_effect = Exception("GSettings schema corrupt")
        with self.assertLogs('theme_manager', level='ERROR') as cm:
            scheme = self.theme_mgr.get_color_scheme()
        self.assertEqual(scheme, 'default')
        # Ensure an error about reading GSettings was logged
        self.assertTrue(any('Error reading color-scheme' in m for m in cm.output))

    def test_set_color_scheme_success(self):
        success = self.theme_mgr.set_color_scheme('prefer-light')
        self.assertTrue(success)
        self.mock_settings.set_string.assert_called_with('color-scheme', 'prefer-light')

    def test_set_color_scheme_failure(self):
        self.mock_settings.set_string.side_effect = Exception("ReadOnly setting")
        with self.assertLogs('theme_manager', level='ERROR') as cm:
            success = self.theme_mgr.set_color_scheme('prefer-dark')
        self.assertFalse(success)
        # Ensure an error about setting the color scheme was logged
        self.assertTrue(any('Error setting color scheme' in m for m in cm.output))

if __name__ == '__main__':
    unittest.main()
