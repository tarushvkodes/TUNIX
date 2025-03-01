#!/usr/bin/python3
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

class SystemConfig:
    def __init__(self):
        self.config_dir = Path("/etc/tunix/config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "system_config.json"
        
        logging.basicConfig(
            filename="/var/log/tunix/system_config.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Default configuration
        self.default_config = {
            "version": "1.0.0",
            "optimization": {
                "power_management": {
                    "enabled": True,
                    "default_profile": "balanced",
                    "battery_threshold": 20,
                    "thermal_threshold": 80
                },
                "thermal_control": {
                    "enabled": True,
                    "prediction_enabled": True,
                    "aggressive_cooling": False,
                    "target_temp": 65,
                    "warning_temp": 75,
                    "critical_temp": 85
                },
                "network": {
                    "enabled": True,
                    "auto_tune": True,
                    "bbr_enabled": True,
                    "buffer_autoscale": True
                },
                "memory": {
                    "swappiness": 60,
                    "cache_pressure": 100,
                    "compaction_proactiveness": 20,
                    "page_lock_unfairness": 5
                },
                "io": {
                    "scheduler": "auto",
                    "readahead": "auto",
                    "disk_idle_timeout": 60
                }
            },
            "monitoring": {
                "enabled": True,
                "interval": 1,
                "log_retention_days": 7,
                "metrics": {
                    "cpu": True,
                    "memory": True,
                    "disk": True,
                    "network": True,
                    "thermal": True,
                    "power": True
                },
                "alerts": {
                    "enabled": True,
                    "temperature_threshold": 80,
                    "memory_threshold": 90,
                    "disk_threshold": 90,
                    "cpu_threshold": 95
                }
            },
            "services": {
                "power_manager": True,
                "thermal_control": True,
                "network_optimizer": True,
                "system_monitor": True
            }
        }
        
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from file or create default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                return self._merge_with_defaults(config)
            else:
                return self.save_config(self.default_config)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return self.default_config.copy()

    def save_config(self, config: Dict) -> Dict:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return config
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            return self.default_config.copy()

    def _merge_with_defaults(self, config: Dict) -> Dict:
        """Merge loaded config with defaults to ensure all fields exist"""
        def merge_dict(source: Dict, target: Dict) -> Dict:
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    merge_dict(value, target[key])
            return target
        
        return merge_dict(self.default_config, config)

    def get_value(self, path: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation path"""
        try:
            value = self.config
            for key in path.split('.'):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set_value(self, path: str, value: Any) -> bool:
        """Set configuration value by dot-notation path"""
        try:
            keys = path.split('.')
            target = self.config
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            self.save_config(self.config)
            return True
        except Exception as e:
            logging.error(f"Error setting config value: {e}")
            return False

    def get_service_config(self, service_name: str) -> Optional[Dict]:
        """Get service-specific configuration"""
        try:
            service_file = self.config_dir / f"{service_name}.json"
            if service_file.exists():
                with open(service_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading service config: {e}")
        return None

    def save_service_config(self, service_name: str, config: Dict) -> bool:
        """Save service-specific configuration"""
        try:
            service_file = self.config_dir / f"{service_name}.json"
            with open(service_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error saving service config: {e}")
            return False

    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled in the configuration"""
        return self.get_value(f"services.{service_name}", False)

    def enable_service(self, service_name: str) -> bool:
        """Enable a service in the configuration"""
        return self.set_value(f"services.{service_name}", True)

    def disable_service(self, service_name: str) -> bool:
        """Disable a service in the configuration"""
        return self.set_value(f"services.{service_name}", False)

    def get_optimization_config(self) -> Dict:
        """Get complete optimization configuration"""
        return self.get_value("optimization", {})

    def get_monitoring_config(self) -> Dict:
        """Get complete monitoring configuration"""
        return self.get_value("monitoring", {})

    def update_optimization_config(self, config: Dict) -> bool:
        """Update optimization configuration"""
        try:
            current = self.get_optimization_config()
            current.update(config)
            return self.set_value("optimization", current)
        except Exception as e:
            logging.error(f"Error updating optimization config: {e}")
            return False

    def update_monitoring_config(self, config: Dict) -> bool:
        """Update monitoring configuration"""
        try:
            current = self.get_monitoring_config()
            current.update(config)
            return self.set_value("monitoring", current)
        except Exception as e:
            logging.error(f"Error updating monitoring config: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    config = SystemConfig()
    
    # Load and verify configuration
    print("Current configuration:")
    print(json.dumps(config.config, indent=2))
    
    # Example: Update thermal control settings
    thermal_config = {
        "target_temp": 70,
        "warning_temp": 80,
        "critical_temp": 90
    }
    if config.set_value("optimization.thermal_control", thermal_config):
        print("\nThermal configuration updated successfully")