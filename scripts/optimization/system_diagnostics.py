#!/usr/bin/python3

import os
import json
import logging
import subprocess
import datetime
from typing import Dict, List, Optional

class SystemDiagnostics:
    def __init__(self):
        self.log_dir = "/var/log/tunix"
        self.profile_file = "/etc/tunix/hardware_profile.json"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up logging
        logging.basicConfig(
            filename=f"{self.log_dir}/diagnostics.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("TUNIXDiagnostics")

    def run_diagnostics(self) -> Dict:
        """Run full system diagnostics and return results"""
        self.logger.info("Starting system diagnostics")
        
        results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "profile_status": self.check_profile_status(),
            "optimization_status": self.check_optimization_status(),
            "performance_metrics": self.collect_performance_metrics(),
            "error_log": self.check_error_logs(),
            "recommendations": []
        }
        
        # Generate recommendations based on findings
        results["recommendations"] = self.generate_recommendations(results)
        
        self.logger.info("Diagnostics completed")
        return results

    def check_profile_status(self) -> Dict:
        """Check if hardware profile is properly applied"""
        try:
            with open(self.profile_file, 'r') as f:
                profile = json.load(f)
            
            current_settings = {
                "cpu_governor": self._get_cpu_governor(),
                "gpu_power": self._get_gpu_power_state(),
                "memory_settings": self._get_memory_settings()
            }
            
            return {
                "profile_exists": True,
                "profile_type": profile.get("performance_profile", "unknown"),
                "settings_match": self._verify_settings(profile, current_settings),
                "current_settings": current_settings
            }
        except Exception as e:
            self.logger.error(f"Error checking profile status: {str(e)}")
            return {"error": str(e)}

    def check_optimization_status(self) -> Dict:
        """Verify system optimizations are properly applied"""
        try:
            return {
                "cpu": self._check_cpu_optimizations(),
                "memory": self._check_memory_optimizations(),
                "storage": self._check_storage_optimizations(),
                "network": self._check_network_optimizations()
            }
        except Exception as e:
            self.logger.error(f"Error checking optimization status: {str(e)}")
            return {"error": str(e)}

    def collect_performance_metrics(self) -> Dict:
        """Collect current system performance metrics"""
        metrics = {}
        
        try:
            # CPU usage and temperature
            cpu_info = subprocess.run(['mpstat', '1', '1'], capture_output=True, text=True)
            metrics['cpu'] = {
                'usage': 100 - float(cpu_info.stdout.split('\n')[-2].split()[-1]),
                'temperature': self._get_cpu_temperature()
            }
            
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                mem_info = f.read()
            total = int(mem_info.split('MemTotal:')[1].split()[0])
            available = int(mem_info.split('MemAvailable:')[1].split()[0])
            metrics['memory'] = {
                'total': total,
                'available': available,
                'used_percent': ((total - available) / total) * 100
            }
            
            # Disk I/O
            iostat = subprocess.run(['iostat', '-x', '1', '1'], capture_output=True, text=True)
            metrics['disk'] = {
                'util': float(iostat.stdout.split('\n')[-2].split()[-1]),
                'io_wait': float(iostat.stdout.split('\n')[-2].split()[3])
            }
            
            return metrics
        except Exception as e:
            self.logger.error(f"Error collecting performance metrics: {str(e)}")
            return {"error": str(e)}

    def check_error_logs(self) -> List[Dict]:
        """Check system logs for TUNIX-related errors"""
        errors = []
        try:
            # Check TUNIX logs
            if os.path.exists(f"{self.log_dir}/system.log"):
                with open(f"{self.log_dir}/system.log", 'r') as f:
                    for line in f:
                        if 'error' in line.lower() or 'fail' in line.lower():
                            errors.append({
                                'source': 'tunix',
                                'message': line.strip(),
                                'timestamp': line.split()[0]
                            })
            
            # Check system journal for related errors
            journal = subprocess.run(
                ['journalctl', '-u', 'tunix-optimize', '--no-pager', '-n', '50'],
                capture_output=True,
                text=True
            )
            for line in journal.stdout.split('\n'):
                if 'error' in line.lower() or 'fail' in line.lower():
                    errors.append({
                        'source': 'systemd',
                        'message': line.strip(),
                        'timestamp': line.split()[0]
                    })
            
            return errors
        except Exception as e:
            self.logger.error(f"Error checking error logs: {str(e)}")
            return [{"error": str(e)}]

    def generate_recommendations(self, diagnostic_results: Dict) -> List[str]:
        """Generate recommendations based on diagnostic results"""
        recommendations = []
        
        # Check profile status
        if not diagnostic_results['profile_status'].get('settings_match', False):
            recommendations.append("System settings don't match hardware profile. Consider running optimize-system.sh")
        
        # Check performance metrics
        metrics = diagnostic_results.get('performance_metrics', {})
        
        if 'memory' in metrics:
            mem_used = metrics['memory'].get('used_percent', 0)
            if mem_used > 90:
                recommendations.append("High memory usage detected. Consider closing unused applications or adding more RAM")
        
        if 'disk' in metrics:
            io_wait = metrics['disk'].get('io_wait', 0)
            if io_wait > 20:
                recommendations.append("High disk I/O wait detected. Consider upgrading to an SSD if using HDD")
        
        # Check optimization status
        opt_status = diagnostic_results.get('optimization_status', {})
        if isinstance(opt_status, dict) and 'error' in opt_status:
            recommendations.append("System optimizations may not be properly applied. Check system logs for details")
        
        return recommendations

    def _get_cpu_governor(self) -> str:
        """Get current CPU governor"""
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'r') as f:
                return f.read().strip()
        except:
            return "unknown"

    def _get_gpu_power_state(self) -> str:
        """Get current GPU power state"""
        # Try NVIDIA
        try:
            nvidia_smi = subprocess.run(['nvidia-smi', '-q'], capture_output=True, text=True)
            if 'Power Management' in nvidia_smi.stdout:
                return "nvidia-" + nvidia_smi.stdout.split('Power Management')[1].split('\n')[1].split(':')[1].strip()
        except:
            pass
        
        # Try AMD
        try:
            with open('/sys/class/drm/card0/device/power_dpm_state', 'r') as f:
                return "amd-" + f.read().strip()
        except:
            return "unknown"

    def _get_memory_settings(self) -> Dict:
        """Get current memory settings"""
        try:
            vm_swappiness = int(subprocess.run(['sysctl', 'vm.swappiness'], 
                                             capture_output=True, text=True).stdout.split('=')[1].strip())
            return {"swappiness": vm_swappiness}
        except:
            return {"error": "Could not read memory settings"}

    def _verify_settings(self, profile: Dict, current: Dict) -> bool:
        """Verify current settings match profile"""
        try:
            profile_settings = profile.get('performance_profiles', {}).get(
                profile.get('performance_profile', ''), {}
            ).get('power_management', {})
            
            return (
                profile_settings.get('cpu_governor') == current['cpu_governor'] and
                profile_settings.get('gpu_power') in current['gpu_power']
            )
        except:
            return False

    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available"""
        try:
            temps = subprocess.run(['sensors'], capture_output=True, text=True)
            for line in temps.stdout.split('\n'):
                if 'Package id 0:' in line:
                    return float(line.split('+')[1].split('°')[0])
        except:
            return None

    def _check_cpu_optimizations(self) -> Dict:
        """Check CPU optimization status"""
        return {
            "governor": self._get_cpu_governor(),
            "cores_online": self._count_online_cores(),
            "frequency_scaling": self._check_frequency_scaling()
        }

    def _check_memory_optimizations(self) -> Dict:
        """Check memory optimization status"""
        return {
            "swappiness": self._get_memory_settings(),
            "zram_status": self._check_zram_status()
        }

    def _check_storage_optimizations(self) -> Dict:
        """Check storage optimization status"""
        return {
            "scheduler": self._get_io_scheduler(),
            "trim_enabled": self._check_trim_status()
        }

    def _check_network_optimizations(self) -> Dict:
        """Check network optimization status"""
        return {
            "congestion_control": self._get_congestion_control(),
            "tcp_fastopen": self._check_tcp_fastopen()
        }

    def _count_online_cores(self) -> int:
        """Count number of online CPU cores"""
        return len([f for f in os.listdir('/sys/devices/system/cpu') 
                   if f.startswith('cpu') and f[3:].isdigit()])

    def _check_frequency_scaling(self) -> bool:
        """Check if CPU frequency scaling is working"""
        try:
            return os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq')
        except:
            return False

    def _check_zram_status(self) -> bool:
        """Check if ZRAM is enabled"""
        try:
            return 'zram0' in subprocess.run(['swapon', '-s'], 
                                           capture_output=True, text=True).stdout
        except:
            return False

    def _get_io_scheduler(self) -> str:
        """Get current I/O scheduler"""
        try:
            with open('/sys/block/sda/queue/scheduler', 'r') as f:
                return f.read().strip()
        except:
            return "unknown"

    def _check_trim_status(self) -> bool:
        """Check if TRIM is enabled"""
        try:
            return 'fstrim.timer' in subprocess.run(['systemctl', 'list-timers'], 
                                                   capture_output=True, text=True).stdout
        except:
            return False

    def _get_congestion_control(self) -> str:
        """Get current TCP congestion control algorithm"""
        try:
            with open('/proc/sys/net/ipv4/tcp_congestion_control', 'r') as f:
                return f.read().strip()
        except:
            return "unknown"

    def _check_tcp_fastopen(self) -> bool:
        """Check if TCP Fast Open is enabled"""
        try:
            with open('/proc/sys/net/ipv4/tcp_fastopen', 'r') as f:
                return int(f.read().strip()) > 0
        except:
            return False

if __name__ == "__main__":
    diagnostics = SystemDiagnostics()
    results = diagnostics.run_diagnostics()
    print(json.dumps(results, indent=2))