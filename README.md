# Gnome Toolbelt

A modular GNOME top-bar indicator daemon for Ubuntu that allows users to quickly toggle CPU power-management profiles (via system D-Bus) and dark/light appearance schemes (via GSettings) directly from the system tray.

And more...

---

## Features

- CPU Profile Management: Toggle between `Performance`, `Balanced (Normal)`, and `Power Saver` modes, interacting with the system `net.hadess.PowerProfiles` D-Bus daemon.
- Appearance Toggles: Seamlessly switch between `Dark Mode`, `Light Mode`, and `System Default` themes (modifying `org.gnome.desktop.interface` color schemes).
- External Settings Shortcuts: Launch GNOME Power Settings and System Monitor directly from the drop-down utility actions.
- Dynamic State Synchronization: Listens for system D-Bus and GSettings changed events to keep tray checkboxes and icons in sync when settings are changed through the OS settings application.
- Memory-Leak Proof: Utilizes state-tracking singletons for dialog instances to guarantee clean resource allocation.
- Self-Cleaning Log System: Built-in rotating logger capped at 512KB to track system states without bloat.

---

## Directory Structure

```text
gnome-bar-app/
├── app/
│   ├── scripts/
│   │   ├── install.sh                              # Installer script
│   │   └── gnome-toolbelt.desktop.template  # Application launcher template
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                                 # App entry point
│   │   ├── power_manager.py                        # DBus interface for CPU profiles
│   │   ├── theme_manager.py                        # GSettings wrapper for themes
│   │   ├── indicator.py                            # AyatanaAppIndicator top-bar wrapper
│   │   └── menu.py                                 # GTK custom dropdown menu layout
│   └── tests/
│       ├── __init__.py
│       ├── test_power_manager.py                   # Power manager tests (mocked D-Bus)
│       └── test_theme_manager.py                   # Theme manager tests (mocked GSettings)
├── README.md
└── .gitignore
```

---

## Prerequisites

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
