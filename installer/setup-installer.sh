#!/bin/bash

# TUNIX Installer Setup Script
# Copyright © Tarushv Kosgi 2025

set -e

UBIQUITY_DIR="/usr/lib/ubiquity"
TUNIX_DATA="/usr/share/tunix"
LOG_FILE="/var/log/tunix-installer-setup.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Create TUNIX installer directories
mkdir -p "$TUNIX_DATA/installer"
mkdir -p "$TUNIX_DATA/installer/frontend"
mkdir -p "$TUNIX_DATA/installer/modules"
mkdir -p "$TUNIX_DATA/installer/data"

# Copy TUNIX installer files
cp frontend/tunix-ubiquity-frontend.py "$TUNIX_DATA/installer/frontend/"
cp modules/hardware_detection.py "$TUNIX_DATA/installer/modules/"
cp data/hardware_compatibility.json "$TUNIX_DATA/installer/data/"

# Create Ubiquity integration
cat > "$UBIQUITY_DIR/frontend/tunix_ui.py" << 'EOF'
from ubiquity.frontend import Base
from tunix.installer.frontend.tunix_ui import TunixUI

class PageGtk(TunixUI):
    plugin_translate = 'tunix'
    def __init__(self, controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller
EOF

# Update Ubiquity configuration
cat > "/etc/ubiquity/ubiquity.conf" << EOF
[Ubuntu]
frontend=tunix_ui
EOF

# Set up Python package
mkdir -p "$TUNIX_DATA/installer/tunix"
touch "$TUNIX_DATA/installer/tunix/__init__.py"

# Create setup script for the Python package
cat > "$TUNIX_DATA/installer/setup.py" << EOF
from setuptools import setup, find_packages

setup(
    name="tunix-installer",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        'pygobject',
        'python-debian'
    ],
    entry_points={
        'ubiquity.frontend': [
            'tunix_ui = tunix.installer.frontend.tunix_ui:PageGtk'
        ],
    }
)
EOF

# Install TUNIX installer package
cd "$TUNIX_DATA/installer"
python3 setup.py install

# Update permissions
chmod +x "$TUNIX_DATA/installer/frontend/tunix-ubiquity-frontend.py"
chmod +x "$TUNIX_DATA/installer/modules/hardware_detection.py"

log_message "TUNIX installer setup completed successfully"