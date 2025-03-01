#!/usr/bin/python3
import os
import psutil
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

class SystemDiagnostics:
    def __init__(self):
        self.log_dir = "/var/log/tunix"
        self.config_dir = "/etc/tunix/diagnostics"
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        logging.basicConfig(
            filename=f"{self.log_dir}/diagnostics.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def get_thermal_info(self) -> Dict[str, float]:
        """Get thermal information from all available sensors"""
        thermal_info = {}
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                for entry in entries:
                    thermal_info[f"{name}_{entry.label or 'unknown'}"] = entry.current
        except Exception as e:
            logging.error(f"Error reading thermal sensors: {e}")
        return thermal_info

    def get_power_metrics(self) -> Dict[str, float]:
        """Get power consumption metrics"""
        metrics = {}
        try:
            battery = psutil.sensors_battery()
            if battery:
                metrics["battery_percent"] = battery.percent
                metrics["power_plugged"] = battery.power_plugged
                metrics["time_left"] = battery.secsleft if battery.secsleft != -1 else None
        except Exception as e:
            logging.error(f"Error reading power metrics: {e}")
        return metrics

    def check_thermal_throttling(self) -> Dict[str, bool]:
        """Check if any components are thermal throttling"""
        throttling = {
            "cpu_throttled": False,
            "gpu_throttled": False
        }
        
        # Check CPU throttling through frequency monitoring
        try:
            cpu_freqs = psutil.cpu_freq(percpu=True)
            max_freq = max(freq.current for freq in cpu_freqs)
            rated_max = self._get_rated_cpu_freq()
            if rated_max and max_freq < (rated_max * 0.8):  # 20% threshold
                throttling["cpu_throttled"] = True
                logging.warning(f"CPU potentially throttling: current max {max_freq}MHz vs rated {rated_max}MHz")
        except Exception as e:
            logging.error(f"Error checking CPU throttling: {e}")

        return throttling

    def _get_rated_cpu_freq(self) -> Optional[float]:
        """Get the rated maximum CPU frequency"""
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        # Extract frequency from CPU model name if available
                        return float(line.split("@")[1].strip().split("GHz")[0]) * 1000
        except Exception as e:
            logging.error(f"Error reading CPU info: {e}")
        return None

    def generate_diagnostic_report(self) -> Dict:
        """Generate a comprehensive system diagnostic report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "thermal": self.get_thermal_info(),
            "power": self.get_power_metrics(),
            "throttling": self.check_thermal_throttling(),
            "system_load": {
                "cpu_percent": psutil.cpu_percent(interval=1, percpu=True),
                "memory_percent": psutil.virtual_memory().percent,
                "swap_percent": psutil.swap_memory().percent
            }
        }

        # Save report
        report_path = f"{self.log_dir}/diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def suggest_optimizations(self, report: Dict) -> List[str]:
        """Suggest system optimizations based on diagnostic report"""
        suggestions = []
        
        # Thermal optimization suggestions
        if any(temp > 80 for temp in report["thermal"].values()):
            suggestions.append("High temperatures detected. Consider cleaning system fans and checking thermal paste.")
        
        # Power optimization suggestions
        if report["power"].get("battery_percent", 100) < 20 and not report["power"].get("power_plugged", True):
            suggestions.append("Battery level critical. Activating extreme power saving mode.")
        
        # Performance optimization suggestions
        if report["throttling"]["cpu_throttled"]:
            suggestions.append("CPU thermal throttling detected. Checking cooling system recommended.")
        
        if report["system_load"]["memory_percent"] > 90:
            suggestions.append("High memory usage detected. Consider increasing swap space or closing unused applications.")

        return suggestions

if __name__ == "__main__":
    diagnostics = SystemDiagnostics()
    report = diagnostics.generate_diagnostic_report()
    suggestions = diagnostics.suggest_optimizations(report)
    for suggestion in suggestions:
        logging.info(f"Optimization suggestion: {suggestion}")