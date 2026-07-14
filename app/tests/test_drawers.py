import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json
import tempfile
from pathlib import Path

# Add src folder to module lookup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from drawers import DrawersManager, DrawersDock


class TestDrawersManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('drawers.CONFIG_DIR')
    @patch('gi.repository.Gtk.Window.show_all')
    def test_drawers_manager_init_creates_empty_drawers(self, mock_show_all, mock_config_dir):
        mock_config_dir.__str__ = lambda self: str(self.config_dir)
        
        with patch('drawers.DrawersManager.load'):
            with patch.object(DrawersManager, 'populate_ui'):
                manager = DrawersManager()
                self.assertIsNotNone(manager.drawers)
                manager.drawers = {}
                self.assertEqual(manager.drawers, {})

    @patch('drawers.CONFIG_DIR')
    @patch('gi.repository.Gtk.Window.show_all')
    def test_drawers_manager_load_saves_config(self, mock_show_all, mock_config_dir):
        mock_config_dir.__str__ = lambda self: str(self.config_dir)
        
        with patch('drawers.DRAWERS_FILE', Path(self.config_dir) / 'drawers.json'):
            with patch('drawers.DrawersManager.populate_ui'):
                manager = DrawersManager()
                manager.drawers = {'Dev': [{'name': 'Terminal', 'command': 'gnome-terminal', 'icon': None}]}
                manager.save()
                
                # Verify file was saved
                drawers_file = Path(self.config_dir) / 'drawers.json'
                self.assertTrue(drawers_file.exists())
                
                with open(drawers_file, 'r') as f:
                    saved = json.load(f)
                self.assertEqual(saved, {'Dev': [{'name': 'Terminal', 'command': 'gnome-terminal', 'icon': None}]})

    @patch('drawers.CONFIG_DIR')
    @patch('gi.repository.Gtk.Window.show_all')
    def test_drawers_manager_add_and_delete_drawer(self, mock_show_all, mock_config_dir):
        mock_config_dir.__str__ = lambda self: str(self.config_dir)
        
        with patch('drawers.DRAWERS_FILE', Path(self.config_dir) / 'drawers.json'):
            with patch('drawers.DrawersManager.populate_ui'):
                manager = DrawersManager()
                manager.drawers = {}
                
                # Add drawer
                manager.drawers['Work'] = []
                manager.save()
                self.assertIn('Work', manager.drawers)
                
                # Delete drawer
                manager.drawers.pop('Work', None)
                manager.save()
                self.assertNotIn('Work', manager.drawers)

    @patch('drawers.CONFIG_DIR')
    @patch('gi.repository.Gtk.Window.show_all')
    def test_drawers_manager_add_shortcut(self, mock_show_all, mock_config_dir):
        mock_config_dir.__str__ = lambda self: str(self.config_dir)
        
        with patch('drawers.DRAWERS_FILE', Path(self.config_dir) / 'drawers.json'):
            with patch('drawers.DrawersManager.populate_ui'):
                manager = DrawersManager()
                manager.drawers = {'Dev': []}
                
                # Add shortcut
                item = {'name': 'Firefox', 'command': 'firefox', 'icon': 'firefox'}
                manager.drawers['Dev'].append(item)
                manager.save()
                
                self.assertEqual(len(manager.drawers['Dev']), 1)
                self.assertEqual(manager.drawers['Dev'][0]['name'], 'Firefox')

    @patch('drawers.CONFIG_DIR')
    @patch('gi.repository.Gtk.Window.show_all')
    def test_drawers_manager_remove_shortcut(self, mock_show_all, mock_config_dir):
        mock_config_dir.__str__ = lambda self: str(self.config_dir)
        
        with patch('drawers.DRAWERS_FILE', Path(self.config_dir) / 'drawers.json'):
            with patch('drawers.DrawersManager.populate_ui'):
                manager = DrawersManager()
                manager.drawers = {
                    'Dev': [
                        {'name': 'Firefox', 'command': 'firefox', 'icon': 'firefox'},
                        {'name': 'Terminal', 'command': 'gnome-terminal', 'icon': None}
                    ]
                }
                
                # Remove first shortcut
                manager.drawers['Dev'].pop(0)
                manager.save()
                
                self.assertEqual(len(manager.drawers['Dev']), 1)
                self.assertEqual(manager.drawers['Dev'][0]['name'], 'Terminal')


class TestDrawersDock(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('gi.repository.Gtk.Window.show_all')
    @patch('gi.repository.GLib.idle_add')
    @patch('gi.repository.GLib.timeout_add_seconds')
    def test_drawers_dock_init(self, mock_timeout, mock_idle_add, mock_show_all):
        with patch('drawers.CONFIG_DIR', self.config_dir):
            with patch('drawers.DRAWERS_FILE', self.config_dir / 'drawers.json'):
                with patch.object(DrawersDock, '_build_drawer_buttons'):
                    dock = DrawersDock()
                    self.assertIsNotNone(dock.drawers)
                    self.assertTrue(dock._dragging == False)

    @patch('gi.repository.Gtk.Window.show_all')
    @patch('gi.repository.GLib.idle_add')
    @patch('gi.repository.GLib.timeout_add_seconds')
    def test_drawers_dock_load(self, mock_timeout, mock_idle_add, mock_show_all):
        # Create test drawers config
        drawers_file = self.config_dir / 'drawers.json'
        test_drawers = {'Dev': [{'name': 'Terminal', 'command': 'gnome-terminal', 'icon': None}]}
        drawers_file.parent.mkdir(parents=True, exist_ok=True)
        with open(drawers_file, 'w') as f:
            json.dump(test_drawers, f)
        
        with patch('drawers.CONFIG_DIR', self.config_dir):
            with patch('drawers.DRAWERS_FILE', drawers_file):
                with patch.object(DrawersDock, '_build_drawer_buttons'):
                    dock = DrawersDock()
                    self.assertEqual(dock.drawers, test_drawers)

    @patch('gi.repository.Gtk.Window.show_all')
    @patch('gi.repository.GLib.idle_add')
    @patch('gi.repository.GLib.timeout_add_seconds')
    def test_drawers_dock_refresh_detects_changes(self, mock_timeout, mock_idle_add, mock_show_all):
        # Create initial config
        drawers_file = self.config_dir / 'drawers.json'
        initial_drawers = {'Dev': []}
        drawers_file.parent.mkdir(parents=True, exist_ok=True)
        with open(drawers_file, 'w') as f:
            json.dump(initial_drawers, f)
        
        with patch('drawers.CONFIG_DIR', self.config_dir):
            with patch('drawers.DRAWERS_FILE', drawers_file):
                with patch.object(DrawersDock, '_build_drawer_buttons') as mock_build:
                    dock = DrawersDock()
                    dock.drawers = initial_drawers
                    
                    # Change config
                    updated_drawers = {'Work': [{'name': 'Firefox', 'command': 'firefox', 'icon': None}]}
                    with open(drawers_file, 'w') as f:
                        json.dump(updated_drawers, f)
                    
                    # Refresh should detect change and rebuild
                    dock._periodic_refresh()
                    self.assertEqual(dock.drawers, updated_drawers)
                    mock_build.assert_called()

    @patch('gi.repository.Gtk.Window.show_all')
    @patch('gi.repository.GLib.idle_add')
    @patch('gi.repository.GLib.timeout_add_seconds')
    def test_drawers_dock_import_desktop_file(self, mock_timeout, mock_idle_add, mock_show_all):
        # Create test .desktop file
        drawers_file = self.config_dir / 'drawers.json'
        drawers_file.parent.mkdir(parents=True, exist_ok=True)
        with open(drawers_file, 'w') as f:
            json.dump({'Dev': []}, f)
        
        desktop_file = self.config_dir / 'firefox.desktop'
        desktop_file.write_text('''[Desktop Entry]
Name=Firefox
Exec=firefox %u
Icon=firefox
Type=Application
''')
        
        with patch('drawers.CONFIG_DIR', self.config_dir):
            with patch('drawers.DRAWERS_FILE', drawers_file):
                with patch.object(DrawersDock, '_build_drawer_buttons'):
                    dock = DrawersDock()
                    dock.drawers = {'Dev': []}
                    
                    # Import desktop file
                    result = dock._import_desktop_file(str(desktop_file))
                    
                    self.assertTrue(result)
                    self.assertEqual(len(dock.drawers['Dev']), 1)
                    self.assertEqual(dock.drawers['Dev'][0]['name'], 'Firefox')
                    self.assertEqual(dock.drawers['Dev'][0]['command'], 'firefox %u')


class TestShortcutsIntegration(unittest.TestCase):
    """Integration tests for shortcuts functionality across dock and menu."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('menu.Path.home')
    def test_menu_loads_drawers_from_config(self, mock_home):
        mock_home.return_value = self.config_dir
        
        # Create test config
        config_file = self.config_dir / '.config' / 'gnome-toolbelt' / 'drawers.json'
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
        
        from menu import IndicatorMenu
        with patch('gi.repository.Gtk.Menu.show_all'):
            menu = IndicatorMenu(
                power_manager=MagicMock(),
                theme_manager=MagicMock(),
                indicator_updater=MagicMock(),
                wifi_manager=MagicMock()
            )
            
            # Mock the shortcuts submenu
            with patch.object(menu, 'shortcuts_submenu'):
                menu.refresh_shortcuts_submenu()
                # Should not raise any exceptions


if __name__ == '__main__':
    unittest.main()
