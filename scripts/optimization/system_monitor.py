#!/usr/bin/python3
import curses
import psutil
import json
import time
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

class SystemMonitor:
    def __init__(self):
        self.config_dir = Path("/etc/tunix/monitor")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.running = True
        self.current_page = 0
        self.pages = ["Overview", "CPU", "Memory", "Storage", "Power", "Network"]
        
        self.metrics_dir = Path("/var/log/tunix/metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.history_length = 3600  # 1 hour of history (1 sample/second)
        self.metrics_history = {
            "cpu": deque(maxlen=self.history_length),
            "memory": deque(maxlen=self.history_length),
            "disk": deque(maxlen=self.history_length),
            "network": deque(maxlen=self.history_length),
            "temperature": deque(maxlen=self.history_length),
            "power": deque(maxlen=self.history_length)
        }
        
        logging.basicConfig(
            filename="/var/log/tunix/system_monitor.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def start(self):
        """Start the system monitor interface"""
        curses.wrapper(self._main)
        
    def _main(self, stdscr):
        """Main interface loop"""
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.curs_set(0)
        
        while self.running:
            stdscr.clear()
            self._draw_header(stdscr)
            self._draw_menu(stdscr)
            
            if self.current_page == 0:
                self._draw_overview(stdscr)
            elif self.current_page == 1:
                self._draw_cpu(stdscr)
            elif self.current_page == 2:
                self._draw_memory(stdscr)
            elif self.current_page == 3:
                self._draw_storage(stdscr)
            elif self.current_page == 4:
                self._draw_power(stdscr)
            elif self.current_page == 5:
                self._draw_network(stdscr)
                
            self._draw_footer(stdscr)
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            if key == ord('q'):
                self.running = False
            elif key == curses.KEY_RIGHT:
                self.current_page = (self.current_page + 1) % len(self.pages)
            elif key == curses.KEY_LEFT:
                self.current_page = (self.current_page - 1) % len(self.pages)
            
            time.sleep(1)  # Update interval
            
    def _draw_header(self, stdscr):
        """Draw the header with system info"""
        header = f" TUNIX System Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        stdscr.addstr(0, 0, header.center(curses.COLS), curses.A_REVERSE)
        
    def _draw_menu(self, stdscr):
        """Draw the menu bar"""
        menu_items = [f" {page} " for page in self.pages]
        x_pos = 2
        for i, item in enumerate(menu_items):
            if i == self.current_page:
                stdscr.addstr(2, x_pos, item, curses.A_REVERSE)
            else:
                stdscr.addstr(2, x_pos, item)
            x_pos += len(item) + 2
            
    def _draw_overview(self, stdscr):
        """Draw system overview"""
        y_pos = 4
        
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_color = self._get_usage_color(cpu_percent)
        stdscr.addstr(y_pos, 2, "CPU Usage:")
        stdscr.addstr(y_pos, 15, f"{cpu_percent:>5.1f}%", cpu_color)
        
        # Memory Usage
        y_pos += 2
        mem = psutil.virtual_memory()
        mem_color = self._get_usage_color(mem.percent)
        stdscr.addstr(y_pos, 2, "Memory Usage:")
        stdscr.addstr(y_pos, 15, f"{mem.percent:>5.1f}%", mem_color)
        
        # Disk Usage
        y_pos += 2
        disk = psutil.disk_usage('/')
        disk_color = self._get_usage_color(disk.percent)
        stdscr.addstr(y_pos, 2, "Disk Usage:")
        stdscr.addstr(y_pos, 15, f"{disk.percent:>5.1f}%", disk_color)
        
        # Battery Status
        y_pos += 2
        battery = psutil.sensors_battery()
        if battery:
            bat_color = self._get_battery_color(battery.percent)
            status = "Charging" if battery.power_plugged else "Discharging"
            stdscr.addstr(y_pos, 2, "Battery:")
            stdscr.addstr(y_pos, 15, f"{battery.percent:>5.1f}% ({status})", bat_color)
        
        # Network Usage
        y_pos += 2
        net = psutil.net_io_counters()
        stdscr.addstr(y_pos, 2, "Network:")
        stdscr.addstr(y_pos, 15, f"↓ {self._format_bytes(net.bytes_recv)}/s  ↑ {self._format_bytes(net.bytes_sent)}/s")
        
        # System Temperature
        y_pos += 2
        temps = psutil.sensors_temperatures()
        if temps:
            max_temp = max(sensor.current for sensors in temps.values() for sensor in sensors)
            temp_color = self._get_temp_color(max_temp)
            stdscr.addstr(y_pos, 2, "Temperature:")
            stdscr.addstr(y_pos, 15, f"{max_temp:>5.1f}°C", temp_color)
            
    def _draw_cpu(self, stdscr):
        """Draw detailed CPU information"""
        y_pos = 4
        
        # Per-core usage
        cpu_percents = psutil.cpu_percent(interval=0.1, percpu=True)
        stdscr.addstr(y_pos, 2, "CPU Core Usage:")
        y_pos += 1
        
        for i, percent in enumerate(cpu_percents):
            if y_pos >= curses.LINES - 2:
                break
            cpu_color = self._get_usage_color(percent)
            bar = self._generate_bar(percent, 20)
            stdscr.addstr(y_pos, 2, f"Core {i:>2}:")
            stdscr.addstr(y_pos, 10, f"{percent:>5.1f}%", cpu_color)
            stdscr.addstr(y_pos, 16, bar)
            y_pos += 1
            
        # CPU frequency
        y_pos += 1
        freq = psutil.cpu_freq()
        if freq:
            stdscr.addstr(y_pos, 2, f"CPU Frequency: {freq.current:.1f} MHz")
            
    def _draw_memory(self, stdscr):
        """Draw detailed memory information"""
        y_pos = 4
        
        # Virtual memory
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        stdscr.addstr(y_pos, 2, "Memory Usage:")
        y_pos += 1
        
        total_gb = mem.total / (1024**3)
        used_gb = (mem.total - mem.available) / (1024**3)
        
        bar = self._generate_bar(mem.percent, 40)
        stdscr.addstr(y_pos, 2, f"RAM: {used_gb:.1f}GB / {total_gb:.1f}GB")
        stdscr.addstr(y_pos, 30, bar)
        
        # Swap usage
        y_pos += 2
        swap_total_gb = swap.total / (1024**3)
        swap_used_gb = swap.used / (1024**3)
        
        bar = self._generate_bar(swap.percent, 40)
        stdscr.addstr(y_pos, 2, f"Swap: {swap_used_gb:.1f}GB / {swap_total_gb:.1f}GB")
        stdscr.addstr(y_pos, 30, bar)
            
    def _draw_storage(self, stdscr):
        """Draw storage information"""
        y_pos = 4
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            if y_pos >= curses.LINES - 2:
                break
                
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                
                stdscr.addstr(y_pos, 2, f"Mount: {partition.mountpoint}")
                y_pos += 1
                bar = self._generate_bar(usage.percent, 40)
                stdscr.addstr(y_pos, 2, f"Usage: {used_gb:.1f}GB / {total_gb:.1f}GB")
                stdscr.addstr(y_pos, 30, bar)
                y_pos += 2
            except:
                continue
                
    def _draw_power(self, stdscr):
        """Draw power management information"""
        y_pos = 4
        
        # Battery information
        battery = psutil.sensors_battery()
        if battery:
            status = "Charging" if battery.power_plugged else "Discharging"
            time_left = ""
            if battery.secsleft > 0:
                hours = battery.secsleft // 3600
                minutes = (battery.secsleft % 3600) // 60
                time_left = f" ({hours:02d}:{minutes:02d} remaining)"
                
            bat_color = self._get_battery_color(battery.percent)
            bar = self._generate_bar(battery.percent, 40)
            
            stdscr.addstr(y_pos, 2, "Battery Status:")
            y_pos += 1
            stdscr.addstr(y_pos, 2, f"Level: {battery.percent}%{time_left}", bat_color)
            y_pos += 1
            stdscr.addstr(y_pos, 2, f"State: {status}")
            y_pos += 1
            stdscr.addstr(y_pos, 2, bar)
            
        # Power profile
        y_pos += 2
        with open("/etc/tunix/power/current_profile", "r") as f:
            current_profile = f.read().strip()
        stdscr.addstr(y_pos, 2, f"Power Profile: {current_profile.capitalize()}")
            
    def _draw_network(self, stdscr):
        """Draw network information"""
        y_pos = 4
        
        # Network interfaces
        interfaces = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        io_counters = psutil.net_io_counters(pernic=True)
        
        for nic, stats in interfaces.items():
            if y_pos >= curses.LINES - 2:
                break
                
            # Interface status
            status = "Up" if stats.isup else "Down"
            status_color = curses.color_pair(1) if stats.isup else curses.color_pair(2)
            stdscr.addstr(y_pos, 2, f"Interface: {nic}")
            stdscr.addstr(y_pos, 20, status, status_color)
            y_pos += 1
            
            # IP addresses
            if nic in addrs:
                for addr in addrs[nic]:
                    if addr.family == 2:  # IPv4
                        stdscr.addstr(y_pos, 4, f"IPv4: {addr.address}")
                        y_pos += 1
                    elif addr.family == 23:  # IPv6
                        stdscr.addstr(y_pos, 4, f"IPv6: {addr.address}")
                        y_pos += 1
                        
            # IO statistics
            if nic in io_counters:
                io = io_counters[nic]
                stdscr.addstr(y_pos, 4, f"TX: {self._format_bytes(io.bytes_sent)}")
                stdscr.addstr(y_pos, 20, f"RX: {self._format_bytes(io.bytes_recv)}")
                y_pos += 2
                
    def _draw_footer(self, stdscr):
        """Draw the footer with controls"""
        footer = " Q: Quit | ←/→: Navigate | R: Refresh "
        stdscr.addstr(curses.LINES-1, 0, footer.center(curses.COLS), curses.A_REVERSE)
        
    def _get_usage_color(self, percent: float) -> int:
        """Get color based on usage percentage"""
        if percent < 60:
            return curses.color_pair(1)  # Green
        elif percent < 85:
            return curses.color_pair(3)  # Yellow
        return curses.color_pair(2)      # Red
        
    def _get_battery_color(self, percent: float) -> int:
        """Get color based on battery percentage"""
        if percent > 40:
            return curses.color_pair(1)  # Green
        elif percent > 15:
            return curses.color_pair(3)  # Yellow
        return curses.color_pair(2)      # Red
        
    def _get_temp_color(self, temp: float) -> int:
        """Get color based on temperature"""
        if temp < 60:
            return curses.color_pair(1)  # Green
        elif temp < 80:
            return curses.color_pair(3)  # Yellow
        return curses.color_pair(2)      # Red
        
    def _generate_bar(self, percent: float, width: int) -> str:
        """Generate a progress bar"""
        filled = int(width * percent / 100)
        return f"[{'#' * filled}{'-' * (width - filled)}]"
        
    def _format_bytes(self, bytes: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f}{unit}"
            bytes /= 1024
        return f"{bytes:.1f}TB"

    def start(self, update_interval: int = 1):
        """Start monitoring system metrics"""
        while True:
            try:
                metrics = self.get_current_stats()
                self._update_history(metrics)
                self._analyze_metrics()
                self._save_metrics(metrics)
                time.sleep(update_interval)
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

    def get_current_stats(self) -> Dict:
        """Get current system statistics"""
        try:
            return {
                "timestamp": time.time(),
                "cpu": self._get_cpu_stats(),
                "memory": self._get_memory_stats(),
                "disk": self._get_disk_stats(),
                "network": self._get_network_stats(),
                "temperature": self._get_temperature_stats(),
                "power": self._get_power_stats()
            }
        except Exception as e:
            logging.error(f"Error getting system stats: {e}")
            return {}

    def _get_cpu_stats(self) -> Dict:
        """Get detailed CPU statistics"""
        try:
            cpu_times = psutil.cpu_times_percent(interval=1)
            cpu_freq = psutil.cpu_freq(percpu=True)
            return {
                "usage_percent": psutil.cpu_percent(interval=1, percpu=True),
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle,
                "iowait": cpu_times.iowait,
                "frequencies": [freq.current for freq in cpu_freq],
                "load_avg": [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()],
                "ctx_switches": psutil.cpu_stats().ctx_switches,
                "interrupts": psutil.cpu_stats().interrupts
            }
        except Exception as e:
            logging.error(f"Error getting CPU stats: {e}")
            return {}

    def _get_memory_stats(self) -> Dict:
        """Get detailed memory statistics"""
        try:
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "total": vm.total,
                "available": vm.available,
                "used": vm.used,
                "free": vm.free,
                "cached": vm.cached,
                "buffers": vm.buffers,
                "percent": vm.percent,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_free": swap.free,
                "swap_percent": swap.percent
            }
        except Exception as e:
            logging.error(f"Error getting memory stats: {e}")
            return {}

    def _get_disk_stats(self) -> Dict:
        """Get detailed disk statistics"""
        try:
            disk_stats = {}
            for partition in psutil.disk_partitions():
                if partition.fstype:
                    usage = psutil.disk_usage(partition.mountpoint)
                    io_counters = psutil.disk_io_counters(perdisk=True)
                    disk_name = partition.device.split('/')[-1]
                    
                    disk_stats[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                        "fstype": partition.fstype,
                        "io_stats": io_counters.get(disk_name, {})
                    }
            return disk_stats
        except Exception as e:
            logging.error(f"Error getting disk stats: {e}")
            return {}

    def _get_network_stats(self) -> Dict:
        """Get detailed network statistics"""
        try:
            net_stats = {}
            for interface, stats in psutil.net_io_counters(pernic=True).items():
                net_stats[interface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout
                }
                
                # Add connection counts
                connections = psutil.net_connections()
                net_stats[interface]["connections"] = len([
                    c for c in connections 
                    if c.status == 'ESTABLISHED'
                ])
                
            return net_stats
        except Exception as e:
            logging.error(f"Error getting network stats: {e}")
            return {}

    def _get_temperature_stats(self) -> Dict:
        """Get temperature information from sensors"""
        try:
            temps = {}
            if hasattr(psutil, "sensors_temperatures"):
                for name, entries in psutil.sensors_temperatures().items():
                    temps[name] = [
                        {"label": entry.label or str(i), "current": entry.current, "high": entry.high, "critical": entry.critical}
                        for i, entry in enumerate(entries)
                    ]
            return temps
        except Exception as e:
            logging.error(f"Error getting temperature stats: {e}")
            return {}

    def _get_power_stats(self) -> Dict:
        """Get power/battery information"""
        try:
            power_stats = {}
            if hasattr(psutil, "sensors_battery"):
                battery = psutil.sensors_battery()
                if battery:
                    power_stats.update({
                        "percent": battery.percent,
                        "power_plugged": battery.power_plugged,
                        "secsleft": battery.secsleft
                    })
                    
            # Try to get additional power info from system files
            for power_supply in Path("/sys/class/power_supply").glob("*"):
                try:
                    with open(power_supply / "type") as f:
                        psu_type = f.read().strip()
                    
                    psu_stats = {"type": psu_type}
                    
                    for stat_file in ["status", "capacity", "voltage_now", "current_now"]:
                        stat_path = power_supply / stat_file
                        if stat_path.exists():
                            with open(stat_path) as f:
                                psu_stats[stat_file] = f.read().strip()
                    
                    power_stats[power_supply.name] = psu_stats
                except Exception:
                    continue
                    
            return power_stats
        except Exception as e:
            logging.error(f"Error getting power stats: {e}")
            return {}

    def _update_history(self, metrics: Dict):
        """Update metrics history"""
        try:
            for category in self.metrics_history:
                if category in metrics:
                    self.metrics_history[category].append(metrics[category])
        except Exception as e:
            logging.error(f"Error updating metrics history: {e}")

    def _analyze_metrics(self):
        """Analyze metrics and detect trends/issues"""
        try:
            analysis = {}
            
            # CPU Analysis
            if len(self.metrics_history["cpu"]) > 60:  # At least 1 minute of data
                cpu_usage = [m.get("usage_percent", [0])[0] for m in self.metrics_history["cpu"]]
                analysis["cpu"] = {
                    "sustained_high_usage": any(
                        np.mean(cpu_usage[-60:]) > 80 for _ in range(5)
                    ),
                    "high_iowait": any(
                        m.get("iowait", 0) > 20 for m in self.metrics_history["cpu"][-60:]
                    )
                }
            
            # Memory Analysis
            if len(self.metrics_history["memory"]) > 60:
                mem_usage = [m.get("percent", 0) for m in self.metrics_history["memory"]]
                swap_usage = [m.get("swap_percent", 0) for m in self.metrics_history["memory"]]
                analysis["memory"] = {
                    "high_usage": np.mean(mem_usage[-60:]) > 85,
                    "increasing_trend": (
                        np.polyfit(range(60), mem_usage[-60:], 1)[0] > 0.1
                    ),
                    "high_swap_usage": np.mean(swap_usage[-60:]) > 50
                }
            
            # Temperature Analysis
            if len(self.metrics_history["temperature"]) > 60:
                temp_readings = []
                for temp_data in self.metrics_history["temperature"]:
                    for sensor in temp_data.values():
                        for reading in sensor:
                            if isinstance(reading, dict) and "current" in reading:
                                temp_readings.append(reading["current"])
                
                if temp_readings:
                    analysis["temperature"] = {
                        "overheating": any(t > 80 for t in temp_readings[-60:]),
                        "temperature_trend": np.polyfit(
                            range(len(temp_readings[-60:])), 
                            temp_readings[-60:], 
                            1
                        )[0]
                    }
            
            # Save analysis results
            analysis_file = self.metrics_dir / "analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            # Log critical issues
            self._log_critical_issues(analysis)
            
        except Exception as e:
            logging.error(f"Error analyzing metrics: {e}")

    def _log_critical_issues(self, analysis: Dict):
        """Log critical issues found during analysis"""
        try:
            if analysis.get("cpu", {}).get("sustained_high_usage"):
                logging.warning("Sustained high CPU usage detected")
            
            if analysis.get("memory", {}).get("high_usage"):
                logging.warning("High memory usage detected")
            
            if analysis.get("temperature", {}).get("overheating"):
                logging.warning("System temperature is too high")
            
        except Exception as e:
            logging.error(f"Error logging critical issues: {e}")

    def _save_metrics(self, metrics: Dict):
        """Save current metrics to file"""
        try:
            # Save detailed metrics every minute
            if int(metrics["timestamp"]) % 60 == 0:
                timestamp = time.strftime("%Y%m%d-%H%M", time.localtime(metrics["timestamp"]))
                metrics_file = self.metrics_dir / f"metrics-{timestamp}.json"
                with open(metrics_file, 'w') as f:
                    json.dump(metrics, f, indent=2)
                
                # Cleanup old metrics files (keep last 24 hours)
                cleanup_time = time.time() - 86400
                for old_file in self.metrics_dir.glob("metrics-*.json"):
                    try:
                        file_time = time.mktime(time.strptime(
                            old_file.stem.split("-")[1], 
                            "%Y%m%d-%H%M"
                        ))
                        if file_time < cleanup_time:
                            old_file.unlink()
                    except Exception:
                        continue
            
            # Always update current metrics
            current_file = self.metrics_dir / "current_metrics.json"
            with open(current_file, 'w') as f:
                json.dump(metrics, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving metrics: {e}")

    def set_update_interval(self, interval: int):
        """Set the metrics update interval"""
        self.update_interval = max(1, interval)  # Minimum 1 second

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.start()