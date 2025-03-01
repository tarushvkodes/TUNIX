#!/usr/bin/python3
import json
import logging
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from tunix_config_manager import ConfigManager

class UpdateManager:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.update_dir = Path("/var/lib/tunix/updates")
        self.backup_dir = Path("/var/backups/tunix")
        self.service_dir = Path("/etc/systemd/system")
        
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename="/var/log/tunix/update_manager.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.components = [
            "system_monitor",
            "performance_analyzer",
            "thermal_control",
            "power_manager",
            "network_optimizer",
            "system_coordinator"
        ]

    def check_updates(self) -> Dict[str, str]:
        """Check for available updates to TUNIX components"""
        updates = {}
        try:
            # In a real implementation, this would check a remote repository
            # For now, we'll just check local file versions
            for component in self.components:
                current_version = self._get_component_version(component)
                latest_version = self._get_latest_version(component)
                if latest_version and latest_version > current_version:
                    updates[component] = latest_version
            return updates
        except Exception as e:
            logging.error(f"Error checking updates: {e}")
            return {}

    def update_system(self, components: Optional[List[str]] = None) -> bool:
        """Update specified components or all if none specified"""
        try:
            if not components:
                components = self.components
            
            # Stop affected services
            self._stop_services(components)
            
            # Backup current system
            if not self._backup_system():
                raise Exception("System backup failed")
            
            # Update each component
            success = True
            for component in components:
                if not self._update_component(component):
                    success = False
                    logging.error(f"Failed to update {component}")
            
            # Update configuration version
            if success:
                self._update_config_version()
            
            # Restart services
            self._restart_services(components)
            
            return success
        except Exception as e:
            logging.error(f"Error during system update: {e}")
            self._restore_backup()
            return False

    def _get_component_version(self, component: str) -> str:
        """Get current version of a component"""
        try:
            version_file = Path(f"/usr/local/lib/tunix/{component}.version")
            if version_file.exists():
                return version_file.read_text().strip()
            return "0.0.0"
        except Exception:
            return "0.0.0"

    def _get_latest_version(self, component: str) -> Optional[str]:
        """Get latest available version of a component"""
        try:
            # In a real implementation, this would check a remote repository
            # For now, return a simulated version
            return "1.0.0"
        except Exception:
            return None

    def _stop_services(self, components: List[str]):
        """Stop services for affected components"""
        try:
            for component in components:
                service_name = f"tunix-{component.replace('_', '-')}.service"
                subprocess.run(["systemctl", "stop", service_name])
        except Exception as e:
            logging.error(f"Error stopping services: {e}")

    def _restart_services(self, components: List[str]):
        """Restart services for affected components"""
        try:
            # Reload systemd to pick up any service file changes
            subprocess.run(["systemctl", "daemon-reload"])
            
            for component in components:
                service_name = f"tunix-{component.replace('_', '-')}.service"
                subprocess.run(["systemctl", "restart", service_name])
        except Exception as e:
            logging.error(f"Error restarting services: {e}")

    def _backup_system(self) -> bool:
        """Create backup of current system state"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = self.backup_dir / f"system-{timestamp}"
            backup_path.mkdir(parents=True)
            
            # Backup configuration
            shutil.copytree(
                self.config_manager.config_root,
                backup_path / "config",
                dirs_exist_ok=True
            )
            
            # Backup component files
            shutil.copytree(
                "/usr/local/lib/tunix",
                backup_path / "lib",
                dirs_exist_ok=True
            )
            
            # Backup service files
            service_backup = backup_path / "services"
            service_backup.mkdir()
            for component in self.components:
                service_file = f"tunix-{component.replace('_', '-')}.service"
                if (self.service_dir / service_file).exists():
                    shutil.copy2(
                        self.service_dir / service_file,
                        service_backup / service_file
                    )
            
            return True
        except Exception as e:
            logging.error(f"Error creating backup: {e}")
            return False

    def _restore_backup(self) -> bool:
        """Restore system from latest backup"""
        try:
            # Find latest backup
            backups = sorted(self.backup_dir.glob("system-*"))
            if not backups:
                return False
            
            latest_backup = backups[-1]
            
            # Restore configuration
            shutil.rmtree(self.config_manager.config_root, ignore_errors=True)
            shutil.copytree(
                latest_backup / "config",
                self.config_manager.config_root,
                dirs_exist_ok=True
            )
            
            # Restore component files
            shutil.rmtree("/usr/local/lib/tunix", ignore_errors=True)
            shutil.copytree(
                latest_backup / "lib",
                "/usr/local/lib/tunix",
                dirs_exist_ok=True
            )
            
            # Restore service files
            for service_file in (latest_backup / "services").glob("*.service"):
                shutil.copy2(
                    service_file,
                    self.service_dir / service_file.name
                )
            
            return True
        except Exception as e:
            logging.error(f"Error restoring backup: {e}")
            return False

    def _update_component(self, component: str) -> bool:
        """Update a specific component"""
        try:
            # In a real implementation, this would download and verify new files
            # For now, we'll just update the version file
            version_file = Path(f"/usr/local/lib/tunix/{component}.version")
            version_file.write_text("1.0.0")
            
            return True
        except Exception as e:
            logging.error(f"Error updating component {component}: {e}")
            return False

    def _update_config_version(self):
        """Update configuration version after successful update"""
        try:
            config = self.config_manager.load_config()
            config["version"] = "1.0.0"
            config["last_update"] = datetime.now().isoformat()
            self.config_manager.save_config(config)
        except Exception as e:
            logging.error(f"Error updating config version: {e}")

    def verify_system_integrity(self) -> Tuple[bool, Dict[str, str]]:
        """Verify integrity of TUNIX components and configurations"""
        status = {}
        try:
            # Check component files
            for component in self.components:
                script_path = Path(f"/usr/local/lib/tunix/{component}.py")
                if not script_path.exists():
                    status[component] = "missing_script"
                    continue
                
                service_name = f"tunix-{component.replace('_', '-')}.service"
                service_path = self.service_dir / service_name
                if not service_path.exists():
                    status[component] = "missing_service"
                    continue
                
                # Check if service is running
                result = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip() != "active":
                    status[component] = "service_inactive"
                    continue
                
                status[component] = "ok"
            
            # Verify configuration
            if not self.config_manager.validate_config(self.config_manager.load_config()):
                status["configuration"] = "invalid"
            else:
                status["configuration"] = "ok"
            
            return all(s == "ok" for s in status.values()), status
            
        except Exception as e:
            logging.error(f"Error verifying system integrity: {e}")
            return False, {"error": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: tunix-update-manager.py [check|update|verify]")
        sys.exit(1)
    
    manager = UpdateManager()
    command = sys.argv[1]
    
    if command == "check":
        updates = manager.check_updates()
        if updates:
            print("Updates available for:")
            for component, version in updates.items():
                print(f"- {component}: {version}")
        else:
            print("No updates available")
            
    elif command == "update":
        components = sys.argv[2:] if len(sys.argv) > 2 else None
        if manager.update_system(components):
            print("Update completed successfully")
        else:
            print("Update failed, check logs for details")
            sys.exit(1)
            
    elif command == "verify":
        success, status = manager.verify_system_integrity()
        print("System integrity check:")
        for component, state in status.items():
            print(f"- {component}: {state}")
        if not success:
            sys.exit(1)
            
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()