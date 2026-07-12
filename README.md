# Gnome Toolbelt

A modular GNOME top-bar indicator daemon for Ubuntu that allows users to quickly toggle CPU power-management profiles (via system D-Bus) and dark/light appearance schemes (via GSettings) directly from the system tray.

And more...

---

## Features

- CPU Profile Management: Toggle between `Performance`, `Balanced (Normal)`, and `Power Saver` modes, interacting with the system `net.hadess.PowerProfiles` D-Bus daemon.
- Appearance Toggles: Seamlessly switch between `Dark Mode`, `Light Mode`, and `System Default` themes (modifying `org.gnome.desktop.interface` color schemes).
- Wi-Fi Connection Management: View and switch between saved Wi-Fi networks directly from the menu.
- Custom Shortcuts & Drawers:
  - Organize custom shortcuts into named drawers (e.g., "Dev", "Work")
  - Drag .desktop files from your desktop or applications folder to the floating dock to auto-import shortcuts
  - Access shortcuts from two places:
    - Floating Dock: Compact always-on-top window showing drawer buttons; click to execute shortcuts or manage them
    - Indicator Menu: "Shortcuts" submenu showing all drawers and their shortcuts; click to run or manage
  - Full CRUD operations: add/edit/delete drawers and shortcuts in the DrawersManager UI
  - Config persisted to `~/.config/gnome-toolbelt/drawers.json`
- External Settings Shortcuts: Launch GNOME Power Settings and System Monitor directly from the drop-down utility actions.
- Dynamic State Synchronization: Listens for system D-Bus and GSettings changed events to keep tray checkmarks and icons in sync when settings are changed through the OS settings application.
- Memory-Leak Proof: Utilizes state-tracking singletons for dialog instances to guarantee clean resource allocation.
- Self-Cleaning Log System: Built-in rotating logger capped at 512KB to track system states without bloat.

---

## Directory Structure

```text
gnome-bar-app/
├── app/
│   ├── scripts/
│   │   ├── install.sh                              # Installer script
│   │   ├── uninstall.sh                            # Uninstaller script
│   │   └── gnome-toolbelt.desktop.template  # Application launcher template
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                                 # App entry point
│   │   ├── indicator.py                            # AyatanaAppIndicator top-bar wrapper
│   │   ├── menu.py                                 # GTK dropdown menu layout + shortcuts submenu
│   │   ├── power_manager.py                        # DBus interface for CPU profiles
│   │   ├── theme_manager.py                        # GSettings wrapper for themes
│   │   ├── wifi_manager.py                         # NetworkManager D-Bus interface for Wi-Fi
│   │   └── drawers.py                              # Shortcuts & drawers UI (DrawersManager + DrawersDock)
│   └── tests/
│       ├── __init__.py
│       ├── test_integration_lifecycle.py           # Full lifecycle tests
│       ├── test_menu.py                            # Menu and shortcuts tests
│       ├── test_power_manager.py                   # Power manager tests (mocked D-Bus)
│       ├── test_theme_manager.py                   # Theme manager tests (mocked GSettings)
│       ├── test_wifi_manager.py                    # Wi-Fi manager tests (mocked NetworkManager)
│       └── test_drawers.py                         # Drawers & dock tests
├── README.md
├── architecture.md                                 # System architecture & design
└── .gitignore
```

---

## Usage

### Quick Settings

Click the indicator icon in the GNOME top bar to open the menu and:

- Toggle CPU profile (Performance / Balanced / Power Saver)
- Toggle appearance theme (Dark / Light / System Default)
- Switch Wi-Fi networks
- Launch Power Settings or System Monitor

### Shortcuts & Drawers

#### Access Shortcuts

1. From the Indicator Menu:
   - Click the indicator → Hover over "Shortcuts"
   - See all drawers (e.g., "Dev", "Work") with their shortcuts
   - Click a shortcut name to execute it immediately
   - Click "Manage Shortcuts..." to open the management UI

2. From the Floating Dock:
   - Click "Shortcuts" in the indicator menu → floating dock appears
   - See drawer buttons (e.g., `[✕] [+] [Dev] [Work]`)
   - Click a drawer button to open the full DrawersManager UI
   - Click `+` to add a new drawer
   - Click `✕` to close the dock (click "Shortcuts" again to reopen)
   - Drag & drop .desktop files from your desktop or file manager onto the dock to auto-import shortcuts

#### Manage Shortcuts

Click "Manage Shortcuts..." or the `+` button in the dock to open the DrawersManager window:

- Add Drawer: Click `+ Add Drawer` button, enter drawer name
- Delete Drawer: Click `Delete Drawer` in the drawer header, confirm
- Add Shortcut: Click `+ Add Shortcut` in a drawer, fill in:
  - Name (e.g., "Firefox")
  - Command (e.g., `firefox`)
  - Icon name (optional, e.g., "firefox")
  - Optionally create a `.desktop` file in `~/.local/share/applications/`
- Delete Shortcut: Click `Remove Shortcut` on a shortcut row, confirm
- Reorder Shortcuts: Drag shortcuts within the same drawer to reorder them
- Drag .desktop Files: Drop files from your desktop onto the drawer list to auto-import

#### Config Storage

Shortcuts are persisted to: `~/.config/gnome-toolbelt/drawers.json`

Example format:

```json
{
  "Dev": [
    {"name": "Terminal", "command": "gnome-terminal", "icon": "utilities-terminal"},
    {"name": "VS Code", "command": "code", "icon": "code"}
  ],
  "Work": [
    {"name": "Firefox", "command": "firefox", "icon": "firefox"}
  ]
}
```

---

Ensure GObject introspection and AppIndicator system libraries are installed on your machine. On Ubuntu/Debian-based systems, run:

```bash
sudo apt update
sudo apt install python3 python3-gi libayatana-appindicator3-dev
```

---

## Installation & Deployment

You can install the application launcher wrapper and configure it to autostart upon login:

Run the installer

```bash
   chmod +x app/scripts/install.sh
   ./app/scripts/install.sh
   # ./app/scripts/uninstall.sh # for uninstallation
```

Start the daemon in the background immediately

```bash
   nohup gnome-toolbelt >/dev/null 2>&1 &
```

Alternatively, search for Gnome Toolbelt in your desktop's application launcher.

---

## Testing & Verification

The suite contains mock-driven unit tests that run headlessly (no D-Bus connection or GUI interface required), making them perfectly suited for local or CI verification pipelines:

```bash
# Run unit tests from workspace root
python3 -m unittest discover -s app/tests
```

---

## Logging & Debugging

The application prints warnings to standard error (captured by `systemd` / `journald` user units) and maintains a rotating log at: `~/.cache/gnome-toolbelt.log`

Log rotation parameters are capped at 512 KB with 1 backup rotation file.
