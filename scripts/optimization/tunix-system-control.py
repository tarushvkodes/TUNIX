#!/usr/bin/python3

import sys
import json
import argparse
import subprocess
from typing import Optional
from pathlib import Path

# Add the installer package to Python path
repo_root = Path(__file__).parent.parent.parent
sys.path.append(str(repo_root))
from installer.modules.hardware_detection import HardwareDetector
from system_diagnostics import SystemDiagnostics

class TunixSystemControl:
    def __init__(self):
        self.hardware_detector = HardwareDetector()
        self.diagnostics = SystemDiagnostics()
        self.base_dir = Path('/etc/tunix')
        self.base_dir.mkdir(exist_ok=True)

    def detect_hardware(self, output_file: Optional[str] = None) -> None:
        """Run hardware detection and save results"""
        results = self.hardware_detector.detect_all()
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        else:
            print(json.dumps(results, indent=2))

    def run_diagnostics(self, output_file: Optional[str] = None) -> None:
        """Run system diagnostics and save results"""
        results = self.diagnostics.run_diagnostics()
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        else:
            print(json.dumps(results, f, indent=2))

    def optimize_system(self) -> None:
        """Run system optimization"""
        subprocess.run(['/usr/share/tunix/scripts/optimization/optimize-system.sh'])

    def generate_report(self, output_file: Optional[str] = None) -> None:
        """Generate a comprehensive system report"""
        report = {
            "hardware_profile": self.hardware_detector.detect_all(),
            "system_diagnostics": self.diagnostics.run_diagnostics(),
            "recommendations": []
        }

        # Generate recommendations based on findings
        if report["system_diagnostics"].get("error_log"):
            report["recommendations"].append(
                "System errors detected - check error logs for details"
            )

        perf_metrics = report["system_diagnostics"].get("performance_metrics", {})
        if perf_metrics:
            if perf_metrics.get("memory", {}).get("used_percent", 0) > 85:
                report["recommendations"].append(
                    "High memory usage detected - consider upgrading RAM"
                )
            if perf_metrics.get("disk", {}).get("io_wait", 0) > 15:
                report["recommendations"].append(
                    "High disk I/O wait detected - consider SSD upgrade"
                )

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
        else:
            print(json.dumps(report, indent=2))

def main():
    parser = argparse.ArgumentParser(description='TUNIX System Control Utility')
    parser.add_argument('action', choices=['detect', 'diagnose', 'optimize', 'report'],
                       help='Action to perform')
    parser.add_argument('--output', '-o', help='Output file for results')
    
    args = parser.parse_args()
    control = TunixSystemControl()
    
    try:
        if args.action == 'detect':
            control.detect_hardware(args.output)
        elif args.action == 'diagnose':
            control.run_diagnostics(args.output)
        elif args.action == 'optimize':
            control.optimize_system()
        elif args.action == 'report':
            control.generate_report(args.output)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()