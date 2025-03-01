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
    for cmd in debootstrap squashfs-tools xorriso isolinux; do
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
        # Placeholder - in real script would download from Ubuntu mirrors
        # wget -O "$WORK_DIR/$UBUNTU_ISO" "https://releases.ubuntu.com/22.04/$UBUNTU_ISO"
        error "Please download $UBUNTU_ISO to $WORK_DIR manually"
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
    mount -o loop "$WORK_DIR/$UBUNTU_ISO" "$MOUNT_DIR"
    
    # Copy contents
    rsync -av "$MOUNT_DIR/" "$EXTRACT_DIR/"
    
    # Unmount
    umount "$MOUNT_DIR"
    
    success "ISO contents extracted"
}

# Apply TUNIX customizations
apply_customizations() {
    log "Applying TUNIX customizations..."
    
    # Extract the squashfs filesystem
    unsquashfs -d "$CHROOT_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs"
    
    # Apply branding
    cp -r "$(pwd)/branding/"* "$CHROOT_DIR/usr/share/backgrounds/"
    
    # Apply UI enhancements
    log "Applying UI enhancements..."
    # Will add specific commands for UI enhancements
    
    # Apply system configurations
    log "Applying system configurations..."
    # Will add specific commands for system configuration
    
    # Install custom packages
    log "Installing custom packages..."
    # Will add specific commands for package installation
    
    success "TUNIX customizations applied"
}

# Rebuild squashfs and ISO
build_iso() {
    log "Building TUNIX ISO..."
    
    # Rebuild squashfs
    rm -f "$EXTRACT_DIR/casper/filesystem.squashfs"
    mksquashfs "$CHROOT_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs"
    
    # Update filesystem size
    printf $(du -sx --block-size=1 "$CHROOT_DIR" | cut -f1) > "$EXTRACT_DIR/casper/filesystem.size"
    
    # Update ISO data
    sed -i 's/Ubuntu/TUNIX/g' "$EXTRACT_DIR/README.diskdefines"
    
    # Rebuild ISO
    cd "$EXTRACT_DIR"
    xorriso -as mkisofs -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
        -c isolinux/boot.cat -b isolinux/isolinux.bin -no-emul-boot \
        -boot-load-size 4 -boot-info-table -eltorito-alt-boot \
        -e boot/grub/efi.img -no-emul-boot -isohybrid-gpt-basdat \
        -o "$OUTPUT_ISO" .
    
    success "TUNIX ISO built successfully at $OUTPUT_ISO"
}

# Main execution
main() {
    log "Starting TUNIX build process..."
    check_requirements
    prepare_environment
    extract_iso
    apply_customizations
    build_iso
    success "TUNIX build completed successfully"
}

main "$@"