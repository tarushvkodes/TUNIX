#!/bin/bash

# TUNIX Container Setup Script
# Copyright © Tarushv Kosgi 2025

set -e

LOG_FILE="/var/log/tunix/container-setup.log"
DISTROBOX_CONFIG="/etc/tunix/distrobox/config.json"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

install_container_tools() {
    log_message "Installing container tools..."
    
    # Install Docker
    apt-get update
    apt-get install -y docker.io docker-compose podman buildah skopeo
    
    # Install Distrobox
    curl -s https://raw.githubusercontent.com/89luca89/distrobox/main/install | sh -s -- --prefix /usr
    
    # Enable and start services
    systemctl enable docker
    systemctl start docker
    systemctl enable podman.socket
}

configure_docker() {
    log_message "Configuring Docker..."
    
    # Create daemon configuration
    cat > /etc/docker/daemon.json << EOF
{
    "storage-driver": "overlay2",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    },
    "default-ulimits": {
        "nofile": {
            "Name": "nofile",
            "Hard": 64000,
            "Soft": 64000
        }
    },
    "features": {
        "buildkit": true
    }
}
EOF

    # Restart Docker to apply changes
    systemctl restart docker
}

configure_podman() {
    log_message "Configuring Podman..."
    
    # Create registries configuration
    cat > /etc/containers/registries.conf << EOF
[registries.search]
registries = ['docker.io', 'quay.io', 'registry.fedoraproject.org']

[registries.insecure]
registries = []

[registries.block]
registries = []
EOF
}

setup_distrobox() {
    log_message "Setting up Distrobox..."
    
    # Create Distrobox configuration directory
    mkdir -p "$(dirname $DISTROBOX_CONFIG)"
    
    # Create default configuration
    cat > "$DISTROBOX_CONFIG" << EOF
{
    "default_containers": [
        {
            "name": "tunix-dev",
            "image": "ubuntu:22.04",
            "description": "Ubuntu 22.04 Development Environment",
            "init": true,
            "packages": [
                "build-essential",
                "git",
                "python3",
                "nodejs"
            ]
        },
        {
            "name": "tunix-gaming",
            "image": "archlinux:latest",
            "description": "Arch Linux Gaming Environment",
            "init": true,
            "packages": [
                "wine",
                "steam",
                "lutris"
            ]
        }
    ],
    "settings": {
        "auto_update": true,
        "share_home": true,
        "share_sound": true,
        "share_gpu": true,
        "share_wayland": true
    }
}
EOF
}

create_desktop_entries() {
    log_message "Creating desktop entries..."
    
    # Create container manager entry
    cat > /usr/share/applications/tunix-container-manager.desktop << EOF
[Desktop Entry]
Name=TUNIX Container Manager
Comment=Manage containers and development environments
Exec=tunix-container-manager
Icon=system-container
Terminal=false
Type=Application
Categories=System;Settings;
Keywords=container;docker;podman;distrobox;
EOF
}

setup_security() {
    log_message "Configuring container security..."
    
    # Set up SELinux policies for containers
    if command -v semanage >/dev/null; then
        semanage fcontext -a -t container_file_t "/var/lib/docker(/.*)?"
        semanage fcontext -a -t container_file_t "/var/lib/podman(/.*)?"
        restorecon -R /var/lib/docker /var/lib/podman
    fi
    
    # Configure AppArmor profiles
    if command -v aa-enabled >/dev/null && aa-enabled; then
        cp /etc/apparmor.d/containers/* /etc/apparmor.d/
        systemctl reload apparmor
    fi
}

create_user_guide() {
    log_message "Creating container user guide..."
    
    cat > /usr/share/doc/tunix/container-guide.md << EOF
# TUNIX Container Guide

## Available Tools
- Docker: Traditional container runtime
- Podman: Daemonless container runtime
- Distrobox: Create development environments

## Quick Start
1. Launch TUNIX Container Manager
2. Select "Create New Environment"
3. Choose from pre-configured templates
4. Start using your container

## Development Environments
Pre-configured environments available:
- Ubuntu 22.04 (Development)
- Arch Linux (Gaming)
- Fedora (Latest)

## Container Management
- Use desktop icons to launch environments
- Access container shell: distrobox enter <name>
- Install software: distrobox install <name> <package>
EOF
}

main() {
    log_message "Starting TUNIX container setup"
    
    install_container_tools
    configure_docker
    configure_podman
    setup_distrobox
    create_desktop_entries
    setup_security
    create_user_guide
    
    log_message "Container setup completed successfully"
}

main