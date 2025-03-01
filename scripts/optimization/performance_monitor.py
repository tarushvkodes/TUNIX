#!/usr/bin/python3
import curses
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from performance_analyzer import PerformanceAnalyzer

class PerformanceMonitor:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.analyzer = PerformanceAnalyzer()
        self.current_view = "overview"  # overview, cpu, memory, io, thermal
        self.views = ["Overview", "CPU", "Memory", "I/O", "Thermal"]
        
        # Setup colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # Good
        curses.init_pair(2, curses.COLOR_RED, -1)     # Critical
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Warning
        curses.init_pair(4, curses.COLOR_CYAN, -1)    # Info
        
        # Hide cursor
        curses.curs_set(0)
        
    def run(self):
        """Main monitoring loop"""
        while True:
            # Collect latest metrics
            metrics = self.analyzer.collect_metrics()
            analysis = self.analyzer.analyze_performance()
            
            # Clear screen
            self.stdscr.clear()
            
            # Draw interface
            self._draw_header()
            self._draw_menu()
            
            if self.current_view == "overview":
                self._draw_overview(metrics, analysis)
            elif self.current_view == "cpu":
                self._draw_cpu_view(metrics)
            elif self.current_view == "memory":
                self._draw_memory_view(metrics)
            elif self.current_view == "io":
                self._draw_io_view(metrics)
            elif self.current_view == "thermal":
                self._draw_thermal_view(metrics)
            
            self._draw_footer(analysis)
            
            # Refresh screen
            self.stdscr.refresh()
            
            # Handle input
            key = self.stdscr.getch()
            if key == ord('q'):
                break
            elif key == curses.KEY_RIGHT:
                self._next_view()
            elif key == curses.KEY_LEFT:
                self._prev_view()
            
            # Wait before next update
            curses.napms(1000)  # 1 second refresh
            
    def _draw_header(self):
        """Draw header with basic system info"""
        header = f" TUNIX Performance Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
        self.stdscr.addstr(0, 0, header.center(curses.COLS), curses.A_REVERSE)
        
    def _draw_menu(self):
        """Draw menu bar"""
        menu_items = [f" {view} " for view in self.views]
        x_pos = 2
        for i, item in enumerate(menu_items):
            if self.views[i].lower() == self.current_view:
                self.stdscr.addstr(2, x_pos, item, curses.A_REVERSE)
            else:
                self.stdscr.addstr(2, x_pos, item)
            x_pos += len(item) + 2
            
    def _draw_overview(self, metrics: Dict, analysis: Dict):
        """Draw system overview"""
        y_pos = 4
        
        # System load
        load1, load5, load15 = metrics["cpu"]["load_avg"]
        self.stdscr.addstr(y_pos, 2, "System Load:")
        self.stdscr.addstr(y_pos, 15, f"{load1:.2f} {load5:.2f} {load5:.2f}")
        
        # CPU Usage
        y_pos += 2
        cpu_color = self._get_usage_color(metrics["cpu"]["overall_percent"])
        self.stdscr.addstr(y_pos, 2, "CPU Usage:")
        self.stdscr.addstr(y_pos, 15, f"{metrics['cpu']['overall_percent']:>5.1f}%", cpu_color)
        
        # Memory Usage
        y_pos += 1
        mem_color = self._get_usage_color(metrics["memory"]["virtual"]["percent"])
        self.stdscr.addstr(y_pos, 2, "Memory Usage:")
        self.stdscr.addstr(y_pos, 15, f"{metrics['memory']['virtual']['percent']:>5.1f}%", mem_color)
        
        # Swap Usage
        y_pos += 1
        swap_color = self._get_usage_color(metrics["memory"]["swap"]["percent"])
        self.stdscr.addstr(y_pos, 2, "Swap Usage:")
        self.stdscr.addstr(y_pos, 15, f"{metrics['memory']['swap']['percent']:>5.1f}%", swap_color)
        
        # Top Processes
        y_pos += 2
        self.stdscr.addstr(y_pos, 2, "Top Processes:", curses.A_BOLD)
        y_pos += 1
        for proc in metrics["processes"][:5]:
            if y_pos >= curses.LINES - 3:
                break
            self.stdscr.addstr(y_pos, 4, 
                f"{proc['name'][:20]:<20} CPU: {proc['cpu_percent']:>5.1f}% "
                f"MEM: {proc['memory_percent']:>5.1f}%"
            )
            y_pos += 1
            
        # Analysis Warnings
        y_pos += 2
        if analysis["warnings"]:
            self.stdscr.addstr(y_pos, 2, "Warnings:", curses.color_pair(3) | curses.A_BOLD)
            y_pos += 1
            for warning in analysis["warnings"]:
                if y_pos >= curses.LINES - 3:
                    break
                self.stdscr.addstr(y_pos, 4, warning, curses.color_pair(3))
                y_pos += 1
                
    def _draw_cpu_view(self, metrics: Dict):
        """Draw detailed CPU information"""
        y_pos = 4
        
        # Overall CPU usage
        self.stdscr.addstr(y_pos, 2, "CPU Usage:")
        cpu_color = self._get_usage_color(metrics["cpu"]["overall_percent"])
        self.stdscr.addstr(y_pos, 15, f"{metrics['cpu']['overall_percent']:>5.1f}%", cpu_color)
        
        # Per-CPU usage
        y_pos += 2
        self.stdscr.addstr(y_pos, 2, "CPU Core Usage:", curses.A_BOLD)
        y_pos += 1
        for i, usage in enumerate(metrics["cpu"]["per_cpu_percent"]):
            if y_pos >= curses.LINES - 3:
                break
            color = self._get_usage_color(usage)
            bar = self._generate_bar(usage, 30)
            self.stdscr.addstr(y_pos, 4, f"Core {i:>2}:")
            self.stdscr.addstr(y_pos, 12, f"{usage:>5.1f}%", color)
            self.stdscr.addstr(y_pos, 20, bar)
            y_pos += 1
            
        # CPU frequency information
        y_pos += 1
        if metrics["cpu"]["freq"]:
            self.stdscr.addstr(y_pos, 2, "CPU Frequencies:", curses.A_BOLD)
            y_pos += 1
            for cpu, freq in metrics["cpu"]["freq"].items():
                if y_pos >= curses.LINES - 3:
                    break
                self.stdscr.addstr(y_pos, 4, 
                    f"{cpu}: Current: {freq['current']:>4.0f}MHz "
                    f"(Min: {freq['min']:>4.0f}MHz, Max: {freq['max']:>4.0f}MHz)"
                )
                y_pos += 1
                
    def _draw_memory_view(self, metrics: Dict):
        """Draw detailed memory information"""
        y_pos = 4
        vm = metrics["memory"]["virtual"]
        swap = metrics["memory"]["swap"]
        
        # Virtual Memory
        self.stdscr.addstr(y_pos, 2, "Virtual Memory:", curses.A_BOLD)
        y_pos += 1
        
        total_gb = vm["total"] / (1024**3)
        used_gb = (vm["total"] - vm["available"]) / (1024**3)
        
        color = self._get_usage_color(vm["percent"])
        bar = self._generate_bar(vm["percent"], 40)
        
        self.stdscr.addstr(y_pos, 4, f"Usage: {used_gb:.1f}GB / {total_gb:.1f}GB ({vm['percent']}%)")
        y_pos += 1
        self.stdscr.addstr(y_pos, 4, bar, color)
        
        # Memory details
        y_pos += 2
        details = [
            ("Active", vm["active"]),
            ("Inactive", vm["inactive"]),
            ("Buffers", vm["buffers"]),
            ("Cached", vm["cached"])
        ]
        
        for label, value in details:
            if y_pos >= curses.LINES - 3:
                break
            gb = value / (1024**3)
            self.stdscr.addstr(y_pos, 4, f"{label}: {gb:.1f}GB")
            y_pos += 1
            
        # Swap Memory
        y_pos += 1
        if y_pos < curses.LINES - 3:
            self.stdscr.addstr(y_pos, 2, "Swap Memory:", curses.A_BOLD)
            y_pos += 1
            
            swap_total_gb = swap["total"] / (1024**3)
            swap_used_gb = swap["used"] / (1024**3)
            
            color = self._get_usage_color(swap["percent"])
            bar = self._generate_bar(swap["percent"], 40)
            
            self.stdscr.addstr(y_pos, 4, 
                f"Usage: {swap_used_gb:.1f}GB / {swap_total_gb:.1f}GB ({swap['percent']}%)"
            )
            y_pos += 1
            self.stdscr.addstr(y_pos, 4, bar, color)
            
    def _draw_io_view(self, metrics: Dict):
        """Draw I/O information"""
        y_pos = 4
        
        # Disk I/O
        self.stdscr.addstr(y_pos, 2, "Disk I/O:", curses.A_BOLD)
        y_pos += 1
        
        for disk, stats in metrics["io"]["disk"].items():
            if y_pos >= curses.LINES - 3:
                break
            
            read_mb = stats["read_bytes"] / (1024**2)
            write_mb = stats["write_bytes"] / (1024**2)
            
            self.stdscr.addstr(y_pos, 4, f"{disk}:")
            self.stdscr.addstr(y_pos, 15, 
                f"Read: {read_mb:.1f}MB ({stats['read_count']} ops) "
                f"Write: {write_mb:.1f}MB ({stats['write_count']} ops)"
            )
            y_pos += 1
            
        # Network I/O
        y_pos += 1
        if y_pos < curses.LINES - 3:
            self.stdscr.addstr(y_pos, 2, "Network I/O:", curses.A_BOLD)
            y_pos += 1
            
            for nic, stats in metrics["io"]["network"].items():
                if y_pos >= curses.LINES - 3:
                    break
                    
                recv_mb = stats["bytes_recv"] / (1024**2)
                sent_mb = stats["bytes_sent"] / (1024**2)
                
                self.stdscr.addstr(y_pos, 4, f"{nic}:")
                self.stdscr.addstr(y_pos, 15,
                    f"↓ {recv_mb:.1f}MB ({stats['packets_recv']} pkts) "
                    f"↑ {sent_mb:.1f}MB ({stats['packets_sent']} pkts)"
                )
                
                if stats["errin"] > 0 or stats["errout"] > 0:
                    y_pos += 1
                    self.stdscr.addstr(y_pos, 6,
                        f"Errors: ↓ {stats['errin']} ↑ {stats['errout']} "
                        f"Drops: ↓ {stats['dropin']} ↑ {stats['dropout']}",
                        curses.color_pair(2)
                    )
                y_pos += 1
                
    def _draw_thermal_view(self, metrics: Dict):
        """Draw thermal information"""
        y_pos = 4
        
        self.stdscr.addstr(y_pos, 2, "Temperature Sensors:", curses.A_BOLD)
        y_pos += 1
        
        for sensor_name, sensors in metrics["thermal"].items():
            if y_pos >= curses.LINES - 3:
                break
                
            self.stdscr.addstr(y_pos, 2, f"{sensor_name}:", curses.A_BOLD)
            y_pos += 1
            
            for sensor in sensors:
                if y_pos >= curses.LINES - 3:
                    break
                    
                temp_color = self._get_temp_color(sensor["current"])
                self.stdscr.addstr(y_pos, 4, f"{sensor['label']}: ")
                self.stdscr.addstr(f"{sensor['current']:>5.1f}°C", temp_color)
                
                if sensor["high"] is not None:
                    self.stdscr.addstr(f" (High: {sensor['high']}°C)")
                if sensor["critical"] is not None:
                    self.stdscr.addstr(f" (Crit: {sensor['critical']}°C)")
                    
                y_pos += 1
            y_pos += 1
            
    def _draw_footer(self, analysis: Dict):
        """Draw footer with controls and recommendations"""
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            rec_text = f" Recommendation: {recommendations[0]} "
        else:
            rec_text = " System running optimally "
            
        controls = " Q: Quit | ←/→: Change View | R: Refresh "
        
        y = curses.LINES - 1
        self.stdscr.addstr(y, 0, rec_text.ljust(curses.COLS - len(controls)), 
                          curses.color_pair(4))
        self.stdscr.addstr(y, curses.COLS - len(controls), controls, curses.A_REVERSE)
        
    def _get_usage_color(self, percent: float) -> int:
        """Get color based on usage percentage"""
        if percent < 60:
            return curses.color_pair(1)  # Green
        elif percent < 85:
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
        
    def _next_view(self):
        """Switch to next view"""
        current_index = self.views.index(self.current_view.capitalize())
        self.current_view = self.views[(current_index + 1) % len(self.views)].lower()
        
    def _prev_view(self):
        """Switch to previous view"""
        current_index = self.views.index(self.current_view.capitalize())
        self.current_view = self.views[(current_index - 1) % len(self.views)].lower()

if __name__ == "__main__":
    def main(stdscr):
        monitor = PerformanceMonitor(stdscr)
        monitor.run()
    
    curses.wrapper(main)