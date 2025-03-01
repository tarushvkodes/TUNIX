#!/usr/bin/python3
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PowerProfile:
    name: str
    description: str
    cpu_governor: str
    cpu_boost: bool
    gpu_mode: str
    disk_power_save: bool
    wifi_power_save: bool
    screen_brightness: int
    usb_autosuspend: bool
    pcie_aspm: str

class PowerManager:
    def __init__(self):
        self.config_dir = Path("/etc/tunix/power")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename="/var/log/tunix/power_manager.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.profiles = self._load_power_profiles()
        self.current_profile = None
        self.on_battery = False
        self.battery_level = 100

    def _load_power_profiles(self) -> Dict[str, PowerProfile]:
        """Load power profiles from configuration"""
        try:
            profiles = {
                "performance": PowerProfile(
                    name="performance",
                    description="Maximum performance mode",
                    cpu_governor="performance",
                    cpu_boost=True,
                    gpu_mode="performance",
                    disk_power_save=False,
                    wifi_power_save=False,
                    screen_brightness=100,
                    usb_autosuspend=False,
                    pcie_aspm="performance"
                ),
                "balanced": PowerProfile(
                    name="balanced",
                    description="Balanced power and performance",
                    cpu_governor="schedutil",
                    cpu_boost=True,
                    gpu_mode="balanced",
                    disk_power_save=True,
                    wifi_power_save=True,
                    screen_brightness=70,
                    usb_autosuspend=True,
                    pcie_aspm="default"
                ),
                "powersave": PowerProfile(
                    name="powersave",
                    description="Maximum power saving",
                    cpu_governor="powersave",
                    cpu_boost=False,
                    gpu_mode="powersave",
                    disk_power_save=True,
                    wifi_power_save=True,
                    screen_brightness=50,
                    usb_autosuspend=True,
                    pcie_aspm="powersave"
                ),
                "emergency": PowerProfile(
                    name="emergency",
                    description="Emergency power saving",
                    cpu_governor="powersave",
                    cpu_boost=False,
                    gpu_mode="powersave",
                    disk_power_save=True,
                    wifi_power_save=True,
                    screen_brightness=30,
                    usb_autosuspend=True,
                    pcie_aspm="powersave"
                )
            }
            
            # Load custom profiles if they exist
            custom_profiles = self.config_dir / "profiles.json"
            if custom_profiles.exists():
                with open(custom_profiles) as f:
                    custom = json.load(f)
                    for name, data in custom.items():
                        profiles[name] = PowerProfile(**data)
            
            return profiles
            
        except Exception as e:
            logging.error(f"Error loading power profiles: {e}")
            return {}

    def run(self):
        """Main power management loop"""
        while True:
            try:
                self._update_power_state()
                self._select_appropriate_profile()
                self._apply_current_profile()
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error in power management loop: {e}")
                time.sleep(10)

    def _update_power_state(self):
        """Update current power state (AC/battery, battery level)"""
        try:
            # Check AC status
            ac_online = Path("/sys/class/power_supply/AC/online")
            if ac_online.exists():
                with open(ac_online) as f:
                    self.on_battery = f.read().strip() == "0"
            
            # Get battery level
            battery = Path("/sys/class/power_supply/BAT0/capacity")
            if battery.exists():
                with open(battery) as f:
                    self.battery_level = int(f.read().strip())
            
            # Update state file for other services
            state = {
                "on_battery": self.on_battery,
                "battery_level": self.battery_level,
                "timestamp": time.time()
            }
            with open(self.config_dir / "power_state.json", 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error updating power state: {e}")

    def _select_appropriate_profile(self):
        """Select the most appropriate power profile based on current state"""
        try:
            if not self.on_battery:
                # On AC power
                self.current_profile = self.profiles["balanced"]
            else:
                # On battery
                if self.battery_level <= 10:
                    self.current_profile = self.profiles["emergency"]
                elif self.battery_level <= 20:
                    self.current_profile = self.profiles["powersave"]
                else:
                    self.current_profile = self.profiles["balanced"]
            
            logging.info(f"Selected power profile: {self.current_profile.name}")
            
        except Exception as e:
            logging.error(f"Error selecting power profile: {e}")

    def _apply_current_profile(self):
        """Apply the current power profile settings"""
        if not self.current_profile:
            return
            
        try:
            self._apply_cpu_settings()
            self._apply_gpu_settings()
            self._apply_disk_settings()
            self._apply_wifi_settings()
            self._apply_screen_settings()
            self._apply_usb_settings()
            self._apply_pcie_settings()
            
        except Exception as e:
            logging.error(f"Error applying power profile: {e}")

    def _apply_cpu_settings(self):
        """Apply CPU power management settings"""
        try:
            # Set CPU governor
            for cpu in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
                governor_file = cpu / "cpufreq/scaling_governor"
                if governor_file.exists():
                    with open(governor_file, 'w') as f:
                        f.write(self.current_profile.cpu_governor)
            
            # Set CPU boost
            boost_file = Path("/sys/devices/system/cpu/cpufreq/boost")
            if boost_file.exists():
                with open(boost_file, 'w') as f:
                    f.write("1" if self.current_profile.cpu_boost else "0")
            
            # Set energy performance preference
            for cpu in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
                epp_file = cpu / "cpufreq/energy_performance_preference"
                if epp_file.exists():
                    with open(epp_file, 'w') as f:
                        if self.current_profile.name == "performance":
                            f.write("performance")
                        elif self.current_profile.name == "powersave":
                            f.write("power")
                        else:
                            f.write("balance_performance")
                            
        except Exception as e:
            logging.error(f"Error applying CPU settings: {e}")

    def _apply_gpu_settings(self):
        """Apply GPU power management settings"""
        try:
            # NVIDIA GPU
            try:
                subprocess.run([
                    "nvidia-settings",
                    "-a", f"[gpu:0]/GpuPowerMizerMode={self._get_nvidia_power_mode()}"
                ])
            except Exception:
                pass
            
            # AMD GPU
            try:
                for card in Path("/sys/class/drm").glob("card[0-9]"):
                    power_method = card / "device/power_method"
                    power_profile = card / "device/power_profile"
                    
                    if power_method.exists() and power_profile.exists():
                        with open(power_method, 'w') as f:
                            f.write("profile")
                        with open(power_profile, 'w') as f:
                            f.write(self._get_amd_power_profile())
            except Exception:
                pass
            
            # Intel GPU
            try:
                for gpu in Path("/sys/class/powercap/intel-rapl").glob("intel-rapl:*"):
                    constraint = gpu / "constraint_0_power_limit_uw"
                    if constraint.exists():
                        with open(constraint, 'w') as f:
                            limit = self._get_intel_power_limit()
                            f.write(str(limit))
            except Exception:
                pass
                
        except Exception as e:
            logging.error(f"Error applying GPU settings: {e}")

    def _apply_disk_settings(self):
        """Apply disk power management settings"""
        try:
            if self.current_profile.disk_power_save:
                # Enable aggressive power saving
                subprocess.run([
                    "hdparm", "-B", "128",
                    *Path("/dev").glob("sd[a-z]")
                ])
                
                # Set SATA power management
                for port in Path("/sys/class/scsi_host").glob("host*"):
                    link_pm = port / "link_power_management_policy"
                    if link_pm.exists():
                        with open(link_pm, 'w') as f:
                            f.write("min_power")
            else:
                # Disable power saving for performance
                subprocess.run([
                    "hdparm", "-B", "254",
                    *Path("/dev").glob("sd[a-z]")
                ])
                
                # Set SATA performance mode
                for port in Path("/sys/class/scsi_host").glob("host*"):
                    link_pm = port / "link_power_management_policy"
                    if link_pm.exists():
                        with open(link_pm, 'w') as f:
                            f.write("max_performance")
                            
        except Exception as e:
            logging.error(f"Error applying disk settings: {e}")

    def _apply_wifi_settings(self):
        """Apply WiFi power management settings"""
        try:
            power_save = "on" if self.current_profile.wifi_power_save else "off"
            
            for device in subprocess.check_output(["iwconfig"]).decode().split("\n"):
                if "IEEE" in device:
                    interface = device.split()[0]
                    subprocess.run([
                        "iwconfig", interface,
                        "power", power_save
                    ])
                    
        except Exception as e:
            logging.error(f"Error applying WiFi settings: {e}")

    def _apply_screen_settings(self):
        """Apply screen brightness settings"""
        try:
            # Set brightness for all displays
            for backlight in Path("/sys/class/backlight").glob("*"):
                max_brightness = int((backlight / "max_brightness").read_text())
                target_brightness = int(
                    (self.current_profile.screen_brightness / 100) * max_brightness
                )
                
                with open(backlight / "brightness", 'w') as f:
                    f.write(str(target_brightness))
                    
        except Exception as e:
            logging.error(f"Error applying screen settings: {e}")

    def _apply_usb_settings(self):
        """Apply USB power management settings"""
        try:
            for device in Path("/sys/bus/usb/devices").glob("*"):
                power_control = device / "power/control"
                if power_control.exists():
                    with open(power_control, 'w') as f:
                        if self.current_profile.usb_autosuspend:
                            f.write("auto")
                        else:
                            f.write("on")
                            
        except Exception as e:
            logging.error(f"Error applying USB settings: {e}")

    def _apply_pcie_settings(self):
        """Apply PCIe ASPM settings"""
        try:
            with open("/sys/module/pcie_aspm/parameters/policy", 'w') as f:
                f.write(self.current_profile.pcie_aspm)
                
        except Exception as e:
            logging.error(f"Error applying PCIe settings: {e}")

    def _get_nvidia_power_mode(self) -> int:
        """Get NVIDIA GPU power mode based on current profile"""
        if self.current_profile.name == "performance":
            return 1  # Prefer maximum performance
        elif self.current_profile.name == "powersave":
            return 0  # Prefer minimum power
        else:
            return 2  # Auto

    def _get_amd_power_profile(self) -> str:
        """Get AMD GPU power profile based on current profile"""
        if self.current_profile.name == "performance":
            return "high"
        elif self.current_profile.name == "powersave":
            return "low"
        else:
            return "auto"

    def _get_intel_power_limit(self) -> int:
        """Get Intel GPU power limit based on current profile"""
        if self.current_profile.name == "performance":
            return 15000000  # 15W
        elif self.current_profile.name == "powersave":
            return 5000000   # 5W
        else:
            return 10000000  # 10W

if __name__ == "__main__":
    manager = PowerManager()
    manager.run()