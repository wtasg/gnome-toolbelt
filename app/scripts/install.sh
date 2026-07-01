#!/usr/bin/env bash

set -e

# Resolve absolute paths early so we can run a safe uninstall first
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
WORKSPACE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# If an uninstall script exists, run it to remove previous wrappers and desktop entries.
# This preserves user settings/configs because uninstall.sh only removes wrapper and desktop files.
if [ -x "$SCRIPT_DIR/uninstall.sh" ]; then
	echo "Found existing installation — running uninstall to clean previous wrappers and desktop entries..."
	"$SCRIPT_DIR/uninstall.sh"
fi

# Target directories
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

# Create directories if they don't exist
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$AUTOSTART_DIR"

# Resolve remaining absolute paths
BIN_DEST="$BIN_DIR/gnome-toolbelt"
TEMPLATE_SRC="$SCRIPT_DIR/gnome-toolbelt.desktop.template"

echo "Installing Modular Gnome Toolbelt..."
echo "Workspace directory resolved to: $WORKSPACE_DIR"

# 1. Create executable wrapper in ~/.local/bin/
cat <<EOF >"$BIN_DEST"
#!/usr/bin/env bash
# Wrapper to run the modular application using development workspace PYTHONPATH
export PYTHONPATH="$WORKSPACE_DIR:\$PYTHONPATH"
exec python3 -m app.src.main "\$@"
EOF

chmod +x "$BIN_DEST"
echo "✓ Executable wrapper created at $BIN_DEST"

# 2. Generate the desktop entry
DESKTOP_DEST_APP="$APP_DIR/gnome-toolbelt.desktop"
DESKTOP_DEST_AUTO="$AUTOSTART_DIR/gnome-toolbelt.desktop"

# Replace __EXEC_PATH__ with absolute path to wrapper destination
sed "s|__EXEC_PATH__|$BIN_DEST|g" "$TEMPLATE_SRC" >"$DESKTOP_DEST_APP"
cp "$DESKTOP_DEST_APP" "$DESKTOP_DEST_AUTO"

chmod +x "$DESKTOP_DEST_APP"
chmod +x "$DESKTOP_DEST_AUTO"

echo "✓ Desktop entries created at:"
echo "  - $DESKTOP_DEST_APP"
echo "  - $DESKTOP_DEST_AUTO (autostart)"

echo ""
echo "Installation complete!"
echo "To start the application in the background right now, run:"
echo "  nohup gnome-toolbelt >/dev/null 2>&1 &"
echo "Or find 'Toolbelt' in your Applications launcher."
