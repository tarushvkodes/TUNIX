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