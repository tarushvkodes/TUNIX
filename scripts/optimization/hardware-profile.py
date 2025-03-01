#!/usr/bin/python3
import json
import os
import subprocess
from typing import Dict, List, Optional
from pathlib import Path

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

class HardwareProfileGenerator:
    def __init__(self):
        self.profile_dir = Path("/etc/tunix/hardware")
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def generate_profile(self) -> Dict:
        """Generate comprehensive hardware profile"""
        profile = {
            "cpu": self._get_cpu_info(),
            "memory": self._get_memory_info(),
            "storage": self._get_storage_info(),
            "gpu": self._get_gpu_info(),
            "network": self._get_network_info(),
            "power": self._get_power_info(),
            "thermal": self._get_thermal_capabilities(),
            "performance_profile": self._determine_performance_profile()
        }

        # Save profile
        profile_path = self.profile_dir / "hardware_profile.json"
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)

        return profile

    def _get_cpu_info(self) -> Dict:
        """Get detailed CPU information"""
        info = {}
        try:
            cpu_info = subprocess.check_output("lscpu", text=True)
            for line in cpu_info.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.strip()] = value.strip()

            # Add thermal info
            thermal_zones = Path("/sys/class/thermal")
            if thermal_zones.exists():
                info["thermal_zones"] = []
                for zone in thermal_zones.glob("thermal_zone*"):
                    if (zone / "type").exists() and "cpu" in (zone / "type").read_text().lower():
                        info["thermal_zones"].append({
                            "zone": zone.name,
                            "type": (zone / "type").read_text().strip()
                        })
        except Exception as e:
            info["error"] = str(e)
        return info

    def _get_memory_info(self) -> Dict:
        """Get memory configuration"""
        info = {}
        try:
            meminfo = Path("/proc/meminfo").read_text()
            for line in meminfo.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.strip()] = value.strip()
        except Exception as e:
            info["error"] = str(e)
        return info

    def _get_storage_info(self) -> List[Dict]:
        """Get storage device information"""
        devices = []
        try:
            lsblk = subprocess.check_output(["lsblk", "-Jo", "NAME,SIZE,TYPE,ROTA,MODEL"], text=True)
            devices = json.loads(lsblk)["blockdevices"]
        except Exception as e:
            devices.append({"error": str(e)})
        return devices

    def _get_gpu_info(self) -> Dict:
        """Get GPU information"""
        info = {"devices": []}
        
        # Check for NVIDIA GPUs
        try:
            nvidia_smi = subprocess.check_output(["nvidia-smi", "-q", "-x"], text=True)
            if nvidia_smi:
                info["devices"].append({
                    "type": "nvidia",
                    "data": nvidia_smi
                })
        except:
            pass

        # Check for AMD GPUs
        try:
            for card in Path("/sys/class/drm").glob("card*"):
                if (card / "device/vendor").exists():
                    vendor = (card / "device/vendor").read_text().strip()
                    if "0x1002" in vendor:  # AMD vendor ID
                        info["devices"].append({
                            "type": "amd",
                            "card": card.name,
                            "vendor": vendor
                        })
        except Exception as e:
            info["error"] = str(e)

        return info

    def _get_network_info(self) -> Dict:
        """Get network interface information"""
        info = {"interfaces": []}
        try:
            ip_link = subprocess.check_output(["ip", "-j", "link", "show"], text=True)
            info["interfaces"] = json.loads(ip_link)
            
            # Add wireless interface details
            for interface in Path("/sys/class/net").glob("*"):
                if (interface / "wireless").exists():
                    wireless_info = {
                        "name": interface.name,
                        "wireless": True
                    }
                    if (interface / "power").exists():
                        wireless_info["power_management"] = True
                    info["interfaces"].append(wireless_info)
        except Exception as e:
            info["error"] = str(e)
        return info

    def _get_power_info(self) -> Dict:
        """Get power management capabilities"""
        info = {
            "batteries": [],
            "cpu_scaling": {},
            "supported_governors": []
        }
        
        # Check batteries
        try:
            for battery in Path("/sys/class/power_supply").glob("BAT*"):
                bat_info = {}
                for attr in ["status", "capacity", "technology", "cycle_count"]:
                    if (battery / attr).exists():
                        bat_info[attr] = (battery / attr).read_text().strip()
                info["batteries"].append(bat_info)
        except Exception as e:
            info["battery_error"] = str(e)

        # Check CPU scaling capabilities
        try:
            cpu0_freq = Path("/sys/devices/system/cpu/cpu0/cpufreq")
            if cpu0_freq.exists():
                for governor in (cpu0_freq / "scaling_available_governors").read_text().strip().split():
                    info["supported_governors"].append(governor)
        except Exception as e:
            info["cpu_scaling_error"] = str(e)

        return info

    def _get_thermal_capabilities(self) -> Dict:
        """Get thermal management capabilities of the system"""
        capabilities = {
            "cooling_devices": [],
            "temp_sensors": [],
            "supports_fan_control": False,
            "supports_power_limits": False,
            "thermal_zones": []
        }

        try:
            # Check cooling devices
            cooling_root = Path("/sys/class/thermal")
            for device in cooling_root.glob("cooling_device*"):
                try:
                    with open(device / "type", "r") as f:
                        dev_type = f.read().strip()
                    with open(device / "max_state", "r") as f:
                        max_state = int(f.read().strip())
                    
                    capabilities["cooling_devices"].append({
                        "type": dev_type,
                        "max_state": max_state,
                        "path": str(device)
                    })
                    
                    if "fan" in dev_type.lower():
                        capabilities["supports_fan_control"] = True
                except:
                    continue

            # Check thermal zones
            for zone in cooling_root.glob("thermal_zone*"):
                try:
                    with open(zone / "type", "r") as f:
                        zone_type = f.read().strip()
                    with open(zone / "temp", "r") as f:
                        temp = int(f.read().strip()) / 1000.0
                    
                    zone_info = {
                        "type": zone_type,
                        "current_temp": temp,
                        "path": str(zone)
                    }
                    
                    # Check if zone has trip points
                    trips_point = zone / "trip_point_0_temp"
                    if trips_point.exists():
                        zone_info["has_trip_points"] = True
                    
                    capabilities["thermal_zones"].append(zone_info)
                except:
                    continue

            # Check for power limit support
            if self._check_power_limit_support():
                capabilities["supports_power_limits"] = True

        except Exception as e:
            capabilities["error"] = str(e)

        return capabilities

    def _check_power_limit_support(self) -> bool:
        """Check if system supports power limits"""
        # Check Intel RAPL
        if Path("/sys/class/powercap/intel-rapl").exists():
            return True
            
        # Check NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=power.limit", "--format=csv,noheader"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except:
            pass
            
        # Check AMD
        if list(Path("/sys/class/drm").glob("card*/device/power_dpm_force_performance_level")):
            return True
            
        return False

    def _determine_performance_profile(self) -> List[str]:
        """Determine appropriate performance profiles"""
        profiles = []
        
        # Check if system is a laptop
        if self._get_power_info()["batteries"]:
            profiles.append("laptop")
            
        # Check if system is high-performance
        cpu_info = self._get_cpu_info()
        if cpu_info.get("CPU(s)") and int(cpu_info["CPU(s)"]) >= 8:
            profiles.append("performance")
            
        # Check if system has dedicated GPU
        gpu_info = self._get_gpu_info()
        if any(dev["type"] in ["nvidia", "amd"] for dev in gpu_info["devices"]):
            profiles.append("graphics")
            
        return profiles

    def generate_optimization_recommendations(self) -> Dict[str, List[str]]:
        """Generate optimization recommendations based on hardware profile"""
        profile = self.generate_profile()
        recommendations = {
            "performance": [],
            "power": [],
            "thermal": [],
            "storage": []
        }

        # CPU recommendations
        cpu_info = profile["cpu"]
        if int(cpu_info.get("CPU(s)", 0)) >= 8:
            recommendations["performance"].append("Enable parallel compilation")
            recommendations["performance"].append("Configure CPU governor for performance")

        # Memory recommendations
        mem_info = profile["memory"]
        total_mem = int(mem_info.get("MemTotal", "0 kB").split()[0])
        if total_mem > 16000000:  # More than 16GB
            recommendations["performance"].append("Optimize swap usage for high memory")
        else:
            recommendations["performance"].append("Configure zram for better memory management")

        # Storage recommendations
        for device in profile["storage"]:
            if device.get("type") == "disk" and device.get("rota") == "1":
                recommendations["storage"].append("Enable disk write caching")
                recommendations["power"].append("Configure disk power management")

        # Power recommendations
        if "laptop" in profile["performance_profile"]:
            recommendations["power"].extend([
                "Enable CPU frequency scaling",
                "Configure display power management",
                "Enable USB autosuspend",
                "Configure wireless power saving"
            ])

        # Thermal recommendations
        thermal_caps = profile["thermal"]
        if thermal_caps["supports_fan_control"]:
            recommendations["thermal"].append("Enable smart fan control")
        if thermal_caps["supports_power_limits"]:
            recommendations["thermal"].append("Configure dynamic power limits")
        if len(thermal_caps["thermal_zones"]) > 0:
            recommendations["thermal"].append("Enable predictive thermal management")

        return recommendations

if __name__ == "__main__":
    profiler = HardwareProfiler()
    profiler.apply_optimizations()
    generator = HardwareProfileGenerator()
    profile = generator.generate_profile()
    recommendations = generator.generate_optimization_recommendations()
    
    print("Hardware Profile:")
    print(json.dumps(profile, indent=2))
    print("\nOptimization Recommendations:")
    print(json.dumps(recommendations, indent=2))