#!/usr/bin/python3

import subprocess
import json
import os
from typing import Dict, List, Tuple, Optional

class HardwareDetector:
    def __init__(self):
        self.gpu_info = {}
        self.audio_info = {}
        self.network_info = {}
        self.printer_info = {}
        self.cpu_info = {}
        self.compatibility_db = "/usr/share/tunix/installer/hardware_compatibility.json"
        self.performance_profile = None

    def detect_all(self) -> Dict:
        """Detect all hardware components and return compatibility info"""
        hardware_info = {
            'gpu': self.detect_graphics(),
            'audio': self.detect_audio(),
            'network': self.detect_network(),
            'printer': self.detect_printers(),
            'cpu': self.detect_cpu(),
            'profile': self.determine_performance_profile()
        }
        self._save_hardware_profile(hardware_info)
        return hardware_info

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

    def detect_cpu(self) -> Dict:
        """Detect CPU capabilities and features"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpu_info = f.read()
            
            # Extract key CPU information
            self.cpu_info = {
                'model': self._extract_cpu_field(cpu_info, 'model name'),
                'cores': len([l for l in cpu_info.split('\n') if 'processor' in l]),
                'flags': self._extract_cpu_field(cpu_info, 'flags').split(),
                'virtualization': 'vmx' in cpu_info or 'svm' in cpu_info
            }
            return self.cpu_info
        except Exception as e:
            return {'error': str(e)}

    def determine_performance_profile(self) -> str:
        """Determine optimal performance profile based on hardware"""
        # Check if running on a laptop
        is_laptop = os.path.exists('/sys/class/power_supply/BAT0')
        
        # Analyze CPU capabilities
        cpu_score = self._calculate_cpu_score()
        gpu_score = self._calculate_gpu_score()
        
        if is_laptop:
            if cpu_score >= 8 and gpu_score >= 7:
                self.performance_profile = 'laptop-performance'
            elif cpu_score >= 5:
                self.performance_profile = 'laptop-balanced'
            else:
                self.performance_profile = 'laptop-powersave'
        else:
            if cpu_score >= 8 and gpu_score >= 7:
                self.performance_profile = 'desktop-performance'
            else:
                self.performance_profile = 'desktop-balanced'
        
        return self.performance_profile

    def _calculate_cpu_score(self) -> int:
        """Calculate CPU capability score (1-10)"""
        score = 5  # Default mid-range score
        
        if self.cpu_info:
            # Adjust score based on cores
            cores = self.cpu_info.get('cores', 4)
            score += min(cores // 2, 3)  # Up to +3 for core count
            
            # Adjust for CPU flags/features
            flags = self.cpu_info.get('flags', [])
            if 'avx2' in flags: score += 1
            if 'aes' in flags: score += 1
            
            # Cap score at 10
            score = min(score, 10)
        
        return score

    def _calculate_gpu_score(self) -> int:
        """Calculate GPU capability score (1-10)"""
        score = 5  # Default mid-range score
        
        if 'nvidia' in self.gpu_info:
            # Assume newer NVIDIA drivers indicate newer/better GPU
            driver_ver = self.gpu_info['nvidia'].split('-')[-1]
            if int(driver_ver) >= 525: score += 3
            elif int(driver_ver) >= 470: score += 2
        elif 'amd' in self.gpu_info:
            score += 2  # AMD GPUs generally good for basic acceleration
        elif 'intel' in self.gpu_info:
            score += 1  # Intel GPUs typically adequate for basic needs
        
        return min(score, 10)

    def _extract_cpu_field(self, cpuinfo: str, field: str) -> str:
        """Extract a specific field from cpuinfo output"""
        for line in cpuinfo.split('\n'):
            if field in line:
                return line.split(':')[1].strip()
        return ''

    def _save_hardware_profile(self, hardware_info: Dict) -> None:
        """Save hardware profile for system optimization"""
        profile_path = '/etc/tunix/hardware_profile.json'
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        
        with open(profile_path, 'w') as f:
            json.dump({
                'hardware': hardware_info,
                'performance_profile': self.performance_profile,
                'driver_recommendations': self.get_driver_recommendations()
            }, f, indent=2)

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
            # Add PRIME support for hybrid graphics
            if 'intel' in self.gpu_info:
                recommendations.append('nvidia-prime')
        if 'amd' in self.gpu_info:
            recommendations.append('xserver-xorg-video-amdgpu')
            recommendations.append('mesa-vulkan-drivers')
        if 'intel' in self.gpu_info:
            recommendations.append('xserver-xorg-video-intel')
            recommendations.append('intel-media-va-driver')
        
        # Network drivers
        if self.network_info.get('wifi'):
            recommendations.append('firmware-iwlwifi')
            recommendations.append('firmware-realtek')
            # Add better power management for WiFi
            recommendations.append('wireless-tools')
            recommendations.append('powertop')
        
        # Add performance optimization packages based on profile
        if self.performance_profile:
            if 'laptop' in self.performance_profile:
                recommendations.append('tlp')
                recommendations.append('thermald')
            if 'performance' in self.performance_profile:
                recommendations.append('cpupower-gui')
                recommendations.append('gamemode')
        
        return recommendations

    def check_compatibility(self) -> Tuple[bool, List[str], Optional[Dict]]:
        """Check overall system compatibility and return status with warnings and recommendations"""
        warnings = []
        recommendations = {}
        is_compatible = True

        # Check minimum system requirements
        mem_info = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        if mem_info < (4 * 1024 * 1024 * 1024):  # 4GB
            warnings.append("Low memory detected: 4GB or more recommended")
            recommendations['memory'] = "Consider upgrading to at least 4GB RAM for better performance"
            is_compatible = False

        # Check disk space
        df = subprocess.run(['df', '/'], capture_output=True, text=True)
        available_space = int(df.stdout.split('\n')[1].split()[3]) * 1024  # Convert to bytes
        if available_space < (20 * 1024 * 1024 * 1024):  # 20GB
            warnings.append("Insufficient disk space: 20GB or more required")
            recommendations['storage'] = "Free up at least 20GB of disk space before installation"
            is_compatible = False

        # Check CPU compatibility
        if self.cpu_info:
            if 'flags' in self.cpu_info:
                if 'lm' not in self.cpu_info['flags']:  # Check for 64-bit support
                    warnings.append("CPU does not support 64-bit operations")
                    is_compatible = False
                if self.cpu_info.get('cores', 0) < 2:
                    warnings.append("Single core CPU detected: dual-core or better recommended")
                    recommendations['cpu'] = "Consider upgrading to a multi-core CPU for better performance"

        return is_compatible, warnings, recommendations if recommendations else None