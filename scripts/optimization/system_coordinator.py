#!/usr/bin/python3
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from system_config import SystemConfig

class ServiceStatus:
    def __init__(self, name: str, active: bool, enabled: bool, status: str):
        self.name = name
        self.active = active
        self.enabled = enabled
        self.status = status

class SystemCoordinator:
    def __init__(self):
        self.config = SystemConfig()
        self.services = [
            "tunix-system-control",
            "tunix-power",
            "tunix-thermal",
            "tunix-network",
            "tunix-network-routing",
            "tunix-monitor",
            "tunix-performance",
            "tunix-optimize"
        ]
        
        logging.basicConfig(
            filename="/var/log/tunix/system_coordinator.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def run(self):
        """Main coordination loop"""
        while True:
            try:
                self.ensure_services_running()
                self.coordinate_optimization()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logging.error(f"Error in coordination loop: {e}")
                time.sleep(10)  # Wait before retry on error

    def check_service_status(self, service: str) -> ServiceStatus:
        """Check status of a systemd service"""
        try:
            active_result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True
            )
            active = active_result.returncode == 0
            
            enabled_result = subprocess.run(
                ["systemctl", "is-enabled", service],
                capture_output=True,
                text=True
            )
            enabled = enabled_result.returncode == 0
            
            status_result = subprocess.run(
                ["systemctl", "status", service],
                capture_output=True,
                text=True
            )
            status = status_result.stdout
            
            return ServiceStatus(service, active, enabled, status)
            
        except Exception as e:
            logging.error(f"Error checking service {service}: {e}")
            return ServiceStatus(service, False, False, f"Error: {str(e)}")

    def ensure_services_running(self):
        """Ensure all TUNIX services are running properly"""
        for service in self.services:
            try:
                if self.config.is_service_enabled(service):
                    status = self.check_service_status(service)
                    
                    if not status.enabled:
                        subprocess.run(["systemctl", "enable", service])
                        
                    if not status.active:
                        subprocess.run(["systemctl", "start", service])
                        logging.info(f"Started service: {service}")
                        
            except Exception as e:
                logging.error(f"Error managing service {service}: {e}")

    def coordinate_optimization(self):
        """Coordinate optimization activities between services"""
        try:
            # Load current system state
            hardware_profile = self._load_hardware_profile()
            performance_metrics = self._load_performance_metrics()
            power_state = self._get_power_state()
            
            # Determine optimal settings based on current state
            settings = self._determine_optimal_settings(
                hardware_profile,
                performance_metrics,
                power_state
            )
            
            # Apply coordinated optimizations
            self._apply_optimizations(settings)
            
        except Exception as e:
            logging.error(f"Error in optimization coordination: {e}")

    def _load_hardware_profile(self) -> Dict:
        """Load current hardware profile"""
        try:
            profile_path = Path("/etc/tunix/hardware/hardware_profile.json")
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading hardware profile: {e}")
        return {}

    def _load_performance_metrics(self) -> Dict:
        """Load current performance metrics"""
        try:
            metrics_path = Path("/var/log/tunix/performance_metrics.json")
            if metrics_path.exists():
                with open(metrics_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading performance metrics: {e}")
        return {}

    def _get_power_state(self) -> Dict:
        """Get current power state (AC/battery, battery level)"""
        try:
            power_state = {"on_battery": False, "battery_level": 100}
            
            # Check if system is on battery
            with open("/sys/class/power_supply/AC/online", "r") as f:
                power_state["on_battery"] = f.read().strip() == "0"
            
            # Get battery level if available
            battery_path = Path("/sys/class/power_supply/BAT0/capacity")
            if battery_path.exists():
                with open(battery_path, "r") as f:
                    power_state["battery_level"] = int(f.read().strip())
            
            return power_state
        except Exception as e:
            logging.error(f"Error getting power state: {e}")
            return {"on_battery": False, "battery_level": 100}

    def _determine_optimal_settings(self, 
                                 hardware_profile: Dict, 
                                 performance_metrics: Dict,
                                 power_state: Dict) -> Dict:
        """Determine optimal system settings based on current state"""
        settings = {
            "power": self._determine_power_settings(hardware_profile, power_state),
            "thermal": self._determine_thermal_settings(hardware_profile, performance_metrics),
            "network": self._determine_network_settings(performance_metrics),
            "memory": self._determine_memory_settings(performance_metrics)
        }
        return settings

    def _determine_power_settings(self, hardware_profile: Dict, power_state: Dict) -> Dict:
        """Determine optimal power settings"""
        settings = {
            "cpu_governor": "powersave" if power_state["on_battery"] else "performance",
            "disk_power_management": True if power_state["on_battery"] else False,
            "usb_autosuspend": True if power_state["on_battery"] else False,
            "wifi_power_save": True if power_state["on_battery"] else False
        }
        
        # Adjust for battery level
        if power_state["on_battery"] and power_state["battery_level"] < 20:
            settings.update({
                "screen_brightness": 50,
                "cpu_boost": False,
                "aggressive_power_save": True
            })
        
        return settings

    def _determine_thermal_settings(self, hardware_profile: Dict, performance_metrics: Dict) -> Dict:
        """Determine optimal thermal settings"""
        settings = {
            "fan_mode": "auto",
            "throttling_threshold": 80
        }
        
        # Check if system is running hot
        if "temperature" in performance_metrics:
            current_temp = performance_metrics["temperature"].get("cpu", 0)
            if current_temp > 75:
                settings.update({
                    "fan_mode": "performance",
                    "throttling_threshold": 75
                })
        
        return settings

    def _determine_network_settings(self, performance_metrics: Dict) -> Dict:
        """Determine optimal network settings"""
        settings = {
            "tcp_congestion_control": "bbr",
            "wifi_power_management": "on",
            "buffer_size": "auto"
        }
        
        # Adjust based on network usage
        if "network" in performance_metrics:
            if performance_metrics["network"].get("bandwidth_usage", 0) > 80:
                settings["buffer_size"] = "large"
        
        return settings

    def _determine_memory_settings(self, performance_metrics: Dict) -> Dict:
        """Determine optimal memory settings"""
        settings = {
            "swappiness": 60,
            "vfs_cache_pressure": 100,
            "dirty_ratio": 20,
            "dirty_background_ratio": 10
        }
        
        # Adjust based on memory usage
        if "memory" in performance_metrics:
            mem_used_percent = performance_metrics["memory"].get("used_percent", 0)
            if mem_used_percent > 80:
                settings.update({
                    "swappiness": 80,
                    "vfs_cache_pressure": 150
                })
        
        return settings

    def _apply_optimizations(self, settings: Dict):
        """Apply coordinated optimization settings"""
        try:
            self._apply_power_settings(settings["power"])
            self._apply_thermal_settings(settings["thermal"])
            self._apply_network_settings(settings["network"])
            self._apply_memory_settings(settings["memory"])
        except Exception as e:
            logging.error(f"Error applying optimizations: {e}")

    def _apply_power_settings(self, settings: Dict):
        """Apply power management settings"""
        try:
            # Set CPU governor
            for cpu in range(subprocess.check_output(["nproc"]).decode().strip()):
                subprocess.run([
                    "cpupower", "-c", str(cpu), 
                    "frequency-set", "-g", settings["cpu_governor"]
                ])
            
            # Set disk power management
            if settings["disk_power_management"]:
                subprocess.run(["hdparm", "-B", "128", "/dev/sda"])
            
            # Set USB autosuspend
            if settings["usb_autosuspend"]:
                for device in Path("/sys/bus/usb/devices").glob("*"):
                    if (device / "power/control").exists():
                        with open(device / "power/control", "w") as f:
                            f.write("auto")
        except Exception as e:
            logging.error(f"Error applying power settings: {e}")

    def _apply_thermal_settings(self, settings: Dict):
        """Apply thermal control settings"""
        try:
            # Configure thermal settings through thermald if available
            subprocess.run([
                "thermald", "--set-adaptive", 
                f"--throttling-temp={settings['throttling_threshold']}"
            ])
            
            # Set fan mode if supported
            if Path("/sys/class/thermal/cooling_device0/cur_state").exists():
                with open("/sys/class/thermal/cooling_device0/cur_state", "w") as f:
                    f.write("0" if settings["fan_mode"] == "auto" else "255")
        except Exception as e:
            logging.error(f"Error applying thermal settings: {e}")

    def _apply_network_settings(self, settings: Dict):
        """Apply network settings"""
        try:
            # Set TCP congestion control
            subprocess.run([
                "sysctl", "-w", 
                f"net.ipv4.tcp_congestion_control={settings['tcp_congestion_control']}"
            ])
            
            # Configure WiFi power management
            for device in subprocess.check_output(["iwconfig"]).decode().split("\n"):
                if "IEEE" in device:
                    interface = device.split()[0]
                    subprocess.run([
                        "iwconfig", interface, 
                        "power", settings["wifi_power_management"]
                    ])
        except Exception as e:
            logging.error(f"Error applying network settings: {e}")

    def _apply_memory_settings(self, settings: Dict):
        """Apply memory management settings"""
        try:
            subprocess.run([
                "sysctl", "-w",
                f"vm.swappiness={settings['swappiness']}",
                f"vm.vfs_cache_pressure={settings['vfs_cache_pressure']}",
                f"vm.dirty_ratio={settings['dirty_ratio']}",
                f"vm.dirty_background_ratio={settings['dirty_background_ratio']}"
            ])
        except Exception as e:
            logging.error(f"Error applying memory settings: {e}")

if __name__ == "__main__":
    coordinator = SystemCoordinator()
    coordinator.run()