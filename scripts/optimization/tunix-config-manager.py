#!/usr/bin/python3
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class ConfigManager:
    def __init__(self):
        self.config_root = Path("/etc/tunix")
        self.backup_dir = Path("/var/backups/tunix")
        self.config_root.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename="/var/log/tunix/config_manager.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.default_config = {
            "version": "1.0.0",
            "last_update": "",
            "components": {
                "system_monitor": {
                    "enabled": True,
                    "update_interval": 1,
                    "metrics_retention_days": 7
                },
                "performance_analyzer": {
                    "enabled": True,
                    "analysis_interval": 300,
                    "anomaly_detection_sensitivity": 0.1
                },
                "thermal_control": {
                    "enabled": True,
                    "prediction_enabled": True,
                    "fan_curve": "balanced",
                    "critical_temp": 90
                },
                "power_manager": {
                    "enabled": True,
                    "default_profile": "balanced",
                    "battery_threshold": 20
                },
                "network_optimizer": {
                    "enabled": True,
                    "auto_tune": True,
                    "bbr_enabled": True
                }
            },
            "optimization": {
                "cpu": {
                    "frequency_scaling": "auto",
                    "energy_preference": "balance_performance",
                    "boost_enabled": True
                },
                "memory": {
                    "swappiness": 60,
                    "vfs_cache_pressure": 100,
                    "dirty_ratio": 20
                },
                "disk": {
                    "scheduler": "auto",
                    "read_ahead": "auto",
                    "power_saving": True
                },
                "network": {
                    "congestion_control": "bbr",
                    "wifi_power_save": True,
                    "buffer_size": "auto"
                }
            },
            "scheduling": {
                "daily_optimization": "03:00",
                "weekly_maintenance": "Sun 04:00",
                "backup_retention_days": 30
            }
        }

    def load_config(self, component: Optional[str] = None) -> Dict:
        """Load configuration, optionally for a specific component"""
        try:
            config_path = self.config_root / "config.json"
            
            if not config_path.exists():
                return self._create_default_config()
            
            with open(config_path) as f:
                config = json.load(f)
            
            # Return specific component config if requested
            if component:
                return config.get("components", {}).get(component, {})
            
            return config
            
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return self._create_default_config()

    def save_config(self, config: Dict, backup: bool = True) -> bool:
        """Save configuration with optional backup"""
        try:
            if backup:
                self._backup_config()
            
            config["last_update"] = datetime.now().isoformat()
            
            with open(self.config_root / "config.json", 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
            
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            return False

    def update_component_config(self, component: str, settings: Dict) -> bool:
        """Update configuration for a specific component"""
        try:
            config = self.load_config()
            
            if "components" not in config:
                config["components"] = {}
            
            if component not in config["components"]:
                config["components"][component] = {}
            
            config["components"][component].update(settings)
            
            return self.save_config(config)
            
        except Exception as e:
            logging.error(f"Error updating component config: {e}")
            return False

    def validate_config(self, config: Dict) -> bool:
        """Validate configuration structure and values"""
        try:
            # Check required top-level keys
            required_keys = ["version", "components", "optimization", "scheduling"]
            if not all(key in config for key in required_keys):
                return False
            
            # Validate component configurations
            for component, settings in config["components"].items():
                if not self._validate_component_settings(component, settings):
                    return False
            
            # Validate optimization settings
            if not self._validate_optimization_settings(config["optimization"]):
                return False
            
            # Validate scheduling
            if not self._validate_scheduling(config["scheduling"]):
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating config: {e}")
            return False

    def _validate_component_settings(self, component: str, settings: Dict) -> bool:
        """Validate settings for a specific component"""
        try:
            # All components must have 'enabled' flag
            if "enabled" not in settings:
                return False
            
            # Component-specific validation
            if component == "system_monitor":
                return (
                    isinstance(settings.get("update_interval"), (int, float)) and
                    isinstance(settings.get("metrics_retention_days"), int)
                )
            elif component == "performance_analyzer":
                return (
                    isinstance(settings.get("analysis_interval"), int) and
                    isinstance(settings.get("anomaly_detection_sensitivity"), float)
                )
            elif component == "thermal_control":
                return (
                    isinstance(settings.get("prediction_enabled"), bool) and
                    isinstance(settings.get("critical_temp"), (int, float))
                )
            elif component == "power_manager":
                return (
                    isinstance(settings.get("battery_threshold"), int) and
                    settings.get("default_profile") in ["performance", "balanced", "powersave"]
                )
            
            return True
            
        except Exception:
            return False

    def _validate_optimization_settings(self, settings: Dict) -> bool:
        """Validate optimization settings"""
        try:
            required_sections = ["cpu", "memory", "disk", "network"]
            if not all(section in settings for section in required_sections):
                return False
            
            # Validate CPU settings
            cpu = settings["cpu"]
            if not (
                cpu["frequency_scaling"] in ["auto", "performance", "powersave"] and
                isinstance(cpu["boost_enabled"], bool)
            ):
                return False
            
            # Validate memory settings
            memory = settings["memory"]
            if not all(
                isinstance(memory[key], int)
                for key in ["swappiness", "vfs_cache_pressure", "dirty_ratio"]
            ):
                return False
            
            return True
            
        except Exception:
            return False

    def _validate_scheduling(self, settings: Dict) -> bool:
        """Validate scheduling settings"""
        try:
            # Validate time formats
            time_format = "%H:%M"
            datetime.strptime(settings["daily_optimization"], time_format)
            
            # Validate weekly maintenance format (Day HH:MM)
            day, time = settings["weekly_maintenance"].split()
            if day not in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                return False
            datetime.strptime(time, time_format)
            
            # Validate retention days
            return isinstance(settings["backup_retention_days"], int)
            
        except Exception:
            return False

    def _create_default_config(self) -> Dict:
        """Create and save default configuration"""
        try:
            self.save_config(self.default_config, backup=False)
            return self.default_config
        except Exception as e:
            logging.error(f"Error creating default config: {e}")
            return {}

    def _backup_config(self):
        """Create a backup of the current configuration"""
        try:
            current_config = self.config_root / "config.json"
            if current_config.exists():
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_path = self.backup_dir / f"config-{timestamp}.json"
                shutil.copy2(current_config, backup_path)
                
                # Cleanup old backups
                self._cleanup_old_backups()
                
        except Exception as e:
            logging.error(f"Error backing up config: {e}")

    def _cleanup_old_backups(self):
        """Remove old backup files"""
        try:
            config = self.load_config()
            retention_days = config["scheduling"]["backup_retention_days"]
            cutoff = datetime.now().timestamp() - (retention_days * 86400)
            
            for backup in self.backup_dir.glob("config-*.json"):
                if backup.stat().st_mtime < cutoff:
                    backup.unlink()
                    
        except Exception as e:
            logging.error(f"Error cleaning up old backups: {e}")

    def export_config(self, path: Path) -> bool:
        """Export configuration to a file"""
        try:
            config = self.load_config()
            with open(path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error exporting config: {e}")
            return False

    def import_config(self, path: Path) -> bool:
        """Import configuration from a file"""
        try:
            with open(path) as f:
                config = json.load(f)
            
            if self.validate_config(config):
                return self.save_config(config)
            return False
            
        except Exception as e:
            logging.error(f"Error importing config: {e}")
            return False

if __name__ == "__main__":
    manager = ConfigManager()
    # Ensure default configuration exists
    manager.load_config()