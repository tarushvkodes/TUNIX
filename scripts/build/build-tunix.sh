#!/bin/bash

# TUNIX Build Script
# Copyright © Tarushv Kosgi 2025

set -e

# Configuration
WORK_DIR="/tmp/tunix-build"
CHROOT_DIR="$WORK_DIR/chroot"
ISO_DIR="$WORK_DIR/iso"
OUTPUT_DIR="$(pwd)/output"
LOG_FILE="$OUTPUT_DIR/build.log"
UBUNTU_URL="https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso"
ISO_NAME="tunix-22.04.iso"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    log_message "Checking build requirements..."
    
    # Check for root privileges
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root"
        exit 1
    }
    
    # Check required packages
    REQUIRED_PKGS="debootstrap squashfs-tools xorriso isolinux"
    for pkg in $REQUIRED_PKGS; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            apt-get install -y "$pkg"
        fi
    done
}

prepare_workspace() {
    log_message "Preparing workspace..."
    
    # Create working directories
    mkdir -p "$WORK_DIR" "$CHROOT_DIR" "$ISO_DIR" "$OUTPUT_DIR"
    
    # Download Ubuntu ISO if not present
    if [ ! -f "$WORK_DIR/ubuntu.iso" ]; then
        wget -O "$WORK_DIR/ubuntu.iso" "$UBUNTU_URL"
    fi
    
    # Mount and extract ISO
    mount -o loop "$WORK_DIR/ubuntu.iso" "$ISO_DIR"
    rsync --exclude=/casper/filesystem.squashfs -a "$ISO_DIR/" "$WORK_DIR/extracted_iso"
    unsquashfs -d "$CHROOT_DIR" "$ISO_DIR/casper/filesystem.squashfs"
}

customize_system() {
    log_message "Customizing system..."
    
    # Mount required filesystems for chroot
    mount --bind /dev "$CHROOT_DIR/dev"
    mount --bind /run "$CHROOT_DIR/run"
    mount -t proc none "$CHROOT_DIR/proc"
    mount -t sysfs none "$CHROOT_DIR/sys"
    
    # Copy TUNIX files into chroot
    cp -r /usr/local/share/tunix "$CHROOT_DIR/usr/local/share/"
    
    # Chroot and customize
    chroot "$CHROOT_DIR" /bin/bash -c "
        # Update system
        apt-get update
        apt-get upgrade -y
        
        # Install TUNIX packages
        bash /usr/local/share/tunix/custom-packages/install-packages.sh
        
        # Configure UI
        bash /usr/local/share/tunix/scripts/post-install/configure-ui.sh
        
        # Install Plymouth theme
        bash /usr/local/share/tunix/branding/plymouth/install-plymouth-theme.sh
        
        # Optimize system
        bash /usr/local/share/tunix/scripts/post-install/optimize-system.sh
        
        # Clean up
        apt-get autoremove -y
        apt-get clean
        rm -rf /tmp/* /var/tmp/*
    "
}

create_iso() {
    log_message "Creating ISO image..."
    
    # Create new squashfs
    mksquashfs "$CHROOT_DIR" "$WORK_DIR/extracted_iso/casper/filesystem.squashfs" -comp xz
    
    # Update ISO files
    printf $(du -sx --block-size=1 "$CHROOT_DIR" | cut -f1) > "$WORK_DIR/extracted_iso/casper/filesystem.size"
    
    # Generate ISO
    xorriso -as mkisofs \
        -iso-level 3 \
        -full-iso9660-filenames \
        -volid "TUNIX" \
        -eltorito-boot boot/grub/bios.img \
        -no-emul-boot \
        -boot-load-size 4 \
        -boot-info-table \
        --grub2-boot-info \
        --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img \
        -eltorito-catalog boot/grub/boot.cat \
        -output "$OUTPUT_DIR/$ISO_NAME" \
        -graft-points \
        "$WORK_DIR/extracted_iso" \
        /boot/grub/bios.img=isolinux/bios.img \
        /EFI/BOOT/=$(pwd)/EFI/BOOT
}

cleanup() {
    log_message "Cleaning up..."
    
    # Unmount filesystems
    umount "$CHROOT_DIR/dev" || true
    umount "$CHROOT_DIR/run" || true
    umount "$CHROOT_DIR/proc" || true
    umount "$CHROOT_DIR/sys" || true
    umount "$ISO_DIR" || true
    
    # Remove work directory
    rm -rf "$WORK_DIR"
}

main() {
    log_message "Starting TUNIX build process"
    
    check_requirements
    prepare_workspace
    customize_system
    create_iso
    cleanup
    
    log_message "Build completed successfully. ISO available at: $OUTPUT_DIR/$ISO_NAME"
}

trap cleanup EXIT
main