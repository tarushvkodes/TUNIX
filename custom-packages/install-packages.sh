#!/bin/bash
# TUNIX Package Installation Script
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

# Update repository information
update_repos() {
    log "Updating package repositories..."
    apt-get update -y || error "Failed to update repositories"
    success "Repositories updated"
}

# Add additional repositories
add_repositories() {
    log "Adding additional repositories..."
    
    # Add Flatpak repository
    add-apt-repository -y ppa:flatpak/stable
    
    # Add VSCode repository
    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
    install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
    sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main" > /etc/apt/sources.list.d/vscode.list'
    rm packages.microsoft.gpg
    
    # Add System76 driver repository
    add-apt-repository -y ppa:system76-dev/stable
    
    # Update after adding repositories
    apt-get update -y
    
    success "Additional repositories added"
}

# Install packages from package list
install_packages() {
    log "Installing TUNIX packages..."
    
    # Check if package list exists
    if [ ! -f "package-list.txt" ]; then
        error "Package list not found!"
    fi
    
    # Filter out comments and empty lines
    PACKAGES=$(grep -v '^#' package-list.txt | grep -v '^$')
    
    # Install packages
    apt-get install -y $PACKAGES || error "Failed to install packages"
    
    success "TUNIX packages installed successfully"
}

# Configure Flatpak and add essential applications
setup_flatpak() {
    log "Setting up Flatpak..."
    
    # Add Flathub repository
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    
    # Install some popular applications from Flatpak
    flatpak install -y flathub org.telegram.desktop
    flatpak install -y flathub com.spotify.Client
    flatpak install -y flathub com.discordapp.Discord
    flatpak install -y flathub org.onlyoffice.desktopeditors
    
    success "Flatpak setup completed"
}

# Apply post-installation configurations
apply_configs() {
    log "Applying package configurations..."
    
    # Enable TLP for battery optimization
    systemctl enable tlp.service
    
    # Configure default applications
    update-alternatives --set x-www-browser /usr/bin/firefox
    
    success "Package configurations applied"
}

# Remove unnecessary packages
remove_bloat() {
    log "Removing unnecessary packages..."
    
    BLOAT_PACKAGES="
        aisleriot
        gnome-mahjongg
        gnome-mines
        gnome-sudoku
        transmission-gtk
    "
    
    apt-get remove -y $BLOAT_PACKAGES
    apt-get autoremove -y
    
    success "Unnecessary packages removed"
}

# Main function
main() {
    log "Starting TUNIX package installation..."
    
    update_repos
    add_repositories
    install_packages
    setup_flatpak
    apply_configs
    remove_bloat
    
    success "TUNIX package installation completed successfully"
}

# Execute main function
main "$@"