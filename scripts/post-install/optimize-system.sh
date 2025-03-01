#!/bin/bash
# TUNIX System Optimization Script
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

# Detect system type
detect_system_type() {
    log "Detecting system type..."
    
    # Check if system is a laptop or desktop
    if [ -d /sys/class/power_supply/BAT* ] || grep -q "Battery" /proc/acpi/battery/*/info 2>/dev/null; then
        SYSTEM_TYPE="laptop"
        log "System detected as laptop"
    else
        SYSTEM_TYPE="desktop"
        log "System detected as desktop"
    fi
    
    # Detect CPU vendor
    if grep -q "Intel" /proc/cpuinfo; then
        CPU_VENDOR="intel"
    elif grep -q "AMD" /proc/cpuinfo; then
        CPU_VENDOR="amd"
    else
        CPU_VENDOR="other"
    fi
    log "CPU detected as $CPU_VENDOR"
    
    # Detect GPU
    if lspci | grep -i vga | grep -i nvidia > /dev/null; then
        GPU_VENDOR="nvidia"
    elif lspci | grep -i vga | grep -i amd > /dev/null; then
        GPU_VENDOR="amd"
    else
        GPU_VENDOR="intel"
    fi
    log "GPU detected as $GPU_VENDOR"
}

# Optimize disk I/O
optimize_disk() {
    log "Optimizing disk I/O..."
    
    # Check if system uses SSD
    if [ -d /sys/block/sda/queue/rotational ] && [ "$(cat /sys/block/sda/queue/rotational)" -eq 0 ]; then
        log "SSD detected, applying SSD optimizations"
        
        # Enable TRIM
        if ! grep -q "discard" /etc/fstab; then
            log "Enabling TRIM for SSDs"
            # Add discard option to ext4 partitions
            sed -i 's/\(ext4.*defaults\)/\1,discard/' /etc/fstab
        fi
        
        # Set up scheduled TRIM
        if [ ! -f /etc/systemd/system/trim.timer ]; then
            log "Setting up weekly TRIM schedule"
            cat > /etc/systemd/system/trim.timer << EOF
[Unit]
Description=Weekly TRIM
Documentation=man:fstrim(8)

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
EOF

            cat > /etc/systemd/system/trim.service << EOF
[Unit]
Description=Run TRIM on SSD drives
Documentation=man:fstrim(8)

[Service]
Type=oneshot
ExecStart=/sbin/fstrim -av

[Install]
WantedBy=multi-user.target
EOF
            systemctl enable trim.timer
        fi
    else
        log "Rotational disk detected, applying HDD optimizations"
        # HDD specific optimizations can be added here
    fi
    
    # Improve swap usage
    log "Configuring swappiness"
    echo "vm.swappiness=10" > /etc/sysctl.d/99-tunix-swappiness.conf
    
    # Improve cache management
    echo "vm.vfs_cache_pressure=50" > /etc/sysctl.d/99-tunix-cache.conf
    
    success "Disk I/O optimization completed"
}

# Optimize CPU performance
optimize_cpu() {
    log "Optimizing CPU performance..."
    
    # Install and configure CPU frequency scaling
    if [ "$SYSTEM_TYPE" = "laptop" ]; then
        log "Setting up power-saving CPU governor for laptops"
        apt-get install -y cpufrequtils
        echo 'GOVERNOR="powersave"' > /etc/default/cpufrequtils
    else
        log "Setting up performance CPU governor for desktops"
        apt-get install -y cpufrequtils
        echo 'GOVERNOR="performance"' > /etc/default/cpufrequtils
    fi
    
    # Enable CPU mitigations with performance consideration
    log "Configuring CPU mitigations for best security/performance balance"
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT=".*"/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash mitigations=auto"/' /etc/default/grub
    update-grub
    
    success "CPU optimization completed"
}

# Optimize memory usage
optimize_memory() {
    log "Optimizing memory usage..."
    
    # Get system memory size in KB
    local mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    
    # Convert to GB
    local mem_gb=$((mem_total / 1024 / 1024))
    
    log "Detected ${mem_gb}GB of RAM"
    
    # Configure memory limits based on available RAM
    if [ $mem_gb -gt 16 ]; then
        # For systems with more than 16GB RAM
        echo "vm.dirty_ratio = 15" > /etc/sysctl.d/99-tunix-memory.conf
        echo "vm.dirty_background_ratio = 10" >> /etc/sysctl.d/99-tunix-memory.conf
    elif [ $mem_gb -gt 8 ]; then
        # For systems with 8-16GB RAM
        echo "vm.dirty_ratio = 10" > /etc/sysctl.d/99-tunix-memory.conf
        echo "vm.dirty_background_ratio = 5" >> /etc/sysctl.d/99-tunix-memory.conf
    else
        # For systems with less than 8GB RAM
        echo "vm.dirty_ratio = 5" > /etc/sysctl.d/99-tunix-memory.conf
        echo "vm.dirty_background_ratio = 3" >> /etc/sysctl.d/99-tunix-memory.conf
    fi
    
    # Configure compressed RAM
    if [ $mem_gb -lt 8 ]; then
        # For systems with limited RAM, enhance with zram
        log "Configuring zram for systems with limited RAM"
        apt-get install -y zram-config
        
        # Configure zram to use 50% of RAM
        echo 'PERCENT=50' > /etc/default/zramswap
    fi
    
    success "Memory optimization completed"
}

# Optimize network performance
optimize_network() {
    log "Optimizing network performance..."
    
    # Create network optimization sysctl config
    cat > /etc/sysctl.d/99-tunix-network.conf << EOF
# Increase TCP max buffer size
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Increase TCP buffer limits
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# Enable TCP window scaling
net.ipv4.tcp_window_scaling = 1

# Enable TCP timestamps
net.ipv4.tcp_timestamps = 1

# Enable TCP selective acknowledgments
net.ipv4.tcp_sack = 1

# Increase number of connections
net.core.somaxconn = 1024

# Protect against TCP SYN flood attacks
net.ipv4.tcp_syncookies = 1

# Reuse sockets in TIME_WAIT state
net.ipv4.tcp_tw_reuse = 1
EOF
    
    # Apply network settings
    sysctl -p /etc/sysctl.d/99-tunix-network.conf
    
    success "Network optimization completed"
}

# Optimize graphics performance
optimize_graphics() {
    log "Optimizing graphics performance..."
    
    case $GPU_VENDOR in
        nvidia)
            log "Configuring NVIDIA GPU optimizations"
            
            # If NVIDIA, ensure proper power management
            if [ -f /etc/modprobe.d/nvidia.conf ]; then
                if ! grep -q "NVreg_PreserveVideoMemoryAllocations=1" /etc/modprobe.d/nvidia.conf; then
                    echo "options nvidia NVreg_PreserveVideoMemoryAllocations=1 NVreg_TemporaryFilePath=/var/tmp" >> /etc/modprobe.d/nvidia.conf
                fi
            else
                echo "options nvidia NVreg_PreserveVideoMemoryAllocations=1 NVreg_TemporaryFilePath=/var/tmp" > /etc/modprobe.d/nvidia.conf
            fi
            
            # Apply optimal NVIDIA settings
            if command -v nvidia-settings &> /dev/null; then
                # Setup script to be run at login
                mkdir -p /etc/tunix/graphics
                cat > /etc/tunix/graphics/nvidia-optimize.sh << EOF
#!/bin/sh
nvidia-settings -a "[gpu:0]/GPUPowerMizerMode=1" # Prefer performance
nvidia-settings -a "[gpu:0]/GpuPowerMizerDefaultMode=1" # Prefer performance
EOF
                chmod +x /etc/tunix/graphics/nvidia-optimize.sh
                
                # Create autostart entry
                mkdir -p /etc/xdg/autostart
                cat > /etc/xdg/autostart/tunix-nvidia-optimize.desktop << EOF
[Desktop Entry]
Name=TUNIX NVIDIA Optimization
Exec=/etc/tunix/graphics/nvidia-optimize.sh
Terminal=false
Type=Application
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF
            fi
            ;;
            
        amd)
            log "Configuring AMD GPU optimizations"
            
            # Enable AMD specific optimizations
            if [ -d /sys/class/drm/card0/device/power ]; then
                echo "performance" > /sys/class/drm/card0/device/power/control
                
                # Create persistent rule
                cat > /etc/udev/rules.d/99-tunix-amd-gpu.rules << EOF
# Set AMD GPU power control to performance mode
KERNEL=="card0", SUBSYSTEM=="drm", DRIVERS=="amdgpu", ATTR{power/control}="performance"
EOF
            fi
            ;;
            
        intel)
            log "Configuring Intel GPU optimizations"
            
            # Enable Intel tear-free
            mkdir -p /etc/X11/xorg.conf.d
            cat > /etc/X11/xorg.conf.d/20-intel.conf << EOF
Section "Device"
    Identifier  "Intel Graphics"
    Driver      "intel"
    Option      "TearFree" "true"
    Option      "DRI" "3"
EndSection
EOF
            ;;
    esac
    
    success "Graphics optimization completed"
}

# Configure system for laptop power efficiency
optimize_laptop() {
    if [ "$SYSTEM_TYPE" != "laptop" ]; then
        return
    fi
    
    log "Applying laptop-specific optimizations..."
    
    # Install and configure TLP for power management
    apt-get install -y tlp tlp-rdw
    systemctl enable tlp.service
    
    # Configure power saving options
    cat > /etc/tlp.d/99-tunix-power.conf << EOF
# TUNIX custom power settings

# Battery charge thresholds (ThinkPad only)
START_CHARGE_THRESH_BAT0=75
STOP_CHARGE_THRESH_BAT0=95

# CPU energy/performance policies
CPU_ENERGY_PERF_POLICY_ON_AC=balance_performance
CPU_ENERGY_PERF_POLICY_ON_BAT=balance_power

# Set CPU governor
CPU_SCALING_GOVERNOR_ON_AC=performance
CPU_SCALING_GOVERNOR_ON_BAT=powersave

# Enable audio power saving
SOUND_POWER_SAVE_ON_AC=10
SOUND_POWER_SAVE_ON_BAT=10

# WIFI power saving
WIFI_PWR_ON_AC=off
WIFI_PWR_ON_BAT=on

# Runtime Power Management for PCIe devices
RUNTIME_PM_ON_AC=on
RUNTIME_PM_ON_BAT=auto
EOF
    
    # Enable powertop auto tune at boot
    apt-get install -y powertop
    
    cat > /etc/systemd/system/powertop.service << EOF
[Unit]
Description=Powertop tunings

[Service]
Type=oneshot
ExecStart=/usr/bin/powertop --auto-tune
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF
    systemctl enable powertop.service
    
    success "Laptop optimization completed"
}

# Apply system security enhancements
enhance_security() {
    log "Applying security enhancements..."
    
    # Enable automatic security updates
    apt-get install -y unattended-upgrades
    
    cat > /etc/apt/apt.conf.d/50unattended-upgrades << EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}";
    "\${distro_id}:\${distro_codename}-security";
    "\${distro_id}ESMApps:\${distro_codename}-apps-security";
    "\${distro_id}ESM:\${distro_codename}-infra-security";
};

Unattended-Upgrade::Package-Blacklist {
};

Unattended-Upgrade::Automatic-Reboot "false";
EOF
    
    # Enable UFW firewall with default settings
    apt-get install -y ufw
    ufw default deny incoming
    ufw default allow outgoing
    ufw enable
    
    # Harden SSH if installed
    if dpkg -l | grep -q openssh-server; then
        log "Hardening SSH configuration"
        sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
        sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
        systemctl restart ssh
    fi
    
    # Configure kernel hardening
    cat > /etc/sysctl.d/99-tunix-security.conf << EOF
# Kernel hardening settings
kernel.kptr_restrict = 1
kernel.dmesg_restrict = 1
kernel.unprivileged_bpf_disabled = 1
net.core.bpf_jit_harden = 2
kernel.yama.ptrace_scope = 1
EOF
    
    success "Security enhancements completed"
}

# Configure kernel for better desktop responsiveness
optimize_responsiveness() {
    log "Optimizing system responsiveness..."
    
    # Configure kernel for desktop responsiveness
    cat > /etc/sysctl.d/99-tunix-desktop.conf << EOF
# Reduce swap tendency
vm.swappiness = 10

# Improve file system performance
vm.vfs_cache_pressure = 50

# Improve Linux kernel responsiveness
kernel.sched_autogroup_enabled = 1
kernel.sched_latency_ns = 6000000
kernel.sched_min_granularity_ns = 3000000
kernel.sched_wakeup_granularity_ns = 2000000
EOF

    # Apply udev rule for improved I/O scheduling
    cat > /etc/udev/rules.d/60-tunix-io-scheduler.rules << EOF
# Set I/O scheduler for SSD devices
ACTION=="add|change", KERNEL=="sd[a-z]|mmcblk[0-9]*", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="mq-deadline"
# Set I/O scheduler for HDD devices
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="1", ATTR{queue/scheduler}="bfq"
EOF
    
    success "System responsiveness optimization completed"
}

# Main function
main() {
    log "Starting TUNIX system optimization..."
    
    # Check if running as root
    if [ "$(id -u)" -ne 0 ]; then
        error "This script must be run as root"
    fi
    
    detect_system_type
    optimize_disk
    optimize_cpu
    optimize_memory
    optimize_network
    optimize_graphics
    optimize_laptop
    enhance_security
    optimize_responsiveness
    
    # Apply all sysctl changes
    sysctl --system
    
    success "TUNIX system optimization completed successfully"
    log "Please reboot your system to apply all optimizations"
}

# Execute main function
main "$@"