# TUNIX Installation Guide

## System Requirements

### Minimum Requirements
- 4GB RAM
- 20GB disk space
- 2 core CPU
- 256MB GPU memory
- USB drive (for installation media)

### Recommended Requirements
- 8GB RAM
- 50GB disk space
- 4 core CPU
- 1GB GPU memory
- SSD storage

## Pre-Installation Steps

1. **Download TUNIX**
   - Visit the official TUNIX website
   - Download the latest ISO file
   - Verify the download using provided SHA256 checksums

2. **Create Installation Media**
   - Use Etcher, Rufus, or dd to write the ISO to a USB drive
   - For Windows: Use Rufus
   - For Linux/macOS: Use Etcher or dd command

3. **Backup Your Data**
   - Back up all important data before installation
   - If dual-booting, ensure you have enough free space

## Installation Process

1. **Boot from USB**
   - Insert the USB drive
   - Boot your computer from the USB
   - Select "Install TUNIX" from the boot menu

2. **Language Selection**
   - Choose your preferred language
   - This will be used during installation and as system default

3. **Hardware Detection**
   - The installer automatically detects your hardware
   - Review detected components
   - Configure specific hardware settings if needed

4. **Installation Type**
   - Choose between:
     - Clean install (use entire disk)
     - Dual boot (install alongside other OS)
     - Custom partitioning
   - For beginners, "Clean install" is recommended

5. **Disk Setup**
   - Select target drive for installation
   - Review partition layout
   - Confirm changes

6. **User Setup**
   - Create your username and password
   - Choose computer name
   - Select privacy settings

7. **Theme Selection**
   - Choose between Light and Dark theme
   - Select accent colors
   - Preview desktop layout

8. **Software Selection**
   - Choose software bundles:
     - Productivity (Office suite, email client)
     - Development (IDEs, version control)
     - Multimedia (Video/audio tools)
     - Gaming (Steam, Lutris)

9. **Installation**
   - The system will now install
   - This typically takes 15-30 minutes
   - Progress and time remaining will be shown

10. **First Boot**
    - Remove USB drive when prompted
    - System will restart
    - Log in to your new TUNIX system

## Post-Installation

1. **System Updates**
   - First boot will check for updates
   - Install any available updates

2. **Driver Installation**
   - Additional drivers will be installed if needed
   - NVIDIA users: Configure graphics settings

3. **System Customization**
   - Use TUNIX Settings to customize your system
   - Configure additional hardware
   - Set up backups

## Troubleshooting

### Common Issues

1. **USB Not Booting**
   - Check BIOS/UEFI boot order
   - Try different USB port
   - Recreate installation media

2. **Graphics Issues**
   - Use safe graphics mode from boot menu
   - Install proper drivers after installation

3. **Wi-Fi Not Working**
   - Connect via ethernet if possible
   - Additional drivers will be installed automatically

4. **Boot Problems**
   - Use boot repair option from live USB
   - Check UEFI/Legacy boot settings

### Getting Help

- Visit TUNIX forums
- Join TUNIX community chat
- Submit bug reports on GitHub
- Check documentation wiki

## Advanced Topics

### Custom Partitioning
- Root partition (/) - Minimum 20GB
- Swap - Equal to RAM size
- Home (/home) - Remaining space
- EFI (/boot/efi) - 512MB if UEFI system

### Encryption
- Full disk encryption available
- Home directory encryption option
- Configure during installation

### Dual Boot
- Windows compatibility assured
- Other Linux distributions supported
- Automatic bootloader configuration