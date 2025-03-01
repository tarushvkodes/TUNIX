#!/bin/bash
# TUNIX Plymouth Theme Installation Script
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

log "Installing TUNIX Plymouth theme..."

# Create theme directory
THEME_DIR="/usr/share/plymouth/themes/tunix"
mkdir -p "$THEME_DIR"

# Copy theme files
log "Copying theme files..."
cp tunix.plymouth "$THEME_DIR/"
cp tunix.script "$THEME_DIR/"
cp logo.png "$THEME_DIR/"
cp progress_bar.png "$THEME_DIR/"
cp progress_box.png "$THEME_DIR/"
cp dialog.png "$THEME_DIR/"
cp bullet.png "$THEME_DIR/"

# Install the theme
log "Setting up theme in system..."
update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$THEME_DIR/tunix.plymouth" 100
update-alternatives --set default.plymouth "$THEME_DIR/tunix.plymouth"

# Update initramfs
log "Updating initramfs..."
update-initramfs -u

success "TUNIX Plymouth theme installed successfully"
log "The theme will be used on next boot"