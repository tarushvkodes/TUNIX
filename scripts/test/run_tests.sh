#!/bin/bash

# TUNIX Test Runner
# Copyright © Tarushv Kosgi 2025

set -e

LOG_DIR="/var/log/tunix/tests"
REPORT_DIR="/var/www/tunix/test-reports"
TEST_TIMEOUT=3600  # 1 hour timeout

# Ensure we're root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Create directories
mkdir -p "$LOG_DIR" "$REPORT_DIR"

# Initialize log file
LOG_FILE="$LOG_DIR/test-run-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG_FILE"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

run_system_tests() {
    log_message "Running system tests..."
    timeout $TEST_TIMEOUT python3 test_system.py --verbose 2>&1 | tee -a "$LOG_FILE"
}

run_multimedia_tests() {
    log_message "Running multimedia subsystem tests..."
    python3 /usr/share/tunix/scripts/test/test_multimedia.py | tee -a "$LOG_FILE"
}

check_desktop_environment() {
    log_message "Checking desktop environment..."
    
    # Check GNOME Shell
    if ! pgrep -f "gnome-shell" > /dev/null; then
        log_message "ERROR: GNOME Shell is not running"
        return 1
    fi
    
    # Check critical services
    SERVICES="gdm systemd-logind NetworkManager"
    for service in $SERVICES; do
        if ! systemctl is-active "$service" > /dev/null; then
            log_message "ERROR: $service is not running"
            return 1
        fi
    done
}

check_hardware_support() {
    log_message "Checking hardware support..."
    
    # Check graphics
    if lspci | grep -i "VGA" | grep -qi "nvidia"; then
        if ! lsmod | grep -q "nvidia"; then
            log_message "WARNING: NVIDIA GPU detected but driver not loaded"
        fi
    fi
    
    # Check audio
    if ! pulseaudio --check; then
        log_message "ERROR: PulseAudio is not running"
        return 1
    fi
}

generate_report() {
    log_message "Generating test report..."
    
    REPORT_FILE="$REPORT_DIR/report-$(date +%Y%m%d-%H%M%S).html"
    
    # Create HTML report
    cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>TUNIX Test Report - $(date)</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; }
        .pass { color: green; }
        .fail { color: red; }
        .warn { color: orange; }
    </style>
</head>
<body>
    <h1>TUNIX Test Report</h1>
    <p>Generated: $(date)</p>
    <h2>Test Results</h2>
    <pre>$(cat "$LOG_FILE")</pre>
</body>
</html>
EOF
}

cleanup_old_reports() {
    # Keep only last 10 reports
    cd "$REPORT_DIR" && ls -t | tail -n +11 | xargs -r rm
    cd "$LOG_DIR" && ls -t | tail -n +11 | xargs -r rm
}

main() {
    log_message "Starting TUNIX test suite"
    
    # Run all tests
    check_desktop_environment
    check_hardware_support
    run_system_tests
    run_multimedia_tests
    
    # Generate and clean up reports
    generate_report
    cleanup_old_reports
    
    log_message "Testing completed. Report available at: $REPORT_DIR"
}

main