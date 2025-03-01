#!/usr/bin/python3
import json
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque

@dataclass
class NetworkProfile:
    interface: str
    type: str  # ethernet, wifi, etc.
    speed: int  # in Mbps
    supports_offload: bool
    supports_power_mgmt: bool

class NetworkOptimizer:
    def __init__(self):
        self.config_dir = Path("/etc/tunix/network")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.history_length = 60  # Keep 1 hour of history (1 sample/minute)
        self.performance_history = deque(maxlen=self.history_length)
        
        logging.basicConfig(
            filename="/var/log/tunix/network_optimizer.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def detect_network_interfaces(self) -> Dict[str, NetworkProfile]:
        """Detect and profile network interfaces"""
        interfaces = {}
        try:
            # Get list of interfaces
            for iface in Path("/sys/class/net").iterdir():
                if iface.name not in ("lo", "docker0"):
                    interface_type = self._detect_interface_type(iface.name)
                    speed = self._get_interface_speed(iface.name)
                    supports_offload = self._check_offload_support(iface.name)
                    supports_power_mgmt = self._check_power_mgmt_support(iface.name)
                    
                    interfaces[iface.name] = NetworkProfile(
                        interface=iface.name,
                        type=interface_type,
                        speed=speed,
                        supports_offload=supports_offload,
                        supports_power_mgmt=supports_power_mgmt
                    )
        except Exception as e:
            logging.error(f"Error detecting network interfaces: {e}")
        
        return interfaces

    def _detect_interface_type(self, interface: str) -> str:
        """Detect the type of network interface"""
        try:
            if Path(f"/sys/class/net/{interface}/wireless").exists():
                return "wifi"
            elif Path(f"/sys/class/net/{interface}/device/driver").exists():
                return "ethernet"
            else:
                return "unknown"
        except Exception:
            return "unknown"

    def _get_interface_speed(self, interface: str) -> int:
        """Get interface speed in Mbps"""
        try:
            # Try ethtool first
            result = subprocess.run(
                ["ethtool", interface],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if "Speed:" in line:
                    return int(line.split(':')[1].strip().replace('Mb/s', ''))
            
            # Fallback to sysfs
            speed_path = Path(f"/sys/class/net/{interface}/speed")
            if speed_path.exists():
                return int(speed_path.read_text().strip())
            
            return 100  # Default assumption
        except Exception:
            return 100

    def _check_offload_support(self, interface: str) -> bool:
        """Check if interface supports hardware offloading"""
        try:
            result = subprocess.run(
                ["ethtool", "-k", interface],
                capture_output=True,
                text=True
            )
            return "tcp-segmentation-offload: on" in result.stdout
        except Exception:
            return False

    def _check_power_mgmt_support(self, interface: str) -> bool:
        """Check if interface supports power management"""
        try:
            if self._detect_interface_type(interface) == "wifi":
                result = subprocess.run(
                    ["iwconfig", interface],
                    capture_output=True,
                    text=True
                )
                return "Power Management" in result.stdout
            else:
                result = subprocess.run(
                    ["ethtool", "--show-features", interface],
                    capture_output=True,
                    text=True
                )
                return "wake-on-lan: enabled" in result.stdout
        except Exception:
            return False

    def optimize_interface(self, profile: NetworkProfile, power_save: bool = False):
        """Apply optimizations for a network interface"""
        try:
            if profile.type == "ethernet":
                self._optimize_ethernet(profile, power_save)
            elif profile.type == "wifi":
                self._optimize_wifi(profile, power_save)
            
            # Apply common optimizations
            self._optimize_tcp_stack(profile)
            self._configure_qos(profile)
            
        except Exception as e:
            logging.error(f"Error optimizing interface {profile.interface}: {e}")

    def _optimize_ethernet(self, profile: NetworkProfile, power_save: bool):
        """Apply ethernet-specific optimizations"""
        try:
            # Configure hardware offloading
            if profile.supports_offload:
                subprocess.run([
                    "ethtool", "-K", profile.interface,
                    "tso", "on",
                    "gso", "on",
                    "gro", "on"
                ])
            
            # Set flow control
            subprocess.run([
                "ethtool", "-A", profile.interface,
                "rx", "on",
                "tx", "on"
            ])
            
            # Configure interrupt coalescence
            if profile.speed >= 1000:  # 1Gbps or faster
                subprocess.run([
                    "ethtool", "-C", profile.interface,
                    "rx-usecs", "3",
                    "tx-usecs", "3"
                ])
            
            # Power management
            if power_save and profile.supports_power_mgmt:
                subprocess.run([
                    "ethtool", "--set-eee", profile.interface,
                    "eee", "on"
                ])
            
        except Exception as e:
            logging.error(f"Error optimizing ethernet interface {profile.interface}: {e}")

    def _optimize_wifi(self, profile: NetworkProfile, power_save: bool):
        """Apply WiFi-specific optimizations"""
        try:
            # Power management
            power_mode = "on" if power_save else "off"
            subprocess.run([
                "iwconfig", profile.interface,
                "power", power_mode
            ])
            
            # Configure rate control algorithm
            subprocess.run([
                "iwconfig", profile.interface,
                "rate", "auto"
            ])
            
            # Set RTS threshold for better performance in crowded environments
            subprocess.run([
                "iwconfig", profile.interface,
                "rts", "2347"  # Default maximum
            ])
            
        except Exception as e:
            logging.error(f"Error optimizing wifi interface {profile.interface}: {e}")

    def _optimize_tcp_stack(self, profile: NetworkProfile):
        """Optimize TCP stack settings"""
        try:
            # Calculate optimal buffer sizes based on bandwidth-delay product
            rtt = self._measure_rtt()
            optimal_buffer = (profile.speed * 1000000 / 8) * (rtt / 1000)
            
            # Set TCP buffer sizes
            subprocess.run([
                "sysctl", "-w",
                f"net.ipv4.tcp_rmem='4096 87380 {int(optimal_buffer)}'",
                f"net.ipv4.tcp_wmem='4096 87380 {int(optimal_buffer)}'"
            ])
            
            # Enable TCP BBR congestion control if available
            if self._check_bbr_available():
                subprocess.run([
                    "sysctl", "-w",
                    "net.ipv4.tcp_congestion_control=bbr"
                ])
            
            # Other TCP optimizations
            subprocess.run([
                "sysctl", "-w",
                "net.ipv4.tcp_fastopen=3",
                "net.ipv4.tcp_slow_start_after_idle=0",
                "net.ipv4.tcp_no_metrics_save=1"
            ])
            
        except Exception as e:
            logging.error(f"Error optimizing TCP stack: {e}")

    def _configure_qos(self, profile: NetworkProfile):
        """Configure Quality of Service"""
        try:
            # Set up traffic classes
            subprocess.run([
                "tc", "qdisc", "add", "dev", profile.interface,
                "root", "handle", "1:", "htb", "default", "30"
            ])
            
            # Configure rate limiting
            rate = f"{profile.speed}mbit"
            subprocess.run([
                "tc", "class", "add", "dev", profile.interface,
                "parent", "1:", "classid", "1:1",
                "htb", "rate", rate, "ceil", rate
            ])
            
            # Priority queues for different traffic types
            priorities = {
                "1:10": "high",   # Interactive traffic
                "1:20": "normal", # Bulk transfers
                "1:30": "low"     # Background traffic
            }
            
            for classid, priority in priorities.items():
                subprocess.run([
                    "tc", "class", "add", "dev", profile.interface,
                    "parent", "1:1", "classid", classid,
                    "htb", "rate", f"{int(profile.speed/3)}mbit",
                    "ceil", rate, "prio", str(len(priorities))
                ])
            
        except Exception as e:
            logging.error(f"Error configuring QoS: {e}")

    def _measure_rtt(self) -> float:
        """Measure round-trip time to a reliable host"""
        try:
            result = subprocess.run(
                ["ping", "-c", "3", "8.8.8.8"],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if "avg" in line:
                    # Extract average RTT
                    rtt = float(line.split('/')[4])
                    return rtt
            
            return 50.0  # Default assumption
        except Exception:
            return 50.0

    def _check_bbr_available(self) -> bool:
        """Check if BBR congestion control is available"""
        try:
            with open("/proc/sys/net/ipv4/tcp_available_congestion_control") as f:
                return "bbr" in f.read()
        except Exception:
            return False

    def monitor_network_performance(self):
        """Monitor network performance and adjust settings"""
        while True:
            try:
                metrics = self._collect_performance_metrics()
                self.performance_history.append(metrics)
                
                # Analyze trends and adjust if needed
                if len(self.performance_history) >= 5:
                    self._analyze_and_adjust()
                
                time.sleep(60)  # Sample every minute
                
            except Exception as e:
                logging.error(f"Error in network monitoring: {e}")
                time.sleep(10)

    def _collect_performance_metrics(self) -> Dict:
        """Collect current network performance metrics"""
        metrics = {}
        try:
            # Get interface statistics
            for interface in self.detect_network_interfaces().values():
                stats_path = Path(f"/sys/class/net/{interface.interface}/statistics")
                metrics[interface.interface] = {
                    "rx_bytes": int((stats_path / "rx_bytes").read_text()),
                    "tx_bytes": int((stats_path / "tx_bytes").read_text()),
                    "rx_errors": int((stats_path / "rx_errors").read_text()),
                    "tx_errors": int((stats_path / "tx_errors").read_text()),
                    "rx_dropped": int((stats_path / "rx_dropped").read_text()),
                    "tx_dropped": int((stats_path / "tx_dropped").read_text())
                }
            
            # Get connection tracking statistics
            with open("/proc/net/stat/nf_conntrack") as f:
                metrics["conntrack"] = len(f.readlines())
            
            return metrics
            
        except Exception as e:
            logging.error(f"Error collecting network metrics: {e}")
            return {}

    def _analyze_and_adjust(self):
        """Analyze performance trends and adjust settings"""
        try:
            # Calculate rates and error rates
            current = self.performance_history[-1]
            previous = self.performance_history[-2]
            
            for interface, stats in current.items():
                if interface in previous:
                    # Skip non-interface metrics
                    if interface == "conntrack":
                        continue
                        
                    prev_stats = previous[interface]
                    
                    # Calculate rates
                    rx_rate = (stats["rx_bytes"] - prev_stats["rx_bytes"]) / 60
                    tx_rate = (stats["tx_bytes"] - prev_stats["tx_bytes"]) / 60
                    error_rate = (
                        (stats["rx_errors"] + stats["tx_errors"]) -
                        (prev_stats["rx_errors"] + prev_stats["tx_errors"])
                    ) / 60
                    
                    # Adjust based on metrics
                    if error_rate > 10:  # More than 10 errors per second
                        self._adjust_for_errors(interface)
                    elif rx_rate > 100000000 or tx_rate > 100000000:  # >100MB/s
                        self._adjust_for_high_throughput(interface)
                    
        except Exception as e:
            logging.error(f"Error analyzing network performance: {e}")

    def _adjust_for_errors(self, interface: str):
        """Adjust settings when seeing high error rates"""
        try:
            # Reduce offload features
            subprocess.run([
                "ethtool", "-K", interface,
                "tso", "off",
                "gso", "off"
            ])
            
            # Increase interrupt coalescence
            subprocess.run([
                "ethtool", "-C", interface,
                "rx-usecs", "100",
                "tx-usecs", "100"
            ])
            
        except Exception as e:
            logging.error(f"Error adjusting for errors on {interface}: {e}")

    def _adjust_for_high_throughput(self, interface: str):
        """Adjust settings for high throughput"""
        try:
            # Enable all offload features
            subprocess.run([
                "ethtool", "-K", interface,
                "tso", "on",
                "gso", "on",
                "gro", "on"
            ])
            
            # Optimize interrupt coalescence
            subprocess.run([
                "ethtool", "-C", interface,
                "rx-usecs", "3",
                "tx-usecs", "3"
            ])
            
            # Increase ring buffer sizes
            subprocess.run([
                "ethtool", "-G", interface,
                "rx", "4096",
                "tx", "4096"
            ])
            
        except Exception as e:
            logging.error(f"Error adjusting for high throughput on {interface}: {e}")

if __name__ == "__main__":
    optimizer = NetworkOptimizer()
    interfaces = optimizer.detect_network_interfaces()
    
    # Initial optimization
    for profile in interfaces.values():
        optimizer.optimize_interface(profile)
    
    # Start monitoring and dynamic adjustment
    optimizer.monitor_network_performance()