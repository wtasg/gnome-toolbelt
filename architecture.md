# Gnome Toolbelt - System Architecture

## Overview

Gnome Toolbelt is a modular GNOME top-bar indicator daemon that provides quick access to system settings (CPU profiles, themes, Wi-Fi) and custom shortcuts organized into "drawers". The architecture is built on three pillars:

1. Modular Managers — Abstracted system interfaces (power, theme, WiFi) via D-Bus/GSettings
2. UI Layer — GTK3-based indicator menu, floating dock, and drawer manager
3. Data Persistence — JSON-based configuration for shortcuts and drawer organization

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    GNOME Top Bar                                │
│                                                                 │
│  [Indicator Icon] ◄──── AyatanaAppIndicator3 Wrapper           │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ (GTK signals)
                              ▼
        ┌─────────────────────────────────────────┐
        │      IndicatorMenu (menu.py)            │
        │  ┌─────────────────────────────────┐   │
        │  │ CPU Profile (submenu)           │   │
        │  │ Appearance (submenu)            │   │
        │  │ Wi-Fi (submenu)                 │   │
        │  │ ────────────────────────────    │   │
        │  │ Shortcuts ◄─────────────┐       │   │ ◄─ reads drawers.json
        │  │   ├─ Dev                │       │   │
        │  │   │  ├─ Terminal        │       │   │
        │  │   │  └─ VS Code         │       │   │
        │  │   └─ Work               │       │   │
        │  │      └─ Firefox         │       │   │
        │  │ ────────────────────────        │   │
        │  │ Manage Shortcuts... ──────┐     │   │
        │  │ Power Settings            │     │   │
        │  │ System Monitor            │     │   │
        │  │ [Separator]               │     │   │
        │  │ About / Quit              │     │   │
        │  └─────────────────────────────┘   │
        └─────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ PowerManager │  │ThemeManager  │  │WiFiManager   │
    │   (D-Bus)    │  │ (GSettings)  │  │  (D-Bus)     │
    └──────────────┘  └──────────────┘  └──────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  PowerProf   │  │ GTK Settings │  │NetworkManager│
    │  D-Bus Svc   │  │   (GSettings)│  │  D-Bus Svc   │
    └──────────────┘  └──────────────┘  └──────────────┘
```

When user clicks "Shortcuts":

```
1. Menu hides
2. FloatingDock appears (click: show DrawersManager)
3. Menu reads drawers.json ◄─ refresh_shortcuts_submenu()
4. Submenu populated with drawer buttons + shortcuts
```

---

## Component Breakdown

### 1. Main Entry Point (`main.py`)

Responsibility: Daemon initialization and lifecycle management

```python
main()
  ├─ Configure logging (rotating log, 512KB cap)
  ├─ Create managers (power, theme, wifi)
  ├─ Create AppIndicator
  ├─ Build menu (IndicatorMenu)
  ├─ Enter Gtk.main_loop()
  └─ Handle graceful shutdown
```

Key Features:

- Signal handlers for `SIGINT`, `SIGTERM` → graceful cleanup
- D-Bus and GSettings connection establishment
- Exception handling for missing services

---

### 2. System Managers

#### `power_manager.py` (PowerManager)

D-Bus Interface: `net.hadess.PowerProfiles`

- `get_active_profile()` — read current CPU profile
- `set_active_profile(name)` — switch to Performance/Balanced/Power-Saver
- `connect_changed(callback)` — subscribe to profile changes
- Design: Singleton pattern; lazy-loads D-Bus on first access

#### `theme_manager.py` (ThemeManager)

GSettings Schema: `org.gnome.desktop.interface`

- `get_color_scheme()` — read current theme
- `set_color_scheme(scheme)` — set to prefer-dark/prefer-light/default
- `connect_changed(callback)` — subscribe to theme changes
- Design: Singleton; handles schema missing gracefully

#### `wifi_manager.py` (WiFiManager)

D-Bus Interface: `org.freedesktop.NetworkManager`

- `get_saved_wifi_connections()` — list saved Wi-Fi networks
- `get_active_wifi()` — get currently connected network
- `activate_wifi(connection_path)` — switch to a network
- `deactivate_wifi()` — disconnect
- Design: Lazy-loads D-Bus; handles network state changes asynchronously

---

### 3. UI Layer

#### `indicator.py` (AppIndicator Wrapper)

Responsibility: Manage top-bar icon and bind menu

```python
class AppIndicator:
  def __init__(self, menu):
    self.indicator = AyatanaAppIndicator3.Indicator(...)
    self.indicator.set_menu(menu)
    
  def update_icon(self, name):
    # Icon changes based on CPU profile or state
    self.indicator.set_icon(name)
```

Icon Variants:

- `power-profile-performance-symbolic` — Performance mode
- `power-profile-balanced-symbolic` — Balanced mode
- `power-profile-powersaver-symbolic` — Power-saver mode

---

#### `menu.py` (IndicatorMenu)

Responsibility: GTK menu layout, CPU/theme/WiFi/shortcuts management

Menu Structure:

```
┌─ CPU Profile
│  ├─ Performance ◆
│  ├─ Balanced (Normal)
│  └─ Power Saver
├─ Appearance
│  ├─ Dark Mode
│  ├─ Light Mode
│  └─ System Default ◆
├─ Wi-Fi
│  ├─ Network 1
│  ├─ Network 2 ◆ (active)
│  └─ Disconnect
├─ Shortcuts ◄─────────── DYNAMIC (read from drawers.json)
│  ├─ Dev (drawer)
│  │  ├─ Terminal ◄─ executable
│  │  └─ VS Code ◄─ executable
│  ├─ Work (drawer)
│  │  └─ Firefox ◄─ executable
│  └─ [Separator]
│  └─ Manage Shortcuts...
├─ [Separator]
├─ Power Settings
├─ System Monitor
├─ [Separator]
├─ About
└─ Quit
```

Key Methods:

- `build_menu()` — initial menu layout
- `refresh_shortcuts_submenu()` — read drawers.json, populate with live shortcuts
- `on_shortcut_clicked(item, command)` — execute shortcut via `subprocess.Popen()`
- `on_menu_show()` — triggered when menu opens; refresh Wi-Fi and shortcuts

Shortcuts Update Flow:

1. User opens menu (signal: `menu.show`)
2. `on_menu_show()` called
3. `refresh_shortcuts_submenu()` reads `~/.config/gnome-toolbelt/drawers.json`
4. Menu rebuilds Shortcuts submenu with current drawers + shortcuts
5. User can click shortcut to execute or "Manage Shortcuts..." to open DrawersManager

---

### 4. Shortcuts & Drawers (`drawers.py`)

Two main classes:

#### `DrawersManager(Gtk.Window)` — Full CRUD UI

Responsibility: Full shortcut/drawer management interface

```text
┌─────────────────────────────────────────────┐
│ Shortcuts Drawers (Window)                  │
│ ┌───────────────────────────────────────┐  │
│ │ Toolbar: [+ Add Drawer]               │  │
│ ├───────────────────────────────────────┤  │
│ │  ┌──────────┐ ┌──────────┐            │  │
│ │  │ Dev      │ │ Work     │            │  │
│ │  │ [+Add    │ │ [+Add    │            │  │
│ │  │  Shortcut│ │  Shortcut│            │  │
│ │  │ DEL HIDE]│ │ DEL HIDE]│            │  │
│ │  ├──────────┤ ├──────────┤            │  │
│ │  │ Terminal │ │ Firefox  │            │  │
│ │  │ [Run]    │ │ [Run]    │            │  │
│ │  │ [Remove] │ │ [Remove] │            │  │
│ │  │──────────│ │──────────│            │  │
│ │  │ VS Code  │ │          │            │  │
│ │  │ [Run]    │ │          │            │  │
│ │  │ [Remove] │ │          │            │  │
│ │  └──────────┘ └──────────┘            │  │
│ └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

Features:

- Drag-and-drop reordering within same drawer
- Add drawer: Dialog prompt for name
- Delete drawer: Confirmation dialog
- Add shortcut: Dialog (Name, Command, Icon, optional .desktop creation)
- Delete shortcut: Confirmation dialog
- Run shortcut: Execute command via `subprocess.Popen()`

Persistence:

- Reads/writes `~/.config/gnome-toolbelt/drawers.json`
- Format: `{ "DrawerName": [{"name": "...", "command": "...", "icon": "..."}] }`

Drag Protocol:

- Source: ListBoxRow (shortcut)
- Target: Listbox (drawers list) in same or different drawer
- Data: JSON payload `{"drawer": "...", "item": {...}}`
- Action: Reorder within drawer OR move to different drawer

---

#### `DrawersDock(Gtk.Window)` — Floating Compact Access

Responsibility: Minimal, always-on-top drawer launcher + .desktop import

```text
┌─ ✕ + ── [Dev] [Work] ──────────────┐
└────────────────────────────────────┘
   │  │    │       └────── drawer buttons
   │  │    └─────────────── add drawer button
   │  └────────────────── separator
   └──────────────────── close button
```

Features:

- Window type: TOPLEVEL (undecorated, keep-above, skip-taskbar)
- Position: Movable via click-and-drag
- Auto-refresh: Periodic check (2s) for config changes
- Drag-and-drop: Accept .desktop files from desktop/file manager
  - Parse .desktop file (Name, Exec, Icon)
  - Search app by ID if dropped text is app name
  - Add to first drawer

Drag Handlers:

- `on_drag_data_received()` — accepts `text/uri-list` and `application/x-desktop`
- `on_drag_motion()` — visualize drop zone
- `on_button_press/release/motion` — implement window dragging

App Search (`_import_by_app_id_or_name()`):

1. Try exact match: `firefox` → `~/.local/share/applications/firefox.desktop`
2. Search in `/usr/share/applications/`, `/usr/local/share/applications/`
3. Fallback: glob search + name matching

---

## Data Flow

### Scenario 1: User Clicks CPU Profile

```text
User clicks menu > selects "Performance"
    ↓
IndicatorMenu.on_cpu_item_clicked(item, "performance")
    ↓
PowerManager.set_active_profile("performance")
    ↓
D-Bus call: net.hadess.PowerProfiles.SetProfile("performance")
    ↓
System D-Bus broadcasts ProfilesChanged signal
    ↓
PowerManager notifies all listeners
    ↓
IndicatorMenu.on_power_profile_changed_externally()
    ↓
Menu updates checkmark + icon
```

### Scenario 2: User Clicks Shortcut in Menu

```text
User opens menu > hovers Shortcuts > clicks "Firefox"
    ↓
IndicatorMenu.refresh_shortcuts_submenu() (on menu show)
    ├─ Read drawers.json
    ├─ Build submenu with drawers + shortcuts
    └─ Attach on_shortcut_clicked handler
    ↓
User clicks "Firefox" shortcut item
    ↓
IndicatorMenu.on_shortcut_clicked(item, "firefox")
    ↓
subprocess.Popen(["firefox"])
    ↓
Firefox launches
```

### Scenario 3: User Drag-Drops .desktop File onto Dock

```text
User drags Firefox.desktop onto floating dock
    ↓
DrawersDock.on_drag_data_received(widget, data)
    ├─ Get URI from data: "file:///usr/share/applications/firefox.desktop"
    ├─ URL-decode → "/usr/share/applications/firefox.desktop"
    └─ Call _import_desktop_file()
    ↓
_import_desktop_file(path)
    ├─ Parse [Desktop Entry] section
    ├─ Extract Name="Firefox", Exec="firefox", Icon="firefox"
    ├─ Add to first drawer: drawers["Dev"].append({name, command, icon})
    ├─ Save to drawers.json
    └─ Call refresh() → rebuild UI
    ↓
DrawersDock buttons updated
    ↓
Menu.refresh_shortcuts_submenu() picks up new config next time menu opens
    ↓
Shortcuts submenu now shows Firefox under Dev
```

---

## State Management

### Managers (Singleton Pattern)

Each manager maintains internal state + D-Bus/GSettings subscriptions:

```python
class PowerManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = PowerManager()
        return cls._instance
```

Why Singleton?

- Prevent duplicate D-Bus/GSettings connections
- Centralize state updates
- Memory efficient

### Menu & Dock References

```python
# In main.py
menu = IndicatorMenu(...)
indicator.set_menu(menu)

# Dock created on demand
menu._drawers_dock = None  # Created when user clicks "Shortcuts"
```

Why Lazy?

- Avoid initializing full DrawersDock window on startup
- Reduce UI latency
- Only instantiate when user requests it

---

## Testing Strategy

### Unit Tests (`app/tests/`)

Coverage:

- test_menu.py (15 tests)
  - Menu initialization
  - CPU/theme item clicks
  - Shortcut menu generation
  - Shortcut execution (subprocess)
  
- test_power_manager.py (4 tests)
  - D-Bus interface mocking
  - Profile get/set
  - Changed signal handling

- test_theme_manager.py (3 tests)
  - GSettings access
  - Theme get/set
  - Changed signal handling

- test_wifi_manager.py (2 tests)
  - NetworkManager interface
  - Network list/active/activate

- test_drawers.py (16 tests)
  - DrawersManager CRUD
  - DrawersDock init/load/refresh
  - .desktop file parsing
  - App ID searching
  - Drag-drop simulation
  - Config persistence

- test_integration_lifecycle.py (5 tests)
  - Full app lifecycle
  - Manager initialization
  - D-Bus connection handling
  - Graceful shutdown

Mocking Strategy:

- D-Bus/GSettings: Mock via `unittest.mock.MagicMock`
- GTK widgets: Patch `Gtk.*.show_all`, avoid GUI
- File I/O: Use `tempfile.TemporaryDirectory` for config

Run Tests:

```bash
PYTHONPATH=$PWD/app/src:$PWD .venv/bin/pytest app/tests/ -q
# Result: 45 tests, all passing
```

---

## Security & Permissions

### D-Bus Policies

- PowerProfiles: User-level; no elevation required
- NetworkManager: User-level; needs `network-manager` group (typically auto)

### Config Permissions

- `~/.config/gnome-toolbelt/drawers.json` — user-owned, 0644 (RW user, R others)
- No sensitive data stored (only shortcut names/commands)

### Subprocess Safety

- Commands executed via `subprocess.Popen()` with shell=False (default)
- No shell interpretation; user input sanitized by GTK entry widgets

---

## Deployment & Lifecycle

### Installation

```bash
./app/scripts/install.sh
  ├─ Create wrapper: ~/.local/bin/gnome-toolbelt
  ├─ Create desktop entry: ~/.local/share/applications/gnome-toolbelt.desktop
  └─ Create autostart link: ~/.config/autostart/gnome-toolbelt.desktop
```

### Autostart

- Desktop file in `~/.config/autostart/` triggers `gnome-toolbelt` on login
- Runs in background; auto-hides terminal

### Logging

- Path: `~/.cache/gnome-toolbelt.log`
- Rotation: 512KB limit, 1 backup file
- Level: INFO (warnings, errors, key events)

### Graceful Shutdown

```text
SIGTERM/SIGINT
  ↓
Signal handler in main.py
  ↓
Gtk.main_quit()
  ↓
Cleanup (D-Bus connections, file handles, temp resources)
  ↓
Exit(0)
```

---

## Future Enhancements

### Possible Extensions

1. Undo/Redo for drawer/shortcut operations
2. Icon selection dialog for shortcuts
3. Keyboard shortcuts (e.g., Ctrl+Alt+S to open dock)
4. Cloud sync (Google Drive, Dropbox) for config
5. Per-shortcut categories (tags, custom sorting)
6. Hotkeys for frequently-used shortcuts (system-wide keybindings)
7. Multi-monitor dock positioning (per-monitor config)
8. Theming for dock (colors, fonts, transparency)

---

## Summary

Gnome Toolbelt achieves modularity through:

- Abstraction: Managers isolate D-Bus/GSettings details
- Composition: IndicatorMenu builds on managers + UI classes
- Persistence: JSON config for user data
- Testing: Mock-based unit tests, no GUI required
- Extensibility: Easy to add new managers, menu items, or UI elements

The architecture prioritizes:

- User Experience: Fast menu load, direct shortcut access, visual feedback
- Reliability: Error handling, graceful degradation
- Maintainability: Clear separation of concerns, comprehensive tests
- Performance: Lazy initialization, caching, minimal D-Bus polling
