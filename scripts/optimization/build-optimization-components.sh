#!/bin/bash
set -e

# Configuration
INSTALL_DIR="/usr/local/lib/tunix"
CONFIG_DIR="/etc/tunix"
LOG_DIR="/var/log/tunix"
SERVICE_DIR="/etc/systemd/system"
COMPONENTS=(
    "system_monitor"
    "performance_analyzer"
    "thermal_control"
    "power_manager"
    "network_optimizer"
    "system_coordinator"
    "system_config"
    "tunix_config_manager"
    "tunix_update_manager"
)

# Ensure we're root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Create required directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"/{config,power,thermal,network,hardware}
mkdir -p "$LOG_DIR"
mkdir -p /var/lib/tunix/{updates,state}
mkdir -p /var/backups/tunix

# Install dependencies
apt-get update
apt-get install -y \
    python3-psutil \
    python3-systemd \
    python3-numpy \
    python3-sklearn \
    python3-daemon \
    python3-curses \
    ethtool \
    hdparm \
    powertop \
    thermald \
    lm-sensors

# Copy Python scripts
echo "Installing Python components..."
for component in "${COMPONENTS[@]}"; do
    src_file="${component}.py"
    dest_file="${component//_/-}.py"
    
    if [[ -f "$src_file" ]]; then
        cp "$src_file" "$INSTALL_DIR/$dest_file"
        chmod 755 "$INSTALL_DIR/$dest_file"
        echo "  Installed $dest_file"
    else
        echo "  Warning: $src_file not found"
    fi
done

# Install systemd service files
echo "Installing service files..."
SERVICES=(
    "tunix-system-monitor"
    "tunix-performance"
    "tunix-thermal"
    "tunix-power"
    "tunix-network"
    "tunix-system-control"
    "tunix-coordinator"
)

for service in "${SERVICES[@]}"; do
    if [[ -f "${service}.service" ]]; then
        cp "${service}.service" "$SERVICE_DIR/"
        chmod 644 "$SERVICE_DIR/${service}.service"
        echo "  Installed ${service}.service"
    else
        echo "  Warning: ${service}.service not found"
    fi
done

# Create default configuration
echo "Creating default configuration..."
python3 << EOF
from tunix_config_manager import ConfigManager
manager = ConfigManager()
manager.load_config()
EOF

# Set up log rotation
cat > /etc/logrotate.d/tunix << EOF
/var/log/tunix/*.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 640 root root
}
EOF

# Configure systemd
echo "Configuring systemd services..."
systemctl daemon-reload

# Enable services
for service in "${SERVICES[@]}"; do
    systemctl enable "$service"
    echo "  Enabled $service"
done

# Set up initial hardware profile
echo "Creating hardware profile..."
python3 << EOF
import json
import subprocess
from pathlib import Path

def get_cpu_info():
    try:
        with open('/proc/cpuinfo') as f:
            cpu_info = f.read()
        return {
            'model': next(line.split(': ')[1].strip() 
                for line in cpu_info.split('\n') 
                if 'model name' in line),
            'cores': len([line for line in cpu_info.split('\n') 
                if 'processor' in line])
        }
    except Exception:
        return {'model': 'unknown', 'cores': 1}

def get_gpu_info():
    try:
        lspci = subprocess.run(
            ['lspci', '-nn'], 
            capture_output=True, 
            text=True
        ).stdout
        
        gpu_lines = [line for line in lspci.split('\n') 
                    if 'VGA' in line or '3D' in line]
        
        return [line.split(': ')[1].strip() for line in gpu_lines]
    except Exception:
        return ['unknown']

def get_memory_info():
    try:
        with open('/proc/meminfo') as f:
            mem = f.read()
        total = next(
            int(line.split()[1]) 
            for line in mem.split('\n') 
            if 'MemTotal' in line
        )
        return {'total_kb': total}
    except Exception:
        return {'total_kb': 0}

profile = {
    'cpu': get_cpu_info(),
    'gpu': get_gpu_info(),
    'memory': get_memory_info(),
    'has_battery': Path('/sys/class/power_supply/BAT0').exists()
}

with open('/etc/tunix/hardware/profile.json', 'w') as f:
    json.dump(profile, f, indent=2)
EOF

# Create optimization state directory
mkdir -p /var/lib/tunix/state
touch /var/lib/tunix/state/last_optimization

# Set up version tracking
echo "1.0.0" > "$INSTALL_DIR/version"
for component in "${COMPONENTS[@]}"; do
    echo "1.0.0" > "$INSTALL_DIR/${component//_/-}.version"
done

# Set permissions
chown -R root:root "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod -R 644 "$CONFIG_DIR"
chmod -R 644 "$LOG_DIR"
chmod 755 "$CONFIG_DIR" "$LOG_DIR"

echo "Installation complete. Starting services..."

# Start services in correct order
systemctl start tunix-coordinator
sleep 2
for service in "${SERVICES[@]}"; do
    if [[ "$service" != "tunix-coordinator" ]]; then
        systemctl start "$service"
        echo "  Started $service"
        sleep 1
    fi
done

echo "TUNIX optimization components have been installed and configured."
echo "Monitor the system status with: tunix-system-control"