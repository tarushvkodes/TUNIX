#!/usr/bin/python3
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from system_monitor import SystemMonitor

def main():
    parser = argparse.ArgumentParser(description='TUNIX System Monitor')
    parser.add_argument('--daemon', action='store_true', help='Run as a background service')
    parser.add_argument('--export', help='Export system stats to specified JSON file')
    parser.add_argument('--watch', type=int, metavar='SECONDS', help='Watch mode with specified refresh interval')
    args = parser.parse_args()

    monitor = SystemMonitor()
    
    if args.daemon:
        # Run in daemon mode
        import daemon
        with daemon.DaemonContext():
            monitor.start()
    elif args.export:
        # Export current stats to JSON
        stats = monitor.get_current_stats()
        with open(args.export, 'w') as f:
            json.dump(stats, f, indent=2)
    elif args.watch:
        # Run in watch mode with specified interval
        monitor.set_update_interval(args.watch)
        monitor.start()
    else:
        # Run in interactive mode
        monitor.start()

if __name__ == "__main__":
    main()