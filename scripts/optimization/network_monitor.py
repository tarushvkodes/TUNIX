#!/usr/bin/python3
import curses
import psutil
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import deque

class NetworkMonitorPanel:
    def __init__(self, stdscr, start_y: int, start_x: int, height: int, width: int):
        self.window = stdscr.derwin(height, width, start_y, start_x)
        self.height = height
        self.width = width
        self.history_length = 60  # 1 minute of history
        self.rx_history = {}  # Interface -> deque
        self.tx_history = {}  # Interface -> deque
        self.interfaces = {}
        
    def update(self):
        """Update network statistics"""
        stats = psutil.net_io_counters(pernic=True)
        
        # Initialize histories for new interfaces
        for interface in stats:
            if interface not in self.rx_history:
                self.rx_history[interface] = deque([0] * self.history_length, maxlen=self.history_length)
                self.tx_history[interface] = deque([0] * self.history_length, maxlen=self.history_length)
            
            # Calculate rates
            self.rx_history[interface].append(stats[interface].bytes_recv)
            self.tx_history[interface].append(stats[interface].bytes_sent)
        
        # Update interface details
        self.interfaces = self._get_interface_details()
        
    def _get_interface_details(self) -> Dict:
        """Get detailed information about network interfaces"""
        details = {}
        try:
            # Get interface addresses
            addrs = psutil.net_if_addrs()
            # Get interface statistics
            stats = psutil.net_if_stats()
            
            for interface in stats:
                details[interface] = {
                    "isup": stats[interface].isup,
                    "speed": stats[interface].speed,
                    "mtu": stats[interface].mtu,
                    "addresses": [],
                    "is_wifi": Path(f"/sys/class/net/{interface}/wireless").exists()
                }
                
                # Add IP addresses
                if interface in addrs:
                    for addr in addrs[interface]:
                        if addr.family == 2:  # IPv4
                            details[interface]["addresses"].append({
                                "ip": addr.address,
                                "netmask": addr.netmask
                            })
                
                # Add WiFi information if applicable
                if details[interface]["is_wifi"]:
                    wifi_info = self._get_wifi_info(interface)
                    details[interface].update(wifi_info)
                    
        except Exception as e:
            pass
        return details
    
    def _get_wifi_info(self, interface: str) -> Dict:
        """Get WiFi-specific information"""
        info = {
            "signal_strength": None,
            "ssid": None,
            "frequency": None
        }
        try:
            import subprocess
            result = subprocess.run(
                ["iwconfig", interface],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                # Extract SSID
                if "ESSID:" in output:
                    info["ssid"] = output.split("ESSID:")[1].split('"')[1]
                # Extract signal strength
                if "Signal level=" in output:
                    info["signal_strength"] = int(
                        output.split("Signal level=")[1].split(" ")[0]
                    )
                # Extract frequency
                if "Frequency:" in output:
                    info["frequency"] = float(
                        output.split("Frequency:")[1].split(" ")[0]
                    )
        except:
            pass
        return info
    
    def _calculate_rate(self, history: deque) -> float:
        """Calculate transfer rate from history"""
        if len(history) < 2:
            return 0
        return (history[-1] - history[-2])
    
    def _format_speed(self, bytes_per_sec: float) -> str:
        """Format transfer speed in human-readable format"""
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        unit_index = 0
        while bytes_per_sec >= 1024 and unit_index < len(units) - 1:
            bytes_per_sec /= 1024
            unit_index += 1
        return f"{bytes_per_sec:.1f} {units[unit_index]}"
    
    def _draw_graph(self, y: int, x: int, width: int, height: int, data: List[float], 
                   max_value: float) -> None:
        """Draw a simple ASCII graph"""
        if not data or max_value == 0:
            return
            
        for i in range(min(width, len(data))):
            value = data[-(i+1)]
            bar_height = int((value / max_value) * (height - 1))
            for h in range(height):
                char = '█' if h < bar_height else '░'
                try:
                    self.window.addch(y + (height - 1 - h), x + i, char)
                except curses.error:
                    pass

    def draw(self):
        """Draw the network monitoring panel"""
        self.window.clear()
        self.window.box()
        self.window.addstr(0, 2, " Network Monitor ")
        
        y_pos = 1
        for interface, details in self.interfaces.items():
            if y_pos >= self.height - 3:
                break
                
            # Skip loopback
            if interface == "lo":
                continue
            
            # Interface name and status
            status = "UP" if details["isup"] else "DOWN"
            status_color = curses.color_pair(1) if details["isup"] else curses.color_pair(2)
            self.window.addstr(y_pos, 2, f"{interface}: ")
            self.window.addstr(status, status_color)
            
            # IP addresses
            y_pos += 1
            for addr in details.get("addresses", []):
                if y_pos >= self.height - 3:
                    break
                self.window.addstr(y_pos, 4, f"IP: {addr['ip']}")
                y_pos += 1
            
            # Current transfer rates
            rx_rate = self._calculate_rate(self.rx_history[interface])
            tx_rate = self._calculate_rate(self.tx_history[interface])
            
            if y_pos < self.height - 3:
                self.window.addstr(y_pos, 4, f"↓ {self._format_speed(rx_rate)}")
                self.window.addstr(y_pos, 25, f"↑ {self._format_speed(tx_rate)}")
            
            # Draw mini graphs
            graph_width = 20
            graph_height = 3
            if y_pos + graph_height < self.height - 3:
                # Calculate max values for scaling
                max_rx = max(max(self.rx_history[interface]), 1)
                max_tx = max(max(self.tx_history[interface]), 1)
                
                # Draw RX graph
                y_pos += 1
                self.window.addstr(y_pos, 4, "RX:")
                self._draw_graph(y_pos, 8, graph_width, graph_height, 
                               list(self.rx_history[interface]), max_rx)
                
                # Draw TX graph
                self.window.addstr(y_pos, 30, "TX:")
                self._draw_graph(y_pos, 34, graph_width, graph_height,
                               list(self.tx_history[interface]), max_tx)
                
                y_pos += graph_height + 1
            
            # Add separator
            if y_pos < self.height - 3:
                self.window.hline(y_pos, 1, curses.ACS_HLINE, self.width - 2)
                y_pos += 1
        
        self.window.refresh()

if __name__ == "__main__":
    def main(stdscr):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        
        height, width = stdscr.getmaxyx()
        monitor = NetworkMonitorPanel(stdscr, 0, 0, height, width)
        
        while True:
            monitor.update()
            monitor.draw()
            time.sleep(1)
    
    curses.wrapper(main)