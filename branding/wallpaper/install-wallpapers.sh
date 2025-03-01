#!/bin/bash
# TUNIX Wallpaper Installation Script
# Copyright © Tarushv Kosgi 2025

# Set script to exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[TUNIX]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    error "This script must be run as root"
fi

log "Installing TUNIX wallpapers..."

# Create wallpaper directories
SYSTEM_DIR="/usr/share/backgrounds/tunix"
XML_DIR="/usr/share/gnome-background-properties"

mkdir -p "$SYSTEM_DIR"
mkdir -p "$XML_DIR"

# Copy wallpaper files
log "Copying wallpaper files..."
cp ../wallpaperlight.PNG "$SYSTEM_DIR/tunix-light.png"
cp ../wallpaperdark.PNG "$SYSTEM_DIR/tunix-dark.png"

# Optimize wallpapers for system use
log "Optimizing wallpaper files..."
if command -v optipng &> /dev/null; then
    optipng -o5 "$SYSTEM_DIR/tunix-light.png"
    optipng -o5 "$SYSTEM_DIR/tunix-dark.png"
fi

# Create XML metadata file for GNOME
log "Creating wallpaper metadata..."
cat > "$XML_DIR/tunix-wallpapers.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE wallpapers SYSTEM "gnome-wp-list.dtd">
<wallpapers>
  <wallpaper deleted="false">
    <name>TUNIX Light</name>
    <filename>/usr/share/backgrounds/tunix/tunix-light.png</filename>
    <options>zoom</options>
    <shade_type>solid</shade_type>
    <pcolor>#ffffff</pcolor>
    <scolor>#000000</scolor>
  </wallpaper>
  <wallpaper deleted="false">
    <name>TUNIX Dark</name>
    <filename>/usr/share/backgrounds/tunix/tunix-dark.png</filename>
    <options>zoom</options>
    <shade_type>solid</shade_type>
    <pcolor>#242424</pcolor>
    <scolor>#000000</scolor>
  </wallpaper>
</wallpapers>
EOF

# Set default GNOME settings
log "Configuring default wallpapers..."
if [ -f "/usr/bin/gsettings" ]; then
    # For system-wide settings, we need to use dconf directly
    # These will be applied to new users
    mkdir -p /etc/dconf/db/local.d
    cat > /etc/dconf/db/local.d/00-tunix-background << EOF
[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/tunix/tunix-light.png'
picture-uri-dark='file:///usr/share/backgrounds/tunix/tunix-dark.png'
picture-options='zoom'

[org/gnome/desktop/screensaver]
picture-uri='file:///usr/share/backgrounds/tunix/tunix-dark.png'
picture-options='zoom'
EOF

    # Update the system databases
    dconf update
fi

success "TUNIX wallpapers installed successfully"