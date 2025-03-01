#!/usr/bin/python3

import subprocess
import json
import os
from typing import Dict, List, Optional

class MultimediaConfig:
    def __init__(self):
        self.config_dir = "/etc/tunix/multimedia"
        os.makedirs(self.config_dir, exist_ok=True)
        self.codec_packages = {
            'video': [
                'ffmpeg',
                'x264',
                'x265',
                'libvpx',
                'libva-intel-driver',
                'libva-utils',
                'vdpau-driver-all'
            ],
            'audio': [
                'pulseaudio',
                'pipewire',
                'pipewire-pulse',
                'pipewire-alsa',
                'pipewire-jack',
                'alsa-utils',
                'lsp-plugins'
            ],
            'image': [
                'webp',
                'libjpeg-turbo',
                'libpng',
                'librsvg2-common'
            ],
            'gstreamer': [
                'gstreamer1.0-plugins-base',
                'gstreamer1.0-plugins-good',
                'gstreamer1.0-plugins-bad',
                'gstreamer1.0-plugins-ugly',
                'gstreamer1.0-libav',
                'gstreamer1.0-vaapi'
            ]
        }

    def detect_multimedia_capabilities(self) -> Dict:
        """Detect system multimedia capabilities"""
        capabilities = {
            'hardware_acceleration': self._detect_hw_acceleration(),
            'audio_devices': self._detect_audio_devices(),
            'available_codecs': self._check_installed_codecs(),
            'missing_codecs': self._find_missing_codecs()
        }
        
        # Save detection results
        with open(f"{self.config_dir}/capabilities.json", 'w') as f:
            json.dump(capabilities, f, indent=2)
        
        return capabilities

    def configure_system(self) -> None:
        """Configure system based on detected capabilities"""
        capabilities = self.detect_multimedia_capabilities()
        
        # Install missing codecs
        self._install_missing_codecs(capabilities['missing_codecs'])
        
        # Configure hardware acceleration
        if capabilities['hardware_acceleration']['available']:
            self._configure_hw_acceleration(capabilities['hardware_acceleration'])
        
        # Configure audio
        self._configure_audio(capabilities['audio_devices'])
        
        # Create optimal configurations
        self._create_app_configs()

    def _detect_hw_acceleration(self) -> Dict:
        """Detect hardware acceleration capabilities"""
        hw_accel = {
            'available': False,
            'type': None,
            'devices': []
        }
        
        # Check for VA-API
        try:
            vainfo = subprocess.run(['vainfo'], capture_output=True, text=True)
            if 'VA-API version' in vainfo.stdout:
                hw_accel['available'] = True
                hw_accel['type'] = 'vaapi'
                for line in vainfo.stdout.split('\n'):
                    if 'supported profile' in line.lower():
                        hw_accel['devices'].append(line.strip())
        except FileNotFoundError:
            pass

        # Check for VDPAU
        try:
            vdpauinfo = subprocess.run(['vdpauinfo'], capture_output=True, text=True)
            if 'VDPAU Driver' in vdpauinfo.stdout:
                hw_accel['available'] = True
                hw_accel['type'] = 'vdpau'
                for line in vdpauinfo.stdout.split('\n'):
                    if 'decoder capabilities' in line.lower():
                        hw_accel['devices'].append(line.strip())
        except FileNotFoundError:
            pass

        return hw_accel

    def _detect_audio_devices(self) -> Dict:
        """Detect audio devices and capabilities"""
        devices = {
            'output': [],
            'input': [],
            'backend': None
        }
        
        # Check audio backend
        if subprocess.run(['pidof', 'pipewire'], capture_output=True).returncode == 0:
            devices['backend'] = 'pipewire'
        elif subprocess.run(['pidof', 'pulseaudio'], capture_output=True).returncode == 0:
            devices['backend'] = 'pulseaudio'
        
        # Get audio devices
        try:
            pactl = subprocess.run(['pactl', 'list'], capture_output=True, text=True)
            for line in pactl.stdout.split('\n'):
                if 'Name: ' in line:
                    device = line.split('Name: ')[1].strip()
                    if 'output' in device.lower():
                        devices['output'].append(device)
                    elif 'input' in device.lower():
                        devices['input'].append(device)
        except FileNotFoundError:
            pass

        return devices

    def _check_installed_codecs(self) -> List[str]:
        """Check which codecs are already installed"""
        installed = []
        for category in self.codec_packages.values():
            for package in category:
                if subprocess.run(['dpkg', '-l', package], 
                                capture_output=True).returncode == 0:
                    installed.append(package)
        return installed

    def _find_missing_codecs(self) -> List[str]:
        """Find which required codecs are missing"""
        installed = self._check_installed_codecs()
        missing = []
        for category in self.codec_packages.values():
            for package in category:
                if package not in installed:
                    missing.append(package)
        return missing

    def _install_missing_codecs(self, missing_codecs: List[str]) -> None:
        """Install missing codec packages"""
        if missing_codecs:
            subprocess.run(['apt-get', 'update'])
            subprocess.run(['apt-get', 'install', '-y'] + missing_codecs)

    def _configure_hw_acceleration(self, hw_config: Dict) -> None:
        """Configure hardware acceleration"""
        # Configure VA-API
        if hw_config['type'] == 'vaapi':
            with open('/etc/environment', 'a') as f:
                f.write('\nLIBVA_DRIVER_NAME=iHD\n')
                f.write('VDPAU_DRIVER=va_gl\n')
        
        # Configure Firefox for hardware acceleration
        os.makedirs('/etc/firefox/policies', exist_ok=True)
        with open('/etc/firefox/policies/policies.json', 'w') as f:
            json.dump({
                'policies': {
                    'HardwareAcceleration': True,
                    'WebGL': True,
                    'DontCheckDefaultBrowser': True
                }
            }, f, indent=2)

    def _configure_audio(self, audio_config: Dict) -> None:
        """Configure audio system"""
        if audio_config['backend'] == 'pipewire':
            # Configure PipeWire for optimal audio
            pw_config = """
context.properties = {
    default.clock.rate = 48000
    default.clock.quantum = 1024
    default.clock.min-quantum = 32
    default.clock.max-quantum = 8192
}
"""
            os.makedirs('/etc/pipewire/pipewire.conf.d', exist_ok=True)
            with open('/etc/pipewire/pipewire.conf.d/tunix.conf', 'w') as f:
                f.write(pw_config)

    def _create_app_configs(self) -> None:
        """Create optimal configurations for multimedia applications"""
        # VLC configuration for hardware acceleration
        vlc_config = """
[codec]
hardware-decoding=1
"""
        os.makedirs('/etc/tunix/app-defaults/vlc', exist_ok=True)
        with open('/etc/tunix/app-defaults/vlc/vlcrc', 'w') as f:
            f.write(vlc_config)

        # MPV configuration
        mpv_config = """
vo=gpu
hwdec=auto
profile=gpu-hq
"""
        os.makedirs('/etc/tunix/app-defaults/mpv', exist_ok=True)
        with open('/etc/tunix/app-defaults/mpv/mpv.conf', 'w') as f:
            f.write(mpv_config)

if __name__ == "__main__":
    config = MultimediaConfig()
    config.configure_system()