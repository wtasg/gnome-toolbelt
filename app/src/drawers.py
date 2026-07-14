import gi
import os
import json
import subprocess
import logging
import urllib.parse
from pathlib import Path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.path.expanduser('~')).joinpath('.config', 'gnome-toolbelt')
DRAWERS_FILE = CONFIG_DIR.joinpath('drawers.json')


def ensure_config_dir():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Failed to create config directory")


class ShortcutDialog(Gtk.Dialog):
    def __init__(self, parent=None):
        super().__init__(title="Add Shortcut", transient_for=parent, flags=0)
        self.set_default_size(400, 150)

        box = self.get_content_area()
        grid = Gtk.Grid(column_spacing=8, row_spacing=8, margin=12)

        self.name_entry = Gtk.Entry()
        self.command_entry = Gtk.Entry()
        self.icon_entry = Gtk.Entry()
        self.create_desktop = Gtk.CheckButton(label="Create .desktop file in ~/.local/share/applications")
        self.create_desktop.set_active(True)

        grid.attach(Gtk.Label(label="Name:"), 0, 0, 1, 1)
        grid.attach(self.name_entry, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Command:"), 0, 1, 1, 1)
        grid.attach(self.command_entry, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Icon (optional):"), 0, 2, 1, 1)
        grid.attach(self.icon_entry, 1, 2, 1, 1)
        grid.attach(self.create_desktop, 0, 3, 2, 1)

        box.add(grid)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        self.show_all()

    def get_values(self):
        return {
            'name': self.name_entry.get_text().strip(),
            'command': self.command_entry.get_text().strip(),
            'icon': self.icon_entry.get_text().strip(),
            'create_desktop': self.create_desktop.get_active()
        }


class DrawersManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shortcuts Drawers")
        self.set_default_size(800, 300)
        ensure_config_dir()
        self.drawers = {}
        self.load()

        header = Gtk.HeaderBar(title="Shortcuts Drawers")
        header.set_show_close_button(True)
        self.set_titlebar(header)

        # Visible toolbar area with Add Drawer button
        add_btn = Gtk.Button(label="Add Drawer")
        add_btn.connect('clicked', self.on_add_drawer)
        header.pack_end(add_btn)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)

        # Use a vertical box so we can include an explicit control row above the scroller
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin=6)
        new_drawer_btn = Gtk.Button(label="+ Add Drawer")
        new_drawer_btn.connect('clicked', self.on_add_drawer)
        controls.pack_start(new_drawer_btn, False, False, 0)
        main_vbox.pack_start(controls, False, False, 0)

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin=12)
        scroller.add(self.hbox)
        main_vbox.pack_start(scroller, True, True, 0)

        self.add(main_vbox)
        self.populate_ui()
        self.show_all()

    # -- Persistence --
    def load(self):
        try:
            if DRAWERS_FILE.exists():
                with DRAWERS_FILE.open('r', encoding='utf-8') as f:
                    self.drawers = json.load(f)
            else:
                # seed with example drawer
                self.drawers = {'Dev': []}
                self.save()
        except Exception:
            logger.exception("Failed to load drawers config, using empty state")
            self.drawers = {'Dev': []}

    def save(self):
        try:
            with DRAWERS_FILE.open('w', encoding='utf-8') as f:
                json.dump(self.drawers, f, indent=2)
        except Exception:
            logger.exception("Failed to save drawers config")

    # -- UI --
    def populate_ui(self):
        for child in self.hbox.get_children():
            self.hbox.remove(child)
        for drawer_name, items in self.drawers.items():
            frame = self._create_drawer_frame(drawer_name, items)
            self.hbox.pack_start(frame, False, False, 0)
        self.show_all()

    def _create_drawer_frame(self, name, items):
        frame = Gtk.Frame()
        frame.set_label(name)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=6)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_btn = Gtk.Button(label="+ Add Shortcut")
        add_btn.connect('clicked', self.on_add_shortcut_clicked, name)
        close_btn = Gtk.Button(label="Hide")
        close_btn.connect('clicked', self.on_close_drawer, name, frame)
        delete_btn = Gtk.Button(label="Delete Drawer")
        delete_btn.connect('clicked', self.on_delete_drawer, name)
        header_box.pack_start(add_btn, False, False, 0)
        header_box.pack_start(delete_btn, False, False, 0)
        header_box.pack_start(close_btn, False, False, 0)

        vbox.pack_start(header_box, False, False, 0)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.set_size_request(220, 240)

        # Setup drag dest
        listbox.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.MOVE)
        listbox.connect('drag-data-received', self.on_drag_data_received)

        for itm in items:
            row = self._create_shortcut_row(itm, name)
            listbox.add(row)

        vbox.pack_start(listbox, True, True, 0)
        frame.add(vbox)
        frame.listbox = listbox
        frame.drawer_name = name
        return frame

    def _create_shortcut_row(self, item, drawer_name):
        row = Gtk.ListBoxRow()
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin=6)
        label = Gtk.Label(label=item.get('name', 'Unnamed'), xalign=0)
        launch = Gtk.Button(label="Run")
        launch.connect('clicked', self.on_run_shortcut, item)
        remove_btn = Gtk.Button(label="Remove Shortcut")
        remove_btn.connect('clicked', self.on_remove_shortcut, drawer_name, item)
        h.pack_start(label, True, True, 0)
        h.pack_start(launch, False, False, 0)
        h.pack_start(remove_btn, False, False, 0)
        row.add(h)

        # make row draggable
        row.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.MOVE)
        row.connect('drag-begin', self.on_drag_begin)
        row.connect('drag-data-get', self.on_drag_data_get, drawer_name, item)

        # Attach metadata
        row.shortcut_item = item
        row.source_drawer = drawer_name
        return row

    # -- Drag handlers --
    def on_drag_begin(self, widget, context):
        pass

    def on_drag_data_get(self, widget, drag_context, data, info, time, drawer_name, item):
        try:
            payload = json.dumps({'drawer': drawer_name, 'item': item})
            data.set_text(payload, -1)
        except Exception:
            logger.exception("Failed to prepare drag data")

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        try:
            text = data.get_text()
            payload = json.loads(text)
            src_drawer = payload['drawer']
            item = payload['item']

            # locate source and dest
            dest_frame = self._find_frame_for_list(widget)
            if not dest_frame:
                return
            dest_name = dest_frame.drawer_name
            # If dropping into same drawer -> reorder within list
            if src_drawer == dest_name:
                listbox = widget
                children = list(listbox.get_children())

                # Find source index and remove it from the underlying data list
                src_items = self.drawers.get(src_drawer, [])
                src_index = None
                for i, it in enumerate(src_items):
                    if it.get('name') == item.get('name') and it.get('command') == item.get('command'):
                        src_index = i
                        src_items.pop(i)
                        break

                # compute destination insert index based on y coordinate
                insert_index = len(children)
                for idx, row in enumerate(children):
                    alloc = row.get_allocation()
                    midpoint = alloc.y + (alloc.height / 2)
                    if y < midpoint:
                        insert_index = idx
                        break

                # if source index was before insert point, adjust insert_index
                if src_index is not None and src_index < insert_index:
                    insert_index -= 1

                # insert back into data
                src_items.insert(insert_index, item)
                self.save()
                GLib.idle_add(self.populate_ui)
                return

            # Remove from source
            src_items = self.drawers.get(src_drawer, [])
            for i, it in enumerate(src_items):
                if it.get('name') == item.get('name') and it.get('command') == item.get('command'):
                    src_items.pop(i)
                    break

            # Add to dest
            self.drawers.setdefault(dest_name, []).append(item)
            self.save()
            GLib.idle_add(self.populate_ui)
        except Exception:
            logger.exception("Failed handling drag-data-received")

    def _find_frame_for_list(self, listbox_widget):
        for child in self.hbox.get_children():
            if hasattr(child, 'listbox') and child.listbox is listbox_widget:
                return child
        return None

    # -- Actions --
    def on_add_drawer(self, _btn):
        dialog = Gtk.Dialog(title="New Drawer", transient_for=self, flags=0)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_text("New Drawer")
        box.add(entry)
        dialog.show_all()
        resp = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and name:
            if name in self.drawers:
                return
            self.drawers[name] = []
            self.save()
            self.populate_ui()

    def on_delete_drawer(self, _btn, name):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=f"Delete drawer '{name}'?")
        dialog.format_secondary_text("This will permanently remove the drawer and its shortcuts.")
        resp = dialog.run()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK:
            if name in self.drawers:
                self.drawers.pop(name, None)
                self.save()
                self.populate_ui()

    def on_remove_shortcut(self, _btn, drawer_name, item):
        # confirmation
        dialog = Gtk.MessageDialog(transient_for=self, flags=0,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=f"Remove shortcut '{item.get('name')}' from '{drawer_name}'?")
        resp = dialog.run()
        dialog.destroy()
        if resp != Gtk.ResponseType.OK:
            return

        items = self.drawers.get(drawer_name, [])
        for i, it in enumerate(items):
            if it.get('name') == item.get('name') and it.get('command') == item.get('command'):
                items.pop(i)
                break
        self.save()
        self.populate_ui()

    def on_close_drawer(self, _btn, name, frame):
        # Close (remove) drawer only from UI; keep config until user deletes
        for child in self.hbox.get_children():
            if getattr(child, 'drawer_name', None) == name:
                self.hbox.remove(child)
                break

    def on_add_shortcut_clicked(self, _btn, drawer_name):
        dialog = ShortcutDialog(parent=self)
        resp = dialog.run()
        vals = dialog.get_values()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and vals.get('name') and vals.get('command'):
            item = {'name': vals['name'], 'command': vals['command'], 'icon': vals.get('icon')}
            if vals.get('create_desktop'):
                self._write_desktop_file(item)
            self.drawers.setdefault(drawer_name, []).append(item)
            self.save()
            self.populate_ui()

    def _write_desktop_file(self, item):
        try:
            apps_dir = Path(os.path.expanduser('~')).joinpath('.local', 'share', 'applications')
            apps_dir.mkdir(parents=True, exist_ok=True)
            # simple slug
            name = item.get('name', 'shortcut').strip()
            slug = ''.join(c for c in name if c.isalnum() or c in (' ', '-', '_')).replace(' ', '-')
            path = apps_dir.joinpath(f"{slug}.desktop")
            with path.open('w', encoding='utf-8') as f:
                f.write('[Desktop Entry]\n')
                f.write('Type=Application\n')
                f.write(f"Name={item.get('name')}\n")
                f.write(f"Exec={item.get('command')}\n")
                if item.get('icon'):
                    f.write(f"Icon={item.get('icon')}\n")
                f.write('Terminal=false\n')
            logger.info('Wrote desktop file: %s', path)
        except Exception:
            logger.exception('Failed to write .desktop file')

    def on_run_shortcut(self, _btn, item):
        try:
            subprocess.Popen(item.get('command').split())
        except Exception:
            logger.exception('Failed to launch shortcut')


class DrawersDock(Gtk.Window):
    """A small floating dock that shows drawer buttons and controls.

    Clicking a drawer opens the full DrawersManager. The dock is kept
    minimal and stays on top.
    """
    def __init__(self):
        logger.info('>>> DrawersDock.__init__ START')
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        logger.info('>>> DrawersDock window created (TOPLEVEL type)')
        
        self.set_title("Toolbelt Dock")
        self.set_default_size(250, 50)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        logger.info('>>> DrawersDock properties set')
        
        # Position dock at a visible location on screen
        self.move(100, 100)
        logger.info('>>> DrawersDock moved to (100, 100)')

        # Track for window dragging
        self._drag_x = 0
        self._drag_y = 0
        self._dragging = False

        ensure_config_dir()
        self.drawers = {}
        self.load()
        logger.info('>>> DrawersDock config loaded')

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin=6)
        self.add(self.hbox)
        logger.info('>>> DrawersDock hbox added')

        # Enable mouse dragging to move the window
        self.hbox.connect('button-press-event', self.on_button_press)
        self.hbox.connect('button-release-event', self.on_button_release)
        self.hbox.connect('motion-notify-event', self.on_motion_notify)
        self.hbox.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        logger.info('>>> DrawersDock drag events enabled')

        # Close button (on the left for easy access)
        close_btn = Gtk.Button(label='✕')
        close_btn.set_tooltip_text('Close Dock')
        close_btn.set_size_request(40, 40)
        close_btn.connect('clicked', lambda btn: self.close())
        self.hbox.pack_start(close_btn, False, False, 0)
        logger.info('>>> DrawersDock close button packed')

        # Add Drawer button
        add_btn = Gtk.Button(label='+')
        add_btn.set_tooltip_text('Add Drawer')
        add_btn.set_size_request(40, 40)
        add_btn.connect('clicked', self.on_add_drawer_clicked)
        self.hbox.pack_start(add_btn, False, False, 0)
        logger.info('>>> DrawersDock add button packed')

        # Separator for visual clarity
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.hbox.pack_start(sep, False, False, 0)

        # Refresh drawer buttons
        self._build_drawer_buttons()
        logger.info('>>> DrawersDock buttons built')

        # Setup drag destination for .desktop files and icons from Ubuntu dock
        # Accept multiple mime types that different sources might send
        targets = [
            Gtk.TargetEntry.new('text/uri-list', 0, 0),
            Gtk.TargetEntry.new('application/x-desktop', 0, 1),
            Gtk.TargetEntry.new('application/x-color', 0, 2),
        ]
        self.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.connect('drag-data-received', self.on_drag_data_received)
        self.connect('drag-motion', self.on_drag_motion)
        logger.info('>>> DrawersDock drag destination set (accepts text/uri-list, application/x-desktop)')

        # Make visible and positioned
        self.realize()
        logger.info('>>> DrawersDock realized')
        self.show_all()
        logger.info('>>> DrawersDock shown_all')
        # Schedule a present call on the main loop to ensure it's on top
        GLib.idle_add(lambda: self.present() or False)
        logger.info('DrawersDock initialized and shown at (100, 100)')

        # Start periodic refresh to detect changes
        GLib.timeout_add_seconds(2, self._periodic_refresh)

    def _build_drawer_buttons(self):
        # remove only drawer buttons (keep the first 3 children: close, add, separator)
        children = list(self.hbox.get_children())
        for child in children[3:]:  # Keep close (0), add (1), separator (2); remove drawer buttons (3+)
            self.hbox.remove(child)

        for name in self.drawers.keys():
            btn = Gtk.Button(label=name)
            btn.set_tooltip_text(f'Open {name} drawers')
            btn.connect('clicked', self.on_drawer_clicked, name)
            self.hbox.pack_start(btn, False, False, 0)

        self.show_all()

    def load(self):
        try:
            if DRAWERS_FILE.exists():
                with DRAWERS_FILE.open('r', encoding='utf-8') as f:
                    self.drawers = json.load(f)
            else:
                self.drawers = {}
        except Exception:
            logger.exception('Failed to load drawers config for dock')
            self.drawers = {}

    def _periodic_refresh(self):
        """Periodically check if drawers.json has changed and refresh UI."""
        try:
            if DRAWERS_FILE.exists():
                with DRAWERS_FILE.open('r', encoding='utf-8') as f:
                    current = json.load(f)
                # Only refresh if content changed
                if current != self.drawers:
                    logger.info('Dock detected drawer config change, refreshing...')
                    self.drawers = current
                    self._build_drawer_buttons()
        except Exception:
            logger.exception('Error in _periodic_refresh')
        return True  # Continue calling this callback

    def refresh(self):
        try:
            if DRAWERS_FILE.exists():
                with DRAWERS_FILE.open('r', encoding='utf-8') as f:
                    self.drawers = json.load(f)
            else:
                self.drawers = {}
            logger.info(f'Dock refreshed with drawers: {list(self.drawers.keys())}')
        except Exception:
            logger.exception('Failed to refresh dock drawers')
            self.drawers = {}
        self._build_drawer_buttons()

    def on_add_drawer_clicked(self, _btn):
        # Delegate to DrawersManager UI to handle creation (keeps behavior centralized)
        try:
            dm = DrawersManager()
            dm.present()
        except Exception:
            logger.exception('Failed to open DrawersManager from dock')

    def on_button_press(self, widget, event):
        """Track mouse press for window dragging."""
        if event.button == 1:  # Left click
            self._dragging = True
            self._drag_x = event.x_root - self.get_position()[0]
            self._drag_y = event.y_root - self.get_position()[1]
            logger.debug(f'Drag started at ({event.x_root}, {event.y_root})')
        return False

    def on_button_release(self, widget, event):
        """Stop window dragging on mouse release."""
        if event.button == 1:
            self._dragging = False
            logger.debug('Drag stopped')
        return False

    def on_motion_notify(self, widget, event):
        """Handle window dragging on mouse move."""
        if self._dragging and event.state & Gdk.ModifierType.BUTTON1_MASK:
            x = event.x_root - self._drag_x
            y = event.y_root - self._drag_y
            self.move(x, y)
        return False

    def on_drawer_clicked(self, _btn, name):
        try:
            # Open the full DrawersManager
            dm = DrawersManager()
            dm.present()
            # ensure the requested drawer is visible; user can use the UI there
        except Exception:
            logger.exception('Failed to open drawer from dock')

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        """Handle drag-and-drop of .desktop files from desktop/sidebar or Ubuntu dock."""
        logger.info(f'>>> on_drag_data_received: target={data.get_target()}, info={info}')
        try:
            # Try to get URIs first (most common for file drops)
            uris = data.get_uris()
            logger.info(f'>>> URIs: {uris}')
            
            if uris:
                for uri in uris:
                    logger.info(f'>>> Processing URI: {uri}')
                    # Convert file:// URI to local path
                    if uri.startswith('file://'):
                        path = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
                        self._import_desktop_file(path)
                    else:
                        logger.debug(f'Skipping non-file URI: {uri}')
                drag_context.finish(True, False, time)
                return
            
            # Try to get text data (fallback for Ubuntu dock app ID/name or other sources)
            text = data.get_text()
            if text:
                logger.info(f'>>> Received text data: {text}')
                text = text.strip()
                # Try to find and import by app ID or name
                if self._import_by_app_id_or_name(text):
                    drag_context.finish(True, False, time)
                    return
            
            logger.warning('>>> No URIs or usable text data in drag')
            drag_context.finish(False, False, time)
        except Exception:
            logger.exception('Failed to handle drag-data-received')
            drag_context.finish(False, False, time)

    def _import_by_app_id_or_name(self, app_id_or_name):
        """Try to import an app by ID or name. Search common .desktop locations."""
        logger.info(f'>>> Searching for app: {app_id_or_name}')
        
        # Search paths for .desktop files
        search_paths = [
            Path.home() / '.local' / 'share' / 'applications',
            Path('/usr/share/applications'),
            Path('/usr/local/share/applications'),
            Path('/snap/*/applications'),
        ]
        
        # Try exact app-id match first (e.g., 'firefox' -> 'firefox.desktop')
        candidates = [
            f'{app_id_or_name}.desktop',
            f'{app_id_or_name}.desktop.in',
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            for candidate in candidates:
                desktop_file = search_path / candidate
                if desktop_file.exists():
                    logger.info(f'>>> Found app desktop file: {desktop_file}')
                    return self._import_desktop_file(str(desktop_file))
            
            # Also try glob search for snap apps or variable paths
            try:
                for desktop_file in search_path.glob('*.desktop'):
                    if self._matches_app_id(desktop_file, app_id_or_name):
                        logger.info(f'>>> Found matching app: {desktop_file}')
                        return self._import_desktop_file(str(desktop_file))
            except Exception:
                pass
        
        logger.warning(f'Could not find .desktop file for: {app_id_or_name}')
        return False

    def _matches_app_id(self, desktop_file, app_id):
        """Check if a .desktop file matches the given app ID."""
        try:
            with open(desktop_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Name=') and app_id.lower() in line.lower():
                        return True
            return False
        except Exception:
            return False

    def _import_desktop_file(self, path):
        """Import a .desktop file and add it to the first drawer. Returns True on success."""
        logger.info(f'>>> _import_desktop_file: path={path}')
        try:
            # Normalize path
            path = os.path.expanduser(path)
            
            if not os.path.exists(path):
                logger.warning(f'Path does not exist: {path}')
                return False
            
            if not path.endswith('.desktop') and not path.endswith('.desktop.in'):
                logger.debug(f'Skipping non-.desktop file: {path}')
                return False

            # Parse .desktop file
            name = None
            command = None
            icon = None

            with open(path, 'r', encoding='utf-8') as f:
                in_desktop_entry = False
                for line in f:
                    line = line.strip()
                    if line == '[Desktop Entry]':
                        in_desktop_entry = True
                        continue
                    if in_desktop_entry and line.startswith('['):
                        break
                    if not in_desktop_entry:
                        continue

                    if line.startswith('Name='):
                        name = line.split('=', 1)[1]
                    elif line.startswith('Exec='):
                        command = line.split('=', 1)[1]
                    elif line.startswith('Icon='):
                        icon = line.split('=', 1)[1]

            if not name or not command:
                logger.warning(f'Could not parse Name/Exec from {path}')
                return False

            # Add to first drawer (or create one if empty)
            drawer_name = list(self.drawers.keys())[0] if self.drawers else 'Default'
            if drawer_name not in self.drawers:
                self.drawers[drawer_name] = []

            item = {'name': name, 'command': command, 'icon': icon}
            self.drawers[drawer_name].append(item)

            # Persist and refresh
            try:
                with DRAWERS_FILE.open('w', encoding='utf-8') as f:
                    json.dump(self.drawers, f, indent=2)
            except Exception:
                logger.exception('Failed to save drawers after importing .desktop file')
                return False

            self.refresh()
            logger.info(f'✓ Imported shortcut "{name}" from {path}')
            return True
        except Exception:
            logger.exception(f'Failed to import .desktop file: {path}')
            return False

    def on_drag_motion(self, widget, drag_context, x, y, time):
        """Accept drag motion over the dock."""
        logger.debug(f'>>> on_drag_motion at ({x}, {y})')
        Gdk.drag_status(drag_context, Gdk.DragAction.COPY, time)
        return True

