#!/usr/bin/python3

import subprocess
import json
import os
from typing import Dict, List, Tuple

class HardwareDetector:
    def __init__(self):
        self.gpu_info = {}
        self.audio_info = {}
        self.network_info = {}
        self.printer_info = {}
        self.compatibility_db = "/usr/share/tunix/installer/hardware_compatibility.json"

    def detect_all(self) -> Dict:
        """Detect all hardware components and return compatibility info"""
        return {
            'gpu': self.detect_graphics(),
            'audio': self.detect_audio(),
            'network': self.detect_network(),
            'printer': self.detect_printers()
        }

    def detect_graphics(self) -> Dict:
        """Detect graphics hardware and determine required drivers"""
        try:
            lspci = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
            gpu_lines = [l for l in lspci.stdout.split('\n') if 'VGA' in l or '3D' in l]
            
            for line in gpu_lines:
                if 'NVIDIA' in line:
                    self.gpu_info['nvidia'] = self._get_nvidia_driver_version(line)
                elif 'AMD' in line or 'ATI' in line:
                    self.gpu_info['amd'] = True
                elif 'Intel' in line:
                    self.gpu_info['intel'] = True

            return self.gpu_info
        except Exception as e:
            return {'error': str(e)}

    def detect_audio(self) -> Dict:
        """Detect audio devices and configurations"""
        try:
            aplay = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
            self.audio_info['devices'] = [
                line.split(':')[1].strip()
                for line in aplay.stdout.split('\n')
                if 'card' in line
            ]
            return self.audio_info
        except Exception as e:
            return {'error': str(e)}

    def detect_network(self) -> Dict:
        """Detect network interfaces and required drivers"""
        try:
            # Detect WiFi devices
            iwconfig = subprocess.run(['iwconfig'], capture_output=True, text=True)
            self.network_info['wifi'] = [
                line.split()[0]
                for line in iwconfig.stdout.split('\n')
                if 'IEEE' in line
            ]

            # Detect ethernet devices
            with open('/proc/net/dev', 'r') as f:
                self.network_info['ethernet'] = [
                    line.split(':')[0].strip()
                    for line in f
                    if 'eth' in line or 'enp' in line
                ]

            return self.network_info
        except Exception as e:
            return {'error': str(e)}

    def detect_printers(self) -> Dict:
        """Detect printers and required drivers"""
        try:
            lpinfo = subprocess.run(['lpinfo', '-v'], capture_output=True, text=True)
            self.printer_info['devices'] = [
                line.split()[-1]
                for line in lpinfo.stdout.split('\n')
                if 'usb' in line or 'socket' in line
            ]
            return self.printer_info
        except Exception as e:
            return {'error': str(e)}

    def _get_nvidia_driver_version(self, pci_line: str) -> str:
        """Determine the appropriate NVIDIA driver version"""
        # Extract PCI ID and check against compatibility database
        pci_id = pci_line.split('[')[-1].split(']')[0]
        
        if os.path.exists(self.compatibility_db):
            with open(self.compatibility_db, 'r') as f:
                compat_data = json.load(f)
                for driver, cards in compat_data['nvidia'].items():
                    if pci_id in cards:
                        return driver
        
        # Default to latest stable driver if no match found
        return "nvidia-driver-525"

    def get_driver_recommendations(self) -> List[str]:
        """Generate list of recommended drivers based on detected hardware"""
        recommendations = []
        
        # Graphics drivers
        if 'nvidia' in self.gpu_info:
            recommendations.append(self.gpu_info['nvidia'])
        if 'amd' in self.gpu_info:
            recommendations.append('xserver-xorg-video-amdgpu')
        if 'intel' in self.gpu_info:
            recommendations.append('xserver-xorg-video-intel')

        # Network drivers
        if self.network_info.get('wifi'):
            recommendations.append('firmware-iwlwifi')
            recommendations.append('firmware-realtek')

        return recommendations

    def check_compatibility(self) -> Tuple[bool, List[str]]:
        """Check overall system compatibility and return status with warnings"""
        warnings = []
        is_compatible = True

        # Check minimum system requirements
        mem_info = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        if mem_info < (4 * 1024 * 1024 * 1024):  # 4GB
            warnings.append("Low memory detected: 4GB or more recommended")
            is_compatible = False

        # Check disk space
        df = subprocess.run(['df', '/'], capture_output=True, text=True)
        available_space = int(df.stdout.split('\n')[1].split()[3]) * 1024  # Convert to bytes
        if available_space < (20 * 1024 * 1024 * 1024):  # 20GB
            warnings.append("Insufficient disk space: 20GB or more required")
            is_compatible = False

        return is_compatible, warnings