#!/bin/bash
# TUNIX System Optimization Script
# Applies optimizations based on hardware profile and current system state

set -e

PROFILE_FILE="/etc/tunix/hardware_profile.json"
CONFIG_DIR="/etc/tunix/config.d"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

apply_cpu_optimizations() {
    local profile=$(jq -r '.performance_profile' "$PROFILE_FILE")
    local governor=$(jq -r ".performance_profiles.\"$profile\".power_management.cpu_governor" "$PROFILE_FILE")
    
    # Set CPU governor
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo "$governor" > "$cpu" 2>/dev/null || true
    done
    
    # Configure CPU energy performance preference if supported
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference ]; then
        local pref=$(jq -r ".performance_profiles.\"$profile\".power_management.energy_performance_preference" "$PROFILE_FILE")
        for cpu in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
            echo "$pref" > "$cpu" 2>/dev/null || true
        done
    fi
}

apply_memory_optimizations() {
    # Get total memory in GB
    local total_mem=$(($(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024))
    local profile
    
    if [ "$total_mem" -lt 4 ]; then
        profile="low_memory"
    elif [ "$total_mem" -ge 16 ]; then
        profile="high_memory"
    else
        profile="balanced"
    fi
    
    # Apply memory optimizations from hardware compatibility database
    local swappiness=$(jq -r ".optimizations.${profile}.recommendations.\"vm.swappiness\"" "$PROFILE_FILE")
    local cache_pressure=$(jq -r ".optimizations.${profile}.recommendations.\"vm.vfs_cache_pressure\"" "$PROFILE_FILE")
    
    sysctl -w vm.swappiness="$swappiness"
    sysctl -w vm.vfs_cache_pressure="$cache_pressure"
    
    # Configure ZRAM if recommended
    if jq -e ".optimizations.${profile}.recommendations.zram" "$PROFILE_FILE" > /dev/null; then
        if ! lsmod | grep -q zram; then
            modprobe zram
            echo lz4 > /sys/block/zram0/comp_algorithm
            echo "${total_mem}G" > /sys/block/zram0/disksize
            mkswap /dev/zram0
            swapon -p 100 /dev/zram0
        fi
    fi
}

apply_storage_optimizations() {
    # Detect storage type
    local is_ssd=false
    if [ -d "/sys/block/sda" ] && cat /sys/block/sda/queue/rotational | grep -q "^0$"; then
        is_ssd=true
    fi
    
    if [ "$is_ssd" = true ]; then
        # Apply SSD optimizations
        local recommendations=$(jq -r '.optimizations.ssd.recommendations' "$PROFILE_FILE")
        
        # Enable TRIM
        systemctl enable fstrim.timer
        systemctl start fstrim.timer
        
        # Optimize I/O scheduler
        echo "mq-deadline" > /sys/block/sda/queue/scheduler
    else
        # Apply HDD optimizations
        local readahead=$(jq -r '.optimizations.hdd.recommendations.readahead' "$PROFILE_FILE")
        blockdev --setra "$readahead" /dev/sda
        
        # Set I/O scheduler
        echo "bfq" > /sys/block/sda/queue/scheduler
    fi
}

apply_gpu_optimizations() {
    local profile=$(jq -r '.performance_profile' "$PROFILE_FILE")
    local gpu_power=$(jq -r ".performance_profiles.\"$profile\".power_management.gpu_power" "$PROFILE_FILE")
    
    # NVIDIA GPU optimizations
    if [ -f /usr/bin/nvidia-settings ]; then
        if [ "$gpu_power" = "performance" ]; then
            nvidia-settings -a "[gpu:0]/GpuPowerMizerMode=1"
        elif [ "$gpu_power" = "balanced" ]; then
            nvidia-settings -a "[gpu:0]/GpuPowerMizerMode=2"
        elif [ "$gpu_power" = "battery" ]; then
            nvidia-settings -a "[gpu:0]/GpuPowerMizerMode=3"
        fi
    fi
    
    # AMD GPU optimizations
    if [ -d "/sys/class/drm/card0/device/power_dpm_state" ]; then
        case "$gpu_power" in
            "performance")
                echo "performance" > /sys/class/drm/card0/device/power_dpm_state
                ;;
            "balanced")
                echo "balanced" > /sys/class/drm/card0/device/power_dpm_state
                ;;
            "battery")
                echo "battery" > /sys/class/drm/card0/device/power_dpm_state
                ;;
        esac
    fi
}

apply_network_optimizations() {
    # Enable BBR congestion control if available
    if grep -q "bbr" /proc/sys/net/ipv4/tcp_available_congestion_control; then
        echo "bbr" > /proc/sys/net/ipv4/tcp_congestion_control
    fi
    
    # Optimize network settings
    sysctl -w net.core.netdev_max_backlog=16384
    sysctl -w net.core.somaxconn=8192
    sysctl -w net.ipv4.tcp_fastopen=3
    sysctl -w net.ipv4.tcp_max_syn_backlog=8192
}

main() {
    log "Starting TUNIX system optimization"
    
    if [ ! -f "$PROFILE_FILE" ]; then
        log "Error: Hardware profile not found"
        exit 1
    fi
    
    # Apply optimizations
    log "Applying CPU optimizations"
    apply_cpu_optimizations
    
    log "Applying memory optimizations"
    apply_memory_optimizations
    
    log "Applying storage optimizations"
    apply_storage_optimizations
    
    log "Applying GPU optimizations"
    apply_gpu_optimizations
    
    log "Applying network optimizations"
    apply_network_optimizations
    
    # Make optimizations persistent
    mkdir -p /etc/sysctl.d
    sysctl -p
    
    log "System optimization completed"
}

# Run main function
main

#!/bin/bash

# Setup directories
mkdir -p /etc/tunix/{config,hardware,power,thermal,network/routing,monitor,diagnostics,system-control}
mkdir -p /var/log/tunix
mkdir -p /usr/local/lib/tunix
mkdir -p /usr/local/bin

# Install required packages
apt-get update
apt-get install -y \
    python3-psutil \
    python3-systemd \
    python3-daemon \
    python3-curses \
    python3-numpy \
    ethtool \
    iw \
    tlp \
    powertop \
    lm-sensors

# Copy Python scripts to system location
SCRIPTS=(
    "hardware_profile.py"
    "power_manager.py"
    "system_diagnostics.py"
    "system_monitor.py"
    "network_monitor.py"
    "network_optimizer.py"
    "network_routing.py"
    "performance_analyzer.py"
    "performance_monitor.py"
    "thermal_control.py"
    "system_config.py"
    "system_coordinator.py"
)

for script in "${SCRIPTS[@]}"; do
    cp "$script" /usr/local/lib/tunix/
    chmod +x "/usr/local/lib/tunix/$script"
done

# Install CLI tools
cp tunix-monitor-cli.py /usr/local/bin/tunix-monitor
chmod +x /usr/local/bin/tunix-monitor

# Install systemd services
SERVICES=(
    "tunix-system-control.service"
    "tunix-power.service"
    "tunix-thermal.service"
    "tunix-network.service"
    "tunix-network-routing.service"
    "tunix-monitor.service"
    "tunix-performance.service"
    "tunix-optimize.service"
    "tunix-coordinator.service"
)

for service in "${SERVICES[@]}"; do
    cp "$service" /etc/systemd/system/
done

# Create default configurations
cat > /etc/tunix/config/system_config.json << EOF
{
    "version": "1.0.0",
    "optimization": {
        "power_management": {
            "enabled": true,
            "default_profile": "balanced",
            "battery_threshold": 20,
            "thermal_threshold": 80
        },
        "thermal_control": {
            "enabled": true,
            "prediction_enabled": true,
            "target_temp": 70,
            "warning_temp": 80,
            "critical_temp": 85
        },
        "network": {
            "enabled": true,
            "auto_tune": true,
            "bbr_enabled": true,
            "buffer_autoscale": true
        },
        "performance": {
            "io_scheduler": "bfq",
            "swappiness": 60,
            "vfs_cache_pressure": 100,
            "dirty_ratio": 20
        }
    },
    "monitoring": {
        "enabled": true,
        "interval": 1,
        "log_retention_days": 7
    },
    "services": {
        "power_manager": true,
        "thermal_control": true,
        "network_optimizer": true,
        "system_monitor": true
    }
}
EOF

# Configure TLP
cat > /etc/tlp.d/00-tunix.conf << EOF
# TUNIX TLP Configuration
TLP_DEFAULT_MODE=AC
TLP_PERSISTENT_DEFAULT=0
CPU_SCALING_GOVERNOR_ON_AC=performance
CPU_SCALING_GOVERNOR_ON_BAT=powersave
CPU_ENERGY_PERF_POLICY_ON_AC=performance
CPU_ENERGY_PERF_POLICY_ON_BAT=power
DISK_IDLE_SECS_ON_AC=0
DISK_IDLE_SECS_ON_BAT=2
MAX_LOST_WORK_SECS_ON_AC=15
MAX_LOST_WORK_SECS_ON_BAT=60
EOF

# Configure log rotation
cat > /etc/logrotate.d/tunix << EOF
/var/log/tunix/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 0640 root root
}
EOF

# Generate initial hardware profile
python3 /usr/local/lib/tunix/hardware_profile.py

# Enable TCP BBR congestion control if available
if grep -q "bbr" /proc/sys/net/ipv4/tcp_available_congestion_control 2>/dev/null; then
    echo "bbr" > /proc/sys/net/ipv4/tcp_congestion_control
fi

# Configure sysctl optimizations
cat > /etc/sysctl.d/99-tunix-optimizations.conf << EOF
# Network optimizations
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 87380 16777216
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0

# VM optimizations
vm.dirty_ratio = 20
vm.dirty_background_ratio = 10
vm.swappiness = 60
vm.vfs_cache_pressure = 100
vm.page_lock_unfairness = 1

# File system optimizations
fs.inotify.max_user_watches = 524288
EOF

# Apply sysctl settings
sysctl --system

# Start and enable services
systemctl daemon-reload

for service in "${SERVICES[@]}"; do
    systemctl enable "${service%.*}"
    systemctl start "${service%.*}"
done

# Configure powertop auto-tune
powertop --auto-tune

echo "TUNIX optimization components have been installed and configured."
echo "System optimization and monitoring services are now running."
echo "Run 'tunix-monitor' to launch the system monitor interface."

# Initial optimization pass
python3 /usr/local/lib/tunix/system_coordinator.py --initial-setup