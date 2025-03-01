#!/usr/bin/python3
import json
import os
import subprocess
from typing import Dict, List

class HardwareProfiler:
    def __init__(self):
        self.profile_path = '/etc/tunix/hardware_profile.json'
        self.config_dir = '/etc/tunix/config.d'
        os.makedirs(self.config_dir, exist_ok=True)

    def load_profile(self) -> Dict:
        """Load the hardware profile generated during installation"""
        with open(self.profile_path, 'r') as f:
            return json.load(f)

    def apply_optimizations(self) -> None:
        """Apply system optimizations based on hardware profile"""
        profile = self.load_profile()
        perf_profile = profile['performance_profile']

        # Apply profile-specific optimizations
        if 'laptop' in perf_profile:
            self._configure_laptop_power_management()
        if 'performance' in perf_profile:
            self._configure_performance_mode()
        else:
            self._configure_balanced_mode()

        # Configure GPU optimizations
        self._configure_gpu(profile['hardware']['gpu'])

        # Configure CPU optimizations
        self._configure_cpu(profile['hardware']['cpu'])

        # Apply recommended driver configurations
        self._configure_drivers(profile.get('driver_recommendations', []))

    def _configure_laptop_power_management(self) -> None:
        """Configure laptop-specific power management"""
        # Configure TLP for better battery life
        tlp_config = """
# TUNIX TLP Configuration
TLP_DEFAULT_MODE=AC
TLP_PERSISTENT_DEFAULT=0
CPU_SCALING_GOVERNOR_ON_AC=performance
CPU_SCALING_GOVERNOR_ON_BAT=powersave
CPU_ENERGY_PERF_POLICY_ON_AC=performance
CPU_ENERGY_PERF_POLICY_ON_BAT=power
"""
        with open('/etc/tlp.d/00-tunix.conf', 'w') as f:
            f.write(tlp_config)

        # Enable and start TLP
        subprocess.run(['systemctl', 'enable', 'tlp.service'])
        subprocess.run(['systemctl', 'start', 'tlp.service'])

    def _configure_performance_mode(self) -> None:
        """Configure system for maximum performance"""
        # Set CPU governor to performance
        with open('/etc/tunix/config.d/cpu-performance.conf', 'w') as f:
            f.write('GOVERNOR="performance"')

        # Configure system limits for better performance
        sysctl_conf = """
# TUNIX Performance Optimizations
vm.swappiness=10
kernel.sched_autogroup_enabled=1
kernel.sched_latency_ns=6000000
"""
        with open('/etc/sysctl.d/99-tunix-performance.conf', 'w') as f:
            f.write(sysctl_conf)

    def _configure_balanced_mode(self) -> None:
        """Configure system for balanced performance and efficiency"""
        # Set CPU governor to schedutil
        with open('/etc/tunix/config.d/cpu-balanced.conf', 'w') as f:
            f.write('GOVERNOR="schedutil"')

        # Configure system for balanced operation
        sysctl_conf = """
# TUNIX Balanced Mode Optimizations
vm.swappiness=60
kernel.sched_autogroup_enabled=1
"""
        with open('/etc/sysctl.d/99-tunix-balanced.conf', 'w') as f:
            f.write(sysctl_conf)

    def _configure_gpu(self, gpu_info: Dict) -> None:
        """Configure GPU-specific optimizations"""
        if 'nvidia' in gpu_info:
            # Configure NVIDIA settings
            nvidia_conf = """
Section "Device"
    Identifier "NVIDIA Card"
    Driver "nvidia"
    Option "NoLogo" "true"
    Option "RegistryDwords" "PowerMizerEnable=0x1; PerfLevelSrc=0x2222"
EndSection
"""
            with open('/etc/X11/xorg.conf.d/10-nvidia.conf', 'w') as f:
                f.write(nvidia_conf)

        elif 'amd' in gpu_info:
            # Configure AMD settings
            amd_conf = """
Section "Device"
    Identifier "AMD Graphics"
    Driver "amdgpu"
    Option "TearFree" "true"
    Option "DRI" "3"
EndSection
"""
            with open('/etc/X11/xorg.conf.d/10-amdgpu.conf', 'w') as f:
                f.write(amd_conf)

    def _configure_cpu(self, cpu_info: Dict) -> None:
        """Configure CPU-specific optimizations"""
        cpu_flags = cpu_info.get('flags', [])
        
        # Enable CPU microcode updates
        if 'intel' in cpu_info.get('model', '').lower():
            subprocess.run(['apt-get', 'install', '-y', 'intel-microcode'])
        elif 'amd' in cpu_info.get('model', '').lower():
            subprocess.run(['apt-get', 'install', '-y', 'amd64-microcode'])

        # Configure CPU frequency scaling
        if cpu_info.get('cores', 0) >= 4:
            with open('/etc/tunix/config.d/cpu-scaling.conf', 'w') as f:
                f.write('SCALING_GOVERNOR="schedutil"\n')
                f.write('ENERGY_PERF_BIAS="performance"\n')

    def _configure_drivers(self, recommended_drivers: List[str]) -> None:
        """Configure and install recommended drivers"""
        # Create a consolidated driver configuration
        driver_conf = {
            'packages': recommended_drivers,
            'post_install': []
        }

        # Add post-installation steps for specific drivers
        if 'nvidia-prime' in recommended_drivers:
            driver_conf['post_install'].append('prime-select')

        # Save driver configuration for system updates
        with open('/etc/tunix/config.d/drivers.conf', 'w') as f:
            json.dump(driver_conf, f, indent=2)

if __name__ == "__main__":
    profiler = HardwareProfiler()
    profiler.apply_optimizations()