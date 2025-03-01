#!/bin/bash

# TUNIX Package Installation Script
# Copyright © Tarushv Kosgi 2025

set -e  # Exit on error
LOG_FILE="/var/log/tunix-package-installation.log"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

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

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root"
        exit 1
    fi
}

# Update repository information
update_repos() {
    log "Updating package repositories..."
    apt-get update -y || error "Failed to update repositories"
    success "Repositories updated"
}

# Function to add required repositories
add_repositories() {
    log_message "Adding required repositories..."
    
    # Add Flatpak support
    apt install -y flatpak gnome-software-plugin-flatpak
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

    # Add VSCode repository
    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/packages.microsoft.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list
}

# Install packages from package list
install_packages() {
    log_message "Starting package installation..."
    
    # Update package lists
    apt update

    # Read package list and install packages
    while read -r line; do
        # Skip comments and empty lines
        [[ $line =~ ^#.*$ ]] || [ -z "$line" ] && continue
        
        log_message "Installing package: $line"
        apt install -y "$line" || log_message "Failed to install package: $line"
    done < "package-list.txt"
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

# Function to perform post-installation setup
post_install() {
    log_message "Performing post-installation setup..."
    
    # Enable services
    systemctl enable tlp
    systemctl start tlp
    
    # Configure default applications
    update-alternatives --set editor /usr/bin/nano
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
    check_root
    log_message "Starting TUNIX package installation"
    
    update_repos
    add_repositories
    install_packages
    setup_flatpak
    apply_configs
    remove_bloat
    post_install
    
    log_message "Package installation completed successfully"
}

# Execute main function
main "$@"