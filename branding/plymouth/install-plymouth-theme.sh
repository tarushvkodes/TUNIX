#!/bin/bash
# TUNIX Plymouth Theme Installer
# Copyright © Tarushv Kosgi 2025

set -e

THEME_NAME="tunix"
THEME_DIR="/usr/share/plymouth/themes/$THEME_NAME"

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
if [ "$EUID" -ne 0 ]; then
    error "Please run as root"
fi

log "Installing TUNIX Plymouth theme..."

# Create theme directory
mkdir -p "$THEME_DIR"

# Copy theme files
log "Copying theme files..."
cp tunix.plymouth "$THEME_DIR/"
cp tunix.script "$THEME_DIR/"
cp ../tunixlogo.PNG "$THEME_DIR/tunixlogo.png"

# Create progress bar images
log "Creating progress bar images..."
convert -size 200x10 xc:transparent \
    -fill "#3584e4" -draw "roundrectangle 0,0,200,10,5,5" \
    "$THEME_DIR/progress_bar.png"

convert -size 202x12 xc:transparent \
    -fill none -stroke "#ffffff" -strokewidth 1 \
    -draw "roundrectangle 0,0,201,11,5,5" \
    "$THEME_DIR/progress_box.png"

# Install the theme
log "Setting up theme in system..."
update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth \
    "$THEME_DIR/tunix.plymouth" 100

# Set as default theme
plymouth-set-default-theme tunix

# Update initramfs
log "Updating initramfs..."
update-initramfs -u

success "TUNIX Plymouth theme installed successfully"
log "The theme will be used on next boot"