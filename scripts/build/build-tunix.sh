#!/bin/bash
# TUNIX Build Script
# Copyright © Tarushv Kosgi 2025
# This script transforms a base Ubuntu installation into TUNIX

set -e  # Exit on any error

# Configuration
WORK_DIR="$(pwd)/tunix-build"
UBUNTU_ISO="ubuntu-22.04-desktop-amd64.iso"  # Update as needed
MOUNT_DIR="$WORK_DIR/mnt"
EXTRACT_DIR="$WORK_DIR/extract"
CHROOT_DIR="$WORK_DIR/chroot"
OUTPUT_ISO="$WORK_DIR/tunix-os.iso"
PROJECT_ROOT="$(pwd)"

# Color output
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

# Check for required tools
check_requirements() {
    log "Checking requirements..."
    for cmd in debootstrap squashfs-tools xorriso isolinux rsync wget; do
        if ! command -v $cmd &> /dev/null; then
            error "$cmd is required but not installed. Please install it and try again."
        fi
    done
    success "All required tools are available"
}

# Prepare working environment
prepare_environment() {
    log "Preparing build environment..."
    mkdir -p "$WORK_DIR" "$MOUNT_DIR" "$EXTRACT_DIR" "$CHROOT_DIR"
    
    # Download Ubuntu ISO if not present
    if [ ! -f "$WORK_DIR/$UBUNTU_ISO" ]; then
        log "Downloading Ubuntu ISO..."
        wget -O "$WORK_DIR/$UBUNTU_ISO" "https://releases.ubuntu.com/22.04/$UBUNTU_ISO" || \
        error "Failed to download Ubuntu ISO. Please download $UBUNTU_ISO to $WORK_DIR manually"
    fi
    
    success "Environment prepared"
}

# Extract ISO contents
extract_iso() {
    log "Mounting and extracting Ubuntu ISO..."
    if [ -d "$EXTRACT_DIR/casper" ]; then
        log "ISO already extracted, skipping..."
        return
    fi
    
    # Mount ISO
    mount -o loop "$WORK_DIR/$UBUNTU_ISO" "$MOUNT_DIR" || error "Failed to mount ISO"
    
    # Copy contents
    rsync -av "$MOUNT_DIR/" "$EXTRACT_DIR/" || error "Failed to extract ISO contents"
    
    # Unmount
    umount "$MOUNT_DIR"
    
    success "ISO contents extracted"
}

# Extract and prepare the squashfs filesystem
prepare_chroot() {
    log "Preparing chroot environment..."
    
    # Extract the squashfs filesystem
    if [ ! -d "$CHROOT_DIR/usr" ]; then
        log "Extracting squashfs filesystem..."
        unsquashfs -d "$CHROOT_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs" || error "Failed to extract squashfs"
    else
        log "Filesystem already extracted, skipping..."
    fi
    
    # Prepare chroot environment
    mount --bind /dev "$CHROOT_DIR/dev" || error "Failed to bind mount /dev"
    mount --bind /run "$CHROOT_DIR/run" || error "Failed to bind mount /run"
    mount --bind /proc "$CHROOT_DIR/proc" || error "Failed to bind mount /proc"
    mount --bind /sys "$CHROOT_DIR/sys" || error "Failed to bind mount /sys"
    
    success "Chroot environment prepared"
}

# Copy TUNIX custom files into the chroot environment
copy_tunix_files() {
    log "Copying TUNIX custom files..."
    
    # Create TUNIX directories in chroot
    mkdir -p "$CHROOT_DIR/usr/share/tunix/"{themes,icons,wallpapers,app-theming/firefox}
    mkdir -p "$CHROOT_DIR/usr/local/bin"
    
    # Copy branding assets
    cp -rv "$PROJECT_ROOT/branding"/* "$CHROOT_DIR/usr/share/tunix/" || log "No branding files to copy"
    
    # Copy custom packages and scripts
    mkdir -p "$CHROOT_DIR/tmp/tunix-setup"
    cp -v "$PROJECT_ROOT/custom-packages/package-list.txt" "$CHROOT_DIR/tmp/tunix-setup/" || log "No package list to copy"
    cp -v "$PROJECT_ROOT/custom-packages/install-packages.sh" "$CHROOT_DIR/tmp/tunix-setup/" || log "No install script to copy"
    chmod +x "$CHROOT_DIR/tmp/tunix-setup/install-packages.sh"
    
    # Copy post-install scripts
    cp -v "$PROJECT_ROOT/scripts/post-install/configure-ui.sh" "$CHROOT_DIR/usr/local/bin/tunix-configure-ui" || log "No UI configuration script to copy"
    chmod +x "$CHROOT_DIR/usr/local/bin/tunix-configure-ui"
    
    success "TUNIX files copied into chroot environment"
}

# Apply TUNIX customizations within the chroot environment
apply_customizations() {
    log "Applying TUNIX customizations..."
    
    # Run commands inside chroot
    chroot "$CHROOT_DIR" /bin/bash -c "cd /tmp/tunix-setup && ./install-packages.sh" || error "Failed to run package installation"
    
    # Set up first boot configuration
    cat > "$CHROOT_DIR/etc/xdg/autostart/tunix-first-setup.desktop" << EOF
[Desktop Entry]
Name=TUNIX First Boot Setup
Exec=/usr/local/bin/tunix-configure-ui
Terminal=false
Type=Application
StartupNotify=true
NoDisplay=true
X-GNOME-Autostart-Phase=Applications
EOF
    
    # Update system information
    echo "TUNIX" > "$CHROOT_DIR/etc/hostname"
    sed -i 's/Ubuntu/TUNIX/g' "$CHROOT_DIR/etc/issue"
    sed -i 's/Ubuntu/TUNIX/g' "$CHROOT_DIR/etc/issue.net"
    sed -i 's/Ubuntu/TUNIX/g' "$CHROOT_DIR/etc/lsb-release"
    sed -i 's/ubuntu/tunix/g' "$CHROOT_DIR/etc/apt/sources.list"
    
    # Update GRUB theme
    sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="TUNIX"/g' "$CHROOT_DIR/etc/default/grub"
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"/g' "$CHROOT_DIR/etc/default/grub"
    
    # Update Plymouth theme
    chroot "$CHROOT_DIR" /bin/bash -c "update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth /usr/share/tunix/plymouth/tunix.plymouth 100"
    chroot "$CHROOT_DIR" /bin/bash -c "update-alternatives --set default.plymouth /usr/share/tunix/plymouth/tunix.plymouth"
    chroot "$CHROOT_DIR" /bin/bash -c "update-initramfs -u"
    
    success "TUNIX customizations applied"
}

# Clean up the chroot environment
cleanup_chroot() {
    log "Cleaning up chroot environment..."
    
    # Clean apt cache
    chroot "$CHROOT_DIR" /bin/bash -c "apt-get clean"
    
    # Remove temporary files
    rm -rf "$CHROOT_DIR/tmp/tunix-setup"
    
    # Unmount filesystems
    umount "$CHROOT_DIR/sys"
    umount "$CHROOT_DIR/proc"
    umount "$CHROOT_DIR/run"
    umount "$CHROOT_DIR/dev"
    
    success "Chroot environment cleaned up"
}

# Rebuild squashfs and ISO
build_iso() {
    log "Building TUNIX ISO..."
    
    # Rebuild squashfs
    log "Creating squashfs filesystem... (this may take a while)"
    rm -f "$EXTRACT_DIR/casper/filesystem.squashfs"
    mksquashfs "$CHROOT_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs" -comp xz -Xbcj x86 || error "Failed to create squashfs"
    
    # Update filesystem size
    log "Updating filesystem size..."
    printf $(du -sx --block-size=1 "$CHROOT_DIR" | cut -f1) > "$EXTRACT_DIR/casper/filesystem.size"
    
    # Update ISO data
    sed -i 's/Ubuntu/TUNIX/g' "$EXTRACT_DIR/README.diskdefines"
    
    # Update isolinux configuration
    if [ -d "$EXTRACT_DIR/isolinux" ]; then
        sed -i 's/Ubuntu/TUNIX/g' "$EXTRACT_DIR/isolinux/txt.cfg"
        cp "$PROJECT_ROOT/branding/splash.png" "$EXTRACT_DIR/isolinux/splash.png" || log "No custom splash screen found"
    fi
    
    # Update GRUB configuration
    if [ -d "$EXTRACT_DIR/boot/grub" ]; then
        sed -i 's/Ubuntu/TUNIX/g' "$EXTRACT_DIR/boot/grub/grub.cfg"
        cp "$PROJECT_ROOT/branding/grub-background.png" "$EXTRACT_DIR/boot/grub/grub-background.png" || log "No custom GRUB background found"
    fi
    
    # Create TUNIX version file
    echo "TUNIX 1.0 Alpha" > "$EXTRACT_DIR/tunix-version"
    
    # Rebuild ISO
    log "Creating ISO image... (this may take a while)"
    cd "$EXTRACT_DIR"
    
    # Create md5sum.txt
    find . -type f -not -path "./md5sum.txt" -not -path "./boot/*" -not -path "./EFI/*" -exec md5sum {} \; > md5sum.txt
    
    # Build the ISO
    xorriso -as mkisofs -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
        -c isolinux/boot.cat -b isolinux/isolinux.bin -no-emul-boot \
        -boot-load-size 4 -boot-info-table -eltorito-alt-boot \
        -e boot/grub/efi.img -no-emul-boot -isohybrid-gpt-basdat \
        -V "TUNIX_OS" \
        -o "$OUTPUT_ISO" . || error "Failed to create ISO image"
    
    success "TUNIX ISO built successfully at $OUTPUT_ISO"
}

# Main execution
main() {
    log "Starting TUNIX build process..."
    
    # Get start time
    BUILD_START=$(date +%s)
    
    check_requirements
    prepare_environment
    extract_iso
    prepare_chroot
    copy_tunix_files
    apply_customizations
    cleanup_chroot
    build_iso
    
    # Calculate build duration
    BUILD_END=$(date +%s)
    BUILD_DURATION=$((BUILD_END - BUILD_START))
    BUILD_MINUTES=$((BUILD_DURATION / 60))
    BUILD_SECONDS=$((BUILD_DURATION % 60))
    
    success "TUNIX build completed successfully in ${BUILD_MINUTES}m ${BUILD_SECONDS}s"
    log "TUNIX ISO is available at: $OUTPUT_ISO"
}

main "$@"