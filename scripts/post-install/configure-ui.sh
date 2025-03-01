#!/bin/bash
# TUNIX UI Configuration Script
# Copyright © Tarushv Kosgi 2025

# Set script to exit on error
set -e

LOG_FILE="/var/log/tunix-ui-config.log"
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

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

# Install theme dependencies
install_dependencies() {
    log_message "Installing theme dependencies"
    apt install -y \
        sassc \
        gtk2-engines-murrine \
        gtk2-engines-pixbuf \
        libglib2.0-dev-bin
}

# Apply GNOME shell extensions
install_extensions() {
    log "Installing GNOME shell extensions..."
    
    # Extensions to install
    EXTENSIONS=(
        "dash-to-dock@micxgx.gmail.com"
        "user-theme@gnome-shell-extensions.gcampax.github.com"
        "appindicatorsupport@rgcjonas.gmail.com"
        "gsconnect@andyholmes.github.io"
        "blur-my-shell@aunetx"
        "just-perfection-desktop@just-perfection"
        "tiling-assistant@leleat-on-github"
    )
    
    # Install/enable extensions
    for extension in "${EXTENSIONS[@]}"; do
        gnome-extensions enable "$extension" || \
        log "Extension $extension not yet installed - will be installed via package manager"
    done
    
    success "GNOME shell extensions installed"
}

# Apply GNOME shell theme
apply_theme() {
    log "Applying TUNIX theme..."
    
    # Create user themes directory if it doesn't exist
    mkdir -p ~/.themes
    mkdir -p ~/.icons
    
    # Copy TUNIX theme files
    cp -r /usr/share/tunix/themes/TUNIX-Light ~/.themes/
    cp -r /usr/share/tunix/themes/TUNIX-Dark ~/.themes/
    cp -r /usr/share/tunix/icons/TUNIX-Icons ~/.icons/
    
    # Apply themes using dconf
    gsettings set org.gnome.desktop.interface gtk-theme "TUNIX-Light"
    gsettings set org.gnome.desktop.interface icon-theme "TUNIX-Icons"
    gsettings set org.gnome.desktop.wm.preferences theme "TUNIX-Light"
    gsettings set org.gnome.shell.extensions.user-theme name "TUNIX-Light"
    
    success "TUNIX theme applied"
}

# Configure GTK theme
setup_gtk_theme() {
    log_message "Setting up GTK theme"
    
    # Copy theme to system directory
    mkdir -p /usr/share/themes/TUNIX-Light
    cp -r /usr/local/share/tunix/themes/TUNIX-Light/* /usr/share/themes/TUNIX-Light/
    
    # Set default theme
    cat > /etc/dconf/db/tunix.d/10-theme << EOF
[org/gnome/desktop/interface]
gtk-theme='TUNIX-Light'
icon-theme='Papirus'
cursor-theme='Adwaita'
font-name='Noto Sans 10'
monospace-font-name='Fira Code 10'
document-font-name='Noto Sans 10'
color-scheme='default'

[org/gnome/desktop/wm/preferences]
theme='TUNIX-Light'
titlebar-font='Noto Sans Bold 10'

[org/gnome/shell]
enabled-extensions=['dash-to-dock@micxgx.gmail.com']
EOF
}

# Configure font settings
configure_fonts() {
    log "Configuring font settings..."
    
    # Set default fonts
    gsettings set org.gnome.desktop.interface font-name "Noto Sans 11"
    gsettings set org.gnome.desktop.interface document-font-name "Noto Sans 11"
    gsettings set org.gnome.desktop.interface monospace-font-name "Fira Code 10"
    gsettings set org.gnome.desktop.wm.preferences titlebar-font "Noto Sans Bold 11"
    
    # Set font rendering options
    gsettings set org.gnome.desktop.interface font-antialiasing "rgba"
    gsettings set org.gnome.desktop.interface font-hinting "slight"
    
    success "Font settings configured"
}

# Configure fonts
setup_fonts() {
    log_message "Setting up font configuration"
    
    # Create font configuration
    cat > /etc/fonts/local.conf << EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <match target="font">
        <edit name="antialias" mode="assign">
            <bool>true</bool>
        </edit>
        <edit name="hinting" mode="assign">
            <bool>true</bool>
        </edit>
        <edit name="hintstyle" mode="assign">
            <const>hintslight</const>
        </edit>
        <edit name="rgba" mode="assign">
            <const>rgb</const>
        </edit>
        <edit name="lcdfilter" mode="assign">
            <const>lcddefault</const>
        </edit>
    </match>
</fontconfig>
EOF
}

# Configure desktop layout
configure_desktop() {
    log "Configuring desktop layout..."
    
    # Configure dock
    gsettings set org.gnome.shell.extensions.dash-to-dock dock-position "BOTTOM"
    gsettings set org.gnome.shell.extensions.dash-to-dock extend-height false
    gsettings set org.gnome.shell.extensions.dash-to-dock dock-fixed true
    gsettings set org.gnome.shell.extensions.dash-to-dock autohide true
    gsettings set org.gnome.shell.extensions.dash-to-dock intellihide true
    gsettings set org.gnome.shell.extensions.dash-to-dock show-apps-at-top true
    gsettings set org.gnome.shell.extensions.dash-to-dock show-mounts false
    
    # Configure top panel
    gsettings set org.gnome.shell.extensions.just-perfection panel-size 38
    gsettings set org.gnome.shell.extensions.just-perfection panel-button-padding-size 8
    gsettings set org.gnome.shell.extensions.just-perfection activities-button false
    
    # Configure window management
    gsettings set org.gnome.desktop.wm.preferences button-layout "appmenu:minimize,maximize,close"
    gsettings set org.gnome.mutter center-new-windows true
    gsettings set org.gnome.mutter dynamic-workspaces true
    
    # Configure tiling window options
    gsettings set org.gnome.shell.extensions.tiling-assistant window-gap 4
    gsettings set org.gnome.shell.extensions.tiling-assistant enable-tiling-popup true
    
    success "Desktop layout configured"
}

# Configure desktop layout
setup_desktop_layout() {
    log_message "Setting up desktop layout"
    
    # Desktop grid and workspace configuration
    cat > /etc/dconf/db/tunix.d/30-workspace << EOF
[org/gnome/mutter]
dynamic-workspaces=true
edge-tiling=true

[org/gnome/desktop/wm/preferences]
button-layout='close,minimize,maximize:appmenu'
action-middle-click-titlebar='minimize'

[org/gnome/shell/overrides]
edge-tiling=true

[org/gnome/desktop/peripherals/touchpad]
tap-to-click=true
natural-scroll=true
EOF
}

# Configure GNOME settings
configure_system() {
    log "Configuring system settings..."
    
    # Set dark/light theme preference
    gsettings set org.gnome.desktop.interface color-scheme "prefer-light"
    
    # Configure mouse/touchpad
    gsettings set org.gnome.desktop.peripherals.mouse natural-scroll false
    gsettings set org.gnome.desktop.peripherals.mouse speed 0.0
    gsettings set org.gnome.desktop.peripherals.touchpad natural-scroll true
    gsettings set org.gnome.desktop.peripherals.touchpad tap-to-click true
    gsettings set org.gnome.desktop.peripherals.touchpad two-finger-scrolling-enabled true
    
    # Configure power settings
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type "nothing"
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 1800
    
    # Configure privacy settings
    gsettings set org.gnome.desktop.privacy remember-recent-files true
    gsettings set org.gnome.desktop.privacy remove-old-temp-files true
    gsettings set org.gnome.desktop.privacy remove-old-trash-files true
    gsettings set org.gnome.desktop.privacy old-files-age 30
    
    success "System settings configured"
}

# Configure GNOME Shell extensions
setup_extensions() {
    log_message "Configuring GNOME Shell extensions"
    
    # Dash to dock configuration
    cat > /etc/dconf/db/tunix.d/20-dash-to-dock << EOF
[org/gnome/shell/extensions/dash-to-dock]
dock-position='LEFT'
dock-fixed=true
extend-height=true
transparency-mode='DYNAMIC'
custom-theme-shrink=true
background-opacity=0.8
EOF
}

# Install default wallpapers
install_wallpapers() {
    log "Installing TUNIX wallpapers..."
    
    # Copy wallpapers to user directory
    mkdir -p ~/Pictures/TUNIX-Wallpapers
    cp -r /usr/share/tunix/wallpapers/* ~/Pictures/TUNIX-Wallpapers/
    
    # Set default wallpaper
    gsettings set org.gnome.desktop.background picture-uri "file:///usr/share/tunix/wallpapers/tunix-default.jpg"
    gsettings set org.gnome.desktop.background picture-uri-dark "file:///usr/share/tunix/wallpapers/tunix-default-dark.jpg"
    
    success "TUNIX wallpapers installed"
}

# Set up application theming for non-GTK apps
configure_app_theming() {
    log "Configuring cross-platform theming..."
    
    # Configure Firefox theming
    if [ -d ~/.mozilla/firefox ]; then
        for profile in ~/.mozilla/firefox/*.default-release; do
            mkdir -p "$profile/chrome"
            cp /usr/share/tunix/app-theming/firefox/userChrome.css "$profile/chrome/"
            cp /usr/share/tunix/app-theming/firefox/userContent.css "$profile/chrome/"
            # Enable custom CSS
            if [ -f "$profile/user.js" ]; then
                echo 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);' >> "$profile/user.js"
            else
                echo 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);' > "$profile/user.js"
            fi
        done
    fi
    
    # Configure Qt application theming
    mkdir -p ~/.config
    echo "[Qt]" > ~/.config/Trolltech.conf
    echo "style=GTK+" >> ~/.config/Trolltech.conf
    
    # Set QT_QPA_PLATFORMTHEME environment variable
    echo 'export QT_QPA_PLATFORMTHEME="gtk3"' >> ~/.profile
    
    success "Cross-platform theming configured"
}

# Main function
main() {
    log "Starting TUNIX UI configuration..."
    
    install_dependencies
    install_extensions
    apply_theme
    setup_gtk_theme
    setup_extensions
    configure_fonts
    setup_fonts
    configure_desktop
    setup_desktop_layout
    configure_system
    install_wallpapers
    configure_app_theming
    
    # Update dconf database
    dconf update
    
    success "TUNIX UI configuration completed successfully"
    log "Please log out and log back in for all changes to take effect"
}

# Execute main function
main "$@"