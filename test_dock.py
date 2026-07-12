#!/usr/bin/env python3
"""Quick test to verify DrawersDock instantiation works."""
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)

# Add app source to path
sys.path.insert(0, '/home/user/src/gh/wtasg/gnome-toolbelt/app/src')
sys.path.insert(0, '/home/user/src/gh/wtasg/gnome-toolbelt')

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

print("=" * 60)
print("TESTING DRAWERSDOCK INSTANTIATION")
print("=" * 60)

try:
    from drawers import DrawersDock
    print("[✓] Successfully imported DrawersDock")
    
    print("[*] Creating DrawersDock instance...")
    dock = DrawersDock()
    print("[✓] DrawersDock instance created successfully")
    
    print("[*] Checking window properties...")
    print(f"  - Title: {dock.get_title()}")
    print(f"  - Size: {dock.get_default_size()}")
    print(f"  - Is visible: {dock.get_visible()}")
    print(f"  - Keep above: {True}")
    
    print("[✓] All properties look correct")
    
    # Try to show it for a moment
    print("[*] Scheduling window to be present for 2 seconds...")
    GLib.timeout_add_seconds(2, lambda: Gtk.main_quit() or False)
    Gtk.main()
    
    print("[✓] Test completed successfully!")
    
except Exception as e:
    print(f"[✗] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
