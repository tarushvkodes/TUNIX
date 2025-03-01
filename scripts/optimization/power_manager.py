#!/usr/bin/python3

import json
import os
import subprocess
import time
from typing import Dict, List, Optional
from pathlib import Path

class PowerManager:
    def __init__(self):
        self.config_dir = Path("/etc/tunix/power")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.config_dir / "power_profile.json"
        self.is_laptop = os.path.exists("/sys/class/power_supply/BAT0")
        
    def configure_power_management(self) -> None:
        """Configure power management based on system type and hardware"""
        profile = self._detect_system_profile()
        self._save_profile(profile)
        self._apply_profile(profile)
        self._setup_monitoring()

    def _detect_system_profile(self) -> Dict:
        """Detect system characteristics for power profile"""
        profile = {
            "system_type": "laptop" if self.is_laptop else "desktop",
            "cpu_info": self._get_cpu_info(),
            "gpu_info": self._get_gpu_info(),
            "thermal_info": self._get_thermal_info(),
            "storage_info": self._get_storage_info()
        }
        
        # Determine optimal settings based on hardware
        profile["settings"] = self._generate_optimal_settings(profile)
        return profile

    def _get_cpu_info(self) -> Dict:
        """Get CPU information relevant for power management"""
        cpu_info = {
            "governors": self._get_available_governors(),
            "cores": self._get_core_count(),
            "frequencies": self._get_frequency_info(),
            "supports_intel_pstate": os.path.exists("/sys/devices/system/cpu/intel_pstate")
        }
        
        # Check for CPU specific features
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
            cpu_info["vendor"] = "intel" if "Intel" in cpuinfo else "amd" if "AMD" in cpuinfo else "other"
            
        return cpu_info

    def _get_gpu_info(self) -> Dict:
        """Get GPU information for power management"""
        gpu_info = {
            "type": "unknown",
            "has_optimus": False,
            "supports_power_control": False
        }
        
        # Check for NVIDIA
        try:
            nvidia_smi = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True)
            if nvidia_smi.returncode == 0:
                gpu_info["type"] = "nvidia"
                gpu_info["supports_power_control"] = True
                
                # Check for Optimus
                if os.path.exists("/proc/acpi/bbswitch"):
                    gpu_info["has_optimus"] = True
        except FileNotFoundError:
            pass
        
        # Check for AMD
        if os.path.exists("/sys/class/drm/card0/device/power_dpm_state"):
            gpu_info["type"] = "amd"
            gpu_info["supports_power_control"] = True
            
        return gpu_info

    def _get_thermal_info(self) -> Dict:
        """Get thermal characteristics of the system"""
        thermal_info = {
            "cooling_devices": [],
            "temp_sensors": [],
            "critical_temp": None
        }
        
        # Get thermal zones
        thermal_root = Path("/sys/class/thermal")
        for zone in thermal_root.glob("thermal_zone*"):
            try:
                with open(zone / "type", "r") as f:
                    zone_type = f.read().strip()
                with open(zone / "temp", "r") as f:
                    temp = int(f.read().strip()) / 1000  # Convert to Celsius
                thermal_info["temp_sensors"].append({
                    "type": zone_type,
                    "temp": temp
                })
            except (IOError, ValueError):
                continue
        
        # Get cooling devices
        for cooler in thermal_root.glob("cooling_device*"):
            try:
                with open(cooler / "type", "r") as f:
                    cooler_type = f.read().strip()
                thermal_info["cooling_devices"].append(cooler_type)
            except IOError:
                continue
                
        return thermal_info

    def _get_storage_info(self) -> Dict:
        """Get storage device power management capabilities"""
        storage_info = {
            "devices": [],
            "supports_apm": False,
            "supports_alpm": False
        }
        
        # Check for AHCI Link Power Management
        if os.path.exists("/sys/class/scsi_host/host0/link_power_management_policy"):
            storage_info["supports_alpm"] = True
            
        # Check disk types and capabilities
        for device in Path("/sys/block").glob("sd*"):
            try:
                with open(device / "queue/rotational", "r") as f:
                    is_ssd = f.read().strip() == "0"
                storage_info["devices"].append({
                    "name": device.name,
                    "type": "ssd" if is_ssd else "hdd",
                    "supports_apm": os.path.exists(device / "device/power/control")
                })
            except IOError:
                continue
                
        return storage_info

    def _generate_optimal_settings(self, profile: Dict) -> Dict:
        """Generate optimal power management settings based on system profile"""
        settings = {
            "cpu": self._get_cpu_settings(profile),
            "gpu": self._get_gpu_settings(profile),
            "thermal": self._get_thermal_settings(profile),
            "storage": self._get_storage_settings(profile)
        }
        
        if profile["system_type"] == "laptop":
            settings.update(self._get_laptop_specific_settings())
            
        return settings

    def _get_cpu_settings(self, profile: Dict) -> Dict:
        """Generate CPU power management settings"""
        cpu_settings = {
            "ac_governor": "performance",
            "bat_governor": "powersave" if self.is_laptop else "performance",
            "energy_perf_bias": "performance" if not self.is_laptop else "balance-power",
            "turbo_boost": True if not self.is_laptop else "auto"
        }
        
        if profile["cpu_info"]["supports_intel_pstate"]:
            cpu_settings.update({
                "min_perf_pct": 0 if self.is_laptop else 15,
                "max_perf_pct": 100,
                "no_turbo": 0 if not self.is_laptop else "auto"
            })
            
        return cpu_settings

    def _get_gpu_settings(self, profile: Dict) -> Dict:
        """Generate GPU power management settings"""
        gpu_settings = {
            "power_control": "auto",
            "render_mode": "integrated" if self.is_laptop else "performance"
        }
        
        if profile["gpu_info"]["type"] == "nvidia":
            gpu_settings.update({
                "nvidia_power_mode": "adaptive" if self.is_laptop else "maximum",
                "optimus_mode": "on-demand" if profile["gpu_info"]["has_optimus"] else None
            })
        elif profile["gpu_info"]["type"] == "amd":
            gpu_settings.update({
                "dpm_state": "balanced" if self.is_laptop else "performance",
                "power_level": "auto" if self.is_laptop else "high"
            })
            
        return gpu_settings

    def _get_thermal_settings(self, profile: Dict) -> Dict:
        """Generate thermal management settings"""
        return {
            "mode": "active" if not self.is_laptop else "adaptive",
            "cpu_temps": {
                "critical": 95,
                "high": 85,
                "target": 75
            },
            "fan_control": "auto",
            "power_limit": None if not self.is_laptop else "15W"
        }

    def _get_storage_settings(self, profile: Dict) -> Dict:
        """Generate storage power management settings"""
        settings = {
            "alpm_policy": "max_performance" if not self.is_laptop else "medium_power",
            "spindown_time": None if not self.is_laptop else 600,
            "apm_level": 254 if not self.is_laptop else 128
        }
        
        # Adjust for SSDs
        for device in profile["storage_info"]["devices"]:
            if device["type"] == "ssd":
                settings["ssd_power_control"] = {
                    "runtime_pm": "on" if self.is_laptop else "off",
                    "autosuspend_delay_ms": 2000 if self.is_laptop else 0
                }
                
        return settings

    def _get_laptop_specific_settings(self) -> Dict:
        """Generate laptop-specific power settings"""
        return {
            "battery": {
                "charge_threshold_start": 75,
                "charge_threshold_stop": 80,
                "discharge_rate_limit": "auto"
            },
            "screen": {
                "brightness_ac": 100,
                "brightness_bat": 50,
                "dim_time": 45,
                "dpms_timeout": 600
            },
            "wifi": {
                "power_save": True,
                "power_level": "auto"
            },
            "usb": {
                "autosuspend": True,
                "autosuspend_delay_ms": 2000
            }
        }

    def _save_profile(self, profile: Dict) -> None:
        """Save power profile to disk"""
        with open(self.profile_file, 'w') as f:
            json.dump(profile, f, indent=2)

    def _apply_profile(self, profile: Dict) -> None:
        """Apply power management settings"""
        settings = profile["settings"]
        
        # Apply CPU settings
        self._apply_cpu_settings(settings["cpu"])
        
        # Apply GPU settings
        self._apply_gpu_settings(settings["gpu"])
        
        # Apply storage settings
        self._apply_storage_settings(settings["storage"])
        
        # Apply thermal settings
        self._apply_thermal_settings(settings["thermal"])
        
        # Apply laptop-specific settings if applicable
        if self.is_laptop and "battery" in settings:
            self._apply_laptop_settings(settings)

    def _get_available_governors(self) -> List[str]:
        """Get available CPU governors"""
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors") as f:
                return f.read().strip().split()
        except:
            return ["performance", "powersave"]

    def _get_core_count(self) -> int:
        """Get number of CPU cores"""
        try:
            return len([f for f in os.listdir("/sys/devices/system/cpu") if f.startswith("cpu") and f[3:].isdigit()])
        except:
            return 1

    def _get_frequency_info(self) -> Dict:
        """Get CPU frequency information"""
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq") as f:
                max_freq = int(f.read().strip())
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq") as f:
                min_freq = int(f.read().strip())
            return {"min": min_freq, "max": max_freq}
        except:
            return {"min": None, "max": None}

if __name__ == "__main__":
    manager = PowerManager()
    manager.configure_power_management()