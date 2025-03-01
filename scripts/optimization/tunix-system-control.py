#!/usr/bin/python3
import sys
import time
import logging
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from power_manager import PowerManager
from system_diagnostics import SystemDiagnostics

import argparse
import json
import curses
from typing import Dict, List, Optional
from datetime import datetime

class TUNIXSystemController:
    def __init__(self):
        self.power_manager = PowerManager()
        self.diagnostics = SystemDiagnostics()
        self.config_dir = Path("/etc/tunix/system-control")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename="/var/log/tunix/system-control.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def run_control_loop(self):
        """Main control loop for system optimization"""
        while True:
            try:
                # Generate diagnostic report
                report = self.diagnostics.generate_diagnostic_report()
                
                # Get optimization suggestions
                suggestions = self.diagnostics.suggest_optimizations(report)
                
                # Apply automatic optimizations based on system state
                self._apply_automatic_optimizations(report)
                
                # Log suggestions that require user intervention
                for suggestion in suggestions:
                    logging.info(f"System suggestion: {suggestion}")
                
                # Wait before next iteration
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                logging.error(f"Error in control loop: {e}")
                time.sleep(60)  # Wait 1 minute on error

    def _apply_automatic_optimizations(self, report):
        """Apply automatic optimizations based on system state"""
        try:
            # Check thermal conditions
            if any(temp > 80 for temp in report["thermal"].values()):
                logging.warning("High temperature detected - applying thermal mitigation")
                self.power_manager.set_power_profile("powersave")
                return

            # Check power conditions
            power_metrics = report["power"]
            if not power_metrics.get("power_plugged", True):
                battery_percent = power_metrics.get("battery_percent", 100)
                if battery_percent < 20:
                    logging.info("Low battery - enabling power saving")
                    self.power_manager.set_power_profile("powersave")
                elif battery_percent < 50:
                    self.power_manager.set_power_profile("balanced")
                return

            # Check performance conditions
            if not report["throttling"]["cpu_throttled"]:
                # If system is cool and on AC power, allow performance mode
                self.power_manager.set_power_profile("performance")

        except Exception as e:
            logging.error(f"Error applying optimizations: {e}")

class TunixSystemControl:
    def __init__(self):
        self.metrics_dir = Path("/var/log/tunix/metrics")
        self.analysis_dir = Path("/var/log/tunix/analysis")
        self.config_dir = Path("/etc/tunix/config")

    def run_dashboard(self, stdscr):
        """Run interactive system dashboard"""
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        
        while True:
            try:
                stdscr.clear()
                
                # Get current data
                metrics = self._get_current_metrics()
                analysis = self._get_latest_analysis()
                
                # Display sections
                self._display_header(stdscr, 0)
                self._display_system_status(stdscr, metrics, 2)
                self._display_performance_analysis(stdscr, analysis, 12)
                self._display_recommendations(stdscr, analysis, 18)
                self._display_controls(stdscr, 23)
                
                stdscr.refresh()
                
                # Handle input
                c = stdscr.getch()
                if c == ord('q'):
                    break
                elif c == ord('r'):
                    self._apply_recommendations(analysis)
                elif c == ord('o'):
                    self._optimize_system()
                elif c == ord('c'):
                    self._configure_system()
                
                time.sleep(1)
                
            except Exception as e:
                self._handle_error(str(e))

    def _display_header(self, stdscr, y: int):
        """Display dashboard header"""
        width = curses.COLS - 1
        header = "TUNIX System Control"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        stdscr.addstr(y, 0, "=" * width)
        stdscr.addstr(y + 1, (width - len(header)) // 2, header, curses.A_BOLD)
        stdscr.addstr(y + 1, width - len(timestamp), timestamp)
        stdscr.addstr(y + 2, 0, "=" * width)

    def _display_system_status(self, stdscr, metrics: Dict, y: int):
        """Display current system status"""
        if not metrics:
            stdscr.addstr(y, 0, "No system metrics available")
            return
        
        stdscr.addstr(y, 0, "System Status:", curses.A_BOLD)
        
        # CPU Status
        if "cpu" in metrics:
            cpu_usage = metrics["cpu"].get("usage_percent", [0])[0]
            color = self._get_status_color(cpu_usage, 80, 90)
            stdscr.addstr(y + 1, 2, f"CPU Usage: {cpu_usage:.1f}%", color)
        
        # Memory Status
        if "memory" in metrics:
            mem_usage = metrics["memory"].get("percent", 0)
            color = self._get_status_color(mem_usage, 80, 90)
            stdscr.addstr(y + 2, 2, f"Memory Usage: {mem_usage:.1f}%", color)
        
        # Temperature
        if "temperature" in metrics:
            temps = []
            for sensor in metrics["temperature"].values():
                if isinstance(sensor, list):
                    for reading in sensor:
                        if isinstance(reading, dict):
                            temps.append(reading.get("current", 0))
            if temps:
                max_temp = max(temps)
                color = self._get_status_color(max_temp, 75, 85)
                stdscr.addstr(y + 3, 2, f"Temperature: {max_temp:.1f}°C", color)
        
        # Power Status
        if "power" in metrics:
            power = metrics["power"]
            if isinstance(power, dict):
                on_battery = not power.get("power_plugged", True)
                battery_level = power.get("percent", 100)
                color = self._get_status_color(battery_level, 30, 15, reverse=True)
                status = "Battery" if on_battery else "AC Power"
                if on_battery:
                    status += f" ({battery_level}%)"
                stdscr.addstr(y + 4, 2, f"Power: {status}", color)

    def _display_performance_analysis(self, stdscr, analysis: Dict, y: int):
        """Display performance analysis results"""
        if not analysis:
            stdscr.addstr(y, 0, "No performance analysis available")
            return
        
        stdscr.addstr(y, 0, "Performance Analysis:", curses.A_BOLD)
        
        # Display trends
        if "trends" in analysis:
            y_offset = 1
            for metric, trend in analysis["trends"].items():
                direction = trend.get("direction", "stable")
                if direction != "stable":
                    color = (curses.color_pair(3) if direction == "increasing" 
                            else curses.color_pair(1))
                    stdscr.addstr(
                        y + y_offset, 2,
                        f"{metric}: {direction.capitalize()}",
                        color
                    )
                    y_offset += 1

    def _display_recommendations(self, stdscr, analysis: Dict, y: int):
        """Display system recommendations"""
        if not analysis or "recommendations" not in analysis:
            stdscr.addstr(y, 0, "No recommendations available")
            return
        
        stdscr.addstr(y, 0, "Recommendations:", curses.A_BOLD)
        
        y_offset = 1
        for rec in analysis["recommendations"]:
            severity = rec.get("severity", "low")
            color = self._get_severity_color(severity)
            stdscr.addstr(
                y + y_offset, 2,
                f"[{severity.upper()}] {rec.get('issue', '')}: {rec.get('action', '')}",
                color
            )
            y_offset += 1

    def _display_controls(self, stdscr, y: int):
        """Display available controls"""
        controls = [
            ("q", "Quit"),
            ("r", "Apply Recommendations"),
            ("o", "Optimize System"),
            ("c", "Configure")
        ]
        
        stdscr.addstr(y, 0, "Controls:", curses.A_BOLD)
        x = 2
        for key, action in controls:
            text = f"[{key}] {action}"
            stdscr.addstr(y + 1, x, text)
            x += len(text) + 3

    def _get_status_color(self, value: float, warn: float, crit: float, 
                         reverse: bool = False) -> int:
        """Get color pair based on status thresholds"""
        if reverse:
            value = 100 - value
            warn = 100 - warn
            crit = 100 - crit
            
        if value >= crit:
            return curses.color_pair(3)
        elif value >= warn:
            return curses.color_pair(2)
        return curses.color_pair(1)

    def _get_severity_color(self, severity: str) -> int:
        """Get color pair based on severity"""
        if severity == "critical":
            return curses.color_pair(3)
        elif severity == "high":
            return curses.color_pair(2)
        return curses.color_pair(1)

    def _get_current_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            metrics_file = self.metrics_dir / "current_metrics.json"
            if metrics_file.exists():
                with open(metrics_file) as f:
                    return json.load(f)
        except Exception as e:
            self._handle_error(f"Error reading metrics: {e}")
        return {}

    def _get_latest_analysis(self) -> Dict:
        """Get latest performance analysis"""
        try:
            analysis_file = self.analysis_dir / "latest_analysis.json"
            if analysis_file.exists():
                with open(analysis_file) as f:
                    return json.load(f)
        except Exception as e:
            self._handle_error(f"Error reading analysis: {e}")
        return {}

    def _apply_recommendations(self, analysis: Dict):
        """Apply recommended optimizations"""
        try:
            if "recommendations" in analysis:
                for rec in analysis["recommendations"]:
                    component = rec.get("component")
                    action = rec.get("action")
                    
                    if component == "cpu":
                        self._optimize_cpu()
                    elif component == "memory":
                        self._optimize_memory()
                    elif component == "thermal":
                        self._optimize_thermal()
        except Exception as e:
            self._handle_error(f"Error applying recommendations: {e}")

    def _optimize_system(self):
        """Trigger system-wide optimization"""
        try:
            # Signal the coordinator to run optimization
            Path("/var/run/tunix/optimize").touch()
        except Exception as e:
            self._handle_error(f"Error triggering optimization: {e}")

    def _configure_system(self):
        """Configure system settings"""
        try:
            # Launch configuration interface
            curses.endwin()
            self._run_config_interface()
            curses.doupdate()
        except Exception as e:
            self._handle_error(f"Error in configuration: {e}")

    def _optimize_cpu(self):
        """Apply CPU optimizations"""
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", 'w') as f:
                f.write("performance")
        except Exception as e:
            self._handle_error(f"Error optimizing CPU: {e}")

    def _optimize_memory(self):
        """Apply memory optimizations"""
        try:
            with open("/proc/sys/vm/swappiness", 'w') as f:
                f.write("60")
            with open("/proc/sys/vm/vfs_cache_pressure", 'w') as f:
                f.write("50")
        except Exception as e:
            self._handle_error(f"Error optimizing memory: {e}")

    def _optimize_thermal(self):
        """Apply thermal optimizations"""
        try:
            # Signal thermal service to optimize
            Path("/var/run/tunix/thermal_optimize").touch()
        except Exception as e:
            self._handle_error(f"Error optimizing thermal: {e}")

    def _handle_error(self, error: str):
        """Handle and log errors"""
        with open("/var/log/tunix/system_control.log", 'a') as f:
            f.write(f"{datetime.now()}: {error}\n")

def main():
    parser = argparse.ArgumentParser(description='TUNIX System Control')
    parser.add_argument('--no-ui', action='store_true', help='Run without UI')
    args = parser.parse_args()
    
    control = TunixSystemControl()
    
    if args.no_ui:
        # Run one-time optimization
        control._optimize_system()
    else:
        # Run interactive dashboard
        curses.wrapper(control.run_dashboard)

if __name__ == "__main__":
    main()