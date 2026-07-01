#!/usr/bin/env bash

set -euo pipefail

# Target directories
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

# Resolve paths similar to install.sh
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
WORKSPACE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
BIN_DEST="$BIN_DIR/gnome-toolbelt"
DESKTOP_DEST_APP="$APP_DIR/gnome-toolbelt.desktop"
DESKTOP_DEST_AUTO="$AUTOSTART_DIR/gnome-toolbelt.desktop"

echo "Uninstalling Modular Gnome Toolbelt..."

delete_file() {
	local f="$1"
	if [ -e "$f" ]; then
		rm -f "$f" && echo "✓ Removed $f"
	else
		echo "- Not found: $f"
	fi
}

# Remove wrapper and desktop entries
delete_file "$BIN_DEST"
delete_file "$DESKTOP_DEST_APP"
delete_file "$DESKTOP_DEST_AUTO"

# Optionally inform about leftover workspace files
echo ""
echo "Note: This removes the executable wrapper and desktop entries only."
echo "If you created additional user files (logs, config), remove them manually."

echo "Uninstallation complete."

exit 0
