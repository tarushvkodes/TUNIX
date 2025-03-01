#!/usr/bin/python3
import json
import logging
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from collections import deque

class ThermalController:
    def __init__(self):
        self.config_dir = Path("/etc/tunix/thermal")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_length = 300  # 5 minutes of history
        self.temp_history = deque(maxlen=self.history_length)
        self.load_history = deque(maxlen=self.history_length)
        
        self.prediction_window = 60  # Predict 1 minute ahead
        
        logging.basicConfig(
            filename="/var/log/tunix/thermal_control.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Load hardware-specific thermal profiles
        self.thermal_profiles = self._load_thermal_profiles()

    def _load_thermal_profiles(self) -> Dict:
        """Load hardware-specific thermal profiles"""
        try:
            profile_path = self.config_dir / "thermal_profiles.json"
            if profile_path.exists():
                with open(profile_path) as f:
                    return json.load(f)
            return self._create_default_profiles()
        except Exception as e:
            logging.error(f"Error loading thermal profiles: {e}")
            return self._create_default_profiles()

    def _create_default_profiles(self) -> Dict:
        """Create default thermal profiles"""
        return {
            "default": {
                "target_temp": 70,
                "warning_temp": 80,
                "critical_temp": 90,
                "fan_curve": [
                    {"temp": 40, "speed": 0},
                    {"temp": 50, "speed": 30},
                    {"temp": 60, "speed": 50},
                    {"temp": 70, "speed": 70},
                    {"temp": 80, "speed": 100}
                ]
            },
            "laptop": {
                "target_temp": 65,
                "warning_temp": 75,
                "critical_temp": 85,
                "fan_curve": [
                    {"temp": 40, "speed": 20},
                    {"temp": 50, "speed": 40},
                    {"temp": 60, "speed": 60},
                    {"temp": 70, "speed": 80},
                    {"temp": 75, "speed": 100}
                ]
            }
        }

    def run(self):
        """Main thermal control loop"""
        while True:
            try:
                current_temps = self._get_temperatures()
                current_load = self._get_system_load()
                
                self.temp_history.append(current_temps)
                self.load_history.append(current_load)
                
                if len(self.temp_history) >= 60:  # At least 1 minute of data
                    predicted_temps = self._predict_temperatures()
                    self._adjust_cooling(current_temps, predicted_temps)
                else:
                    self._adjust_cooling(current_temps, None)
                
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error in thermal control loop: {e}")
                time.sleep(5)

    def _get_temperatures(self) -> Dict[str, float]:
        """Get current temperatures from all available sensors"""
        temps = {}
        try:
            # CPU temperature
            for cpu in Path("/sys/class/thermal/thermal_zone*").glob("*"):
                if (cpu / "type").exists() and (cpu / "temp").exists():
                    with open(cpu / "type") as f:
                        sensor_type = f.read().strip()
                    with open(cpu / "temp") as f:
                        temp = int(f.read().strip()) / 1000.0  # Convert from millidegrees
                    temps[sensor_type] = temp
            
            # GPU temperature (NVIDIA)
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    temps["gpu"] = float(result.stdout.strip())
            except Exception:
                pass
            
            # GPU temperature (AMD)
            amd_temp = Path("/sys/class/drm/card0/device/hwmon/hwmon0/temp1_input")
            if amd_temp.exists():
                with open(amd_temp) as f:
                    temps["gpu"] = int(f.read().strip()) / 1000.0
            
        except Exception as e:
            logging.error(f"Error reading temperatures: {e}")
        
        return temps

    def _get_system_load(self) -> Dict[str, float]:
        """Get current system load metrics"""
        try:
            with open("/proc/stat") as f:
                cpu = f.readline().split()[1:]
            
            total = sum(float(x) for x in cpu)
            idle = float(cpu[3])
            
            load = {
                "cpu_usage": 100 * (1 - idle/total)
            }
            
            # Get GPU utilization if available
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    load["gpu_usage"] = float(result.stdout.strip())
            except Exception:
                pass
            
            return load
            
        except Exception as e:
            logging.error(f"Error getting system load: {e}")
            return {}

    def _predict_temperatures(self) -> Dict[str, float]:
        """Predict future temperatures using recent history"""
        predictions = {}
        try:
            # Convert history to numpy arrays for analysis
            for sensor in self.temp_history[-1].keys():
                temps = [h.get(sensor, 0) for h in self.temp_history]
                loads = [h.get("cpu_usage", 0) for h in self.load_history]
                
                if len(temps) >= 60:  # Need at least 1 minute of data
                    # Use polynomial regression for prediction
                    x = np.arange(len(temps))
                    z = np.polyfit(x, temps, 2)
                    p = np.poly1d(z)
                    
                    # Predict temperature in 1 minute
                    future_x = len(temps) + 60
                    predicted_temp = p(future_x)
                    
                    # Adjust prediction based on current load trend
                    load_trend = np.mean(loads[-10:]) - np.mean(loads[-60:-50])
                    predicted_temp += load_trend * 0.1
                    
                    predictions[sensor] = max(20, min(100, predicted_temp))
            
        except Exception as e:
            logging.error(f"Error predicting temperatures: {e}")
        
        return predictions

    def _adjust_cooling(self, current_temps: Dict[str, float], predicted_temps: Optional[Dict[str, float]]):
        """Adjust cooling based on current and predicted temperatures"""
        try:
            # Determine which thermal profile to use
            profile = self._get_current_profile()
            
            # Get the highest current temperature
            max_current_temp = max(current_temps.values()) if current_temps else 0
            
            # Get the highest predicted temperature
            max_predicted_temp = max(predicted_temps.values()) if predicted_temps else 0
            
            # Determine target fan speed
            target_speed = self._calculate_fan_speed(
                max_current_temp,
                max_predicted_temp,
                profile
            )
            
            # Apply fan speed
            self._set_fan_speed(target_speed)
            
            # Apply additional cooling measures if needed
            if max_current_temp >= profile["warning_temp"]:
                self._apply_emergency_cooling(max_current_temp, profile)
            
        except Exception as e:
            logging.error(f"Error adjusting cooling: {e}")

    def _get_current_profile(self) -> Dict:
        """Determine which thermal profile to use"""
        try:
            # Check if we're on a laptop
            if Path("/sys/class/power_supply/BAT0").exists():
                return self.thermal_profiles.get("laptop", self.thermal_profiles["default"])
            return self.thermal_profiles["default"]
        except Exception:
            return self.thermal_profiles["default"]

    def _calculate_fan_speed(self, current_temp: float, predicted_temp: float, profile: Dict) -> int:
        """Calculate optimal fan speed percentage"""
        try:
            # Get the base fan speed from the fan curve
            base_speed = 0
            for point in profile["fan_curve"]:
                if current_temp <= point["temp"]:
                    base_speed = point["speed"]
                    break
            if current_temp > profile["fan_curve"][-1]["temp"]:
                base_speed = 100
            
            # Adjust speed based on prediction
            if predicted_temp:
                temp_delta = predicted_temp - current_temp
                if temp_delta > 0:
                    # Increase fan speed preemptively
                    base_speed = min(100, base_speed + (temp_delta * 2))
            
            return int(base_speed)
            
        except Exception as e:
            logging.error(f"Error calculating fan speed: {e}")
            return 50  # Safe default

    def _set_fan_speed(self, speed: int):
        """Set fan speed"""
        try:
            # Try standard PWM control
            for fan in Path("/sys/class/hwmon").glob("*/pwm[0-9]"):
                try:
                    # Convert percentage to PWM value (0-255)
                    pwm_value = int((speed / 100) * 255)
                    with open(fan, 'w') as f:
                        f.write(str(pwm_value))
                except Exception:
                    continue
            
            # Try ThinkPad-specific fan control
            thinkpad_fan = Path("/proc/acpi/ibm/fan")
            if thinkpad_fan.exists():
                with open(thinkpad_fan, 'w') as f:
                    if speed >= 100:
                        f.write("level disengaged")
                    else:
                        # Convert percentage to level (0-7)
                        level = min(7, int((speed / 100) * 7))
                        f.write(f"level {level}")
                        
        except Exception as e:
            logging.error(f"Error setting fan speed: {e}")

    def _apply_emergency_cooling(self, current_temp: float, profile: Dict):
        """Apply emergency cooling measures"""
        try:
            if current_temp >= profile["critical_temp"]:
                # Aggressive CPU throttling
                self._set_cpu_frequency("powersave")
                self._reduce_cpu_power_limit()
                
                # Log critical temperature event
                logging.critical(
                    f"Critical temperature reached: {current_temp}°C. "
                    "Applying emergency cooling measures."
                )
                
            elif current_temp >= profile["warning_temp"]:
                # Moderate CPU throttling
                self._set_cpu_frequency("conservative")
                
                # Log warning temperature event
                logging.warning(
                    f"High temperature warning: {current_temp}°C. "
                    "Applying preventive measures."
                )
                
        except Exception as e:
            logging.error(f"Error applying emergency cooling: {e}")

    def _set_cpu_frequency(self, governor: str):
        """Set CPU frequency scaling governor"""
        try:
            for cpu in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
                governor_file = cpu / "cpufreq/scaling_governor"
                if governor_file.exists():
                    with open(governor_file, 'w') as f:
                        f.write(governor)
        except Exception as e:
            logging.error(f"Error setting CPU frequency governor: {e}")

    def _reduce_cpu_power_limit(self):
        """Reduce CPU power limit for emergency thermal control"""
        try:
            # Try Intel RAPL interface
            for domain in Path("/sys/class/powercap/intel-rapl").glob("intel-rapl:*"):
                constraint_file = domain / "constraint_0_power_limit_uw"
                if constraint_file.exists():
                    # Reduce to 50% of normal power limit
                    with open(domain / "constraint_0_max_power_uw") as f:
                        max_power = int(f.read().strip())
                    with open(constraint_file, 'w') as f:
                        f.write(str(max_power // 2))
                        
            # Try AMD k10temp interface
            # Note: AMD power limit adjustment would go here
            
        except Exception as e:
            logging.error(f"Error reducing CPU power limit: {e}")

if __name__ == "__main__":
    controller = ThermalController()
    controller.run()