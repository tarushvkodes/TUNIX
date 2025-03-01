#!/bin/bash

# TUNIX System Maintenance Script
# Copyright © Tarushv Kosgi 2025

set -e

LOG_FILE="/var/log/tunix/maintenance.log"
BACKUP_DIR="/var/backups/tunix"
HEALTH_REPORT="/var/log/tunix/health-report.txt"
MAINTENANCE_LOCK="/var/run/tunix-maintenance.lock"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check for root and create lock
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

if [ -f "$MAINTENANCE_LOCK" ]; then
    echo "Maintenance already running"
    exit 1
fi
touch "$MAINTENANCE_LOCK"

# Ensure cleanup on exit
trap 'rm -f $MAINTENANCE_LOCK' EXIT

# Create directories
mkdir -p "$(dirname "$LOG_FILE")" "$BACKUP_DIR"

# System update function
update_system() {
    log_message "Starting system update"
    
    # Update package lists
    apt-get update
    
    # Create snapshot before upgrade
    if command -v timeshift >/dev/null; then
        timeshift --create --comments "Before system upgrade"
    fi
    
    # Perform upgrade
    DEBIAN_FRONTEND=noninteractive apt-get -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        dist-upgrade
    
    # Clean up
    apt-get -y autoremove
    apt-get clean
}

# Check disk health
check_disk_health() {
    log_message "Checking disk health"
    
    # Check disk space
    df -h > "$HEALTH_REPORT"
    
    # Check for failing disks
    for disk in $(lsblk -d -n -o NAME); do
        if [[ $disk == sd* || $disk == nvme* ]]; then
            smartctl -H "/dev/$disk" >> "$HEALTH_REPORT" 2>&1 || true
        fi
    done
    
    # Check filesystem errors
    for mount in $(df -h --output=target | tail -n +2); do
        if [ "$mount" = "/" ]; then
            touch /forcefsck
            log_message "Scheduled root filesystem check for next boot"
        fi
    done
}

# Clean system
clean_system() {
    log_message "Cleaning system"
    
    # Clean package cache
    apt-get clean
    
    # Clean old logs
    find /var/log -type f -name "*.gz" -delete
    find /var/log -type f -name "*.1" -delete
    
    # Clean temporary files
    rm -rf /tmp/*
    rm -rf /var/tmp/*
    
    # Clean user caches older than 30 days
    find /home -type f -name ".cache" -atime +30 -delete
}

# Check system services
check_services() {
    log_message "Checking system services"
    
    # Check critical services
    CRITICAL_SERVICES="networkd-dispatcher NetworkManager systemd-logind gdm"
    for service in $CRITICAL_SERVICES; do
        systemctl is-active --quiet $service || {
            log_message "Warning: $service is not running"
            systemctl restart $service
        }
    done
    
    # Check for failed services
    systemctl --failed >> "$HEALTH_REPORT"
}

# Backup system configuration
backup_config() {
    log_message "Backing up system configuration"
    
    BACKUP_FILE="$BACKUP_DIR/config-$(date +%Y%m%d).tar.gz"
    
    # Create backup of important configuration
    tar czf "$BACKUP_FILE" \
        /etc/fstab \
        /etc/default \
        /etc/tunix \
        /etc/apt/sources.list.d \
        /etc/X11/xorg.conf.d \
        /etc/dconf/db/tunix.d 2>/dev/null || true
    
    # Rotate old backups (keep last 5)
    find "$BACKUP_DIR" -type f -name "config-*.tar.gz" | sort -r | tail -n +6 | xargs -r rm
}

# Optimize system
optimize_system() {
    log_message "Optimizing system"
    
    # Update locate database
    updatedb
    
    # Rebuild font cache
    fc-cache -f
    
    # Update GRUB
    update-grub
    
    # Update initramfs if needed
    if [ -f /var/run/reboot-required.pkgs ]; then
        update-initramfs -u
    fi
}

# Generate maintenance report
generate_report() {
    log_message "Generating maintenance report"
    
    {
        echo "TUNIX System Maintenance Report"
        echo "Date: $(date)"
        echo "----------------------------------------"
        echo "Disk Usage:"
        df -h
        echo "----------------------------------------"
        echo "Service Status:"
        systemctl --failed
        echo "----------------------------------------"
        echo "Recent System Changes:"
        tail -n 50 /var/log/dpkg.log
        echo "----------------------------------------"
        echo "System Health Report:"
        cat "$HEALTH_REPORT"
    } > "$HEALTH_REPORT.new"
    
    mv "$HEALTH_REPORT.new" "$HEALTH_REPORT"
}

# Main execution
main() {
    log_message "Starting TUNIX system maintenance"
    
    update_system
    check_disk_health
    clean_system
    check_services
    backup_config
    optimize_system
    generate_report
    
    # Check if reboot is needed
    if [ -f /var/run/reboot-required ]; then
        log_message "System requires a reboot"
    fi
    
    log_message "Maintenance completed successfully"
}

# Run main function
main