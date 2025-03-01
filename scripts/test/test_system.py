#!/usr/bin/env python3

import unittest
import subprocess
import os
import sys
import json
import shutil
import platform
from typing import List, Dict
from pathlib import Path

from hardware_detection import HardwareDetector

@unittest.skipUnless(platform.system() == 'Linux', "Tests require Linux")
class TunixSystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.geteuid() != 0:
            raise PermissionError("Tests must be run as root")
        
        cls.test_dir = "/tmp/tunix-test"
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # Add the TUNIX modules to Python path
        cls.tunix_path = Path("/usr/share/tunix")
        if not cls.tunix_path.exists():
            cls.tunix_path = Path(__file__).parent.parent.parent

    def test_system_packages(self):
        """Test that all required packages are installed"""
        with open("/usr/share/tunix/custom-packages/package-list.txt", "r") as f:
            required_packages = [
                line.strip() for line in f
                if line.strip() and not line.startswith("#")
            ]
        
        for package in required_packages:
            result = subprocess.run(
                ["dpkg", "-l", package],
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0, f"Package {package} not installed")

    def test_theme_installation(self):
        """Test theme files are properly installed"""
        theme_paths = [
            "/usr/share/themes/TUNIX-Light",
            "/usr/share/themes/TUNIX-Light/gtk-4.0",
            "/usr/share/themes/TUNIX-Light/gtk-4.0/gtk.css",
            "/usr/share/themes/TUNIX-Light/gtk-4.0/colors.css"
        ]
        for path in theme_paths:
            self.assertTrue(os.path.exists(path), f"Theme path {path} not found")

    def test_plymouth_theme(self):
        """Test Plymouth theme installation"""
        plymouth_paths = [
            "/usr/share/plymouth/themes/tunix/tunix.plymouth",
            "/usr/share/plymouth/themes/tunix/tunix.script"
        ]
        for path in plymouth_paths:
            self.assertTrue(os.path.exists(path), f"Plymouth theme file {path} not found")

    def test_hardware_detection(self):
        """Test hardware detection module"""
        detector = HardwareDetector()
        hw_info = detector.detect_all()
        
        self.assertIsInstance(hw_info, dict)
        self.assertIn('gpu', hw_info)
        self.assertIn('audio', hw_info)
        self.assertIn('network', hw_info)
        self.assertNotIn('error', hw_info)

    def test_system_optimization(self):
        """Test system optimization settings"""
        # Test swappiness
        with open("/proc/sys/vm/swappiness", "r") as f:
            swappiness = int(f.read().strip())
        self.assertLessEqual(swappiness, 10)
        
        # Test I/O scheduler for SSDs
        scheduler_path = "/sys/block/sda/queue/scheduler"
        if os.path.exists(scheduler_path):
            with open(scheduler_path, "r") as f:
                scheduler = f.read().strip()
            self.assertIn("[mq-deadline]", scheduler)

    def test_dconf_settings(self):
        """Test GNOME/dconf settings"""
        test_settings = {
            "/org/gnome/desktop/interface/enable-animations": "true",
            "/org/gnome/desktop/interface/font-name": "'Noto Sans 10'",
            "/org/gnome/desktop/wm/preferences/button-layout": "'close,minimize,maximize:appmenu'"
        }
        
        for key, expected in test_settings.items():
            result = subprocess.run(
                ["gsettings", "get", key],
                capture_output=True,
                text=True
            )
            self.assertEqual(result.stdout.strip(), expected)

    def test_installer_components(self):
        """Test installer component availability"""
        installer_paths = [
            "/usr/share/tunix/installer/frontend/tunix-ubiquity-frontend.py",
            "/usr/share/tunix/installer/modules/hardware_detection.py",
            "/usr/share/tunix/installer/data/hardware_compatibility.json"
        ]
        for path in installer_paths:
            self.assertTrue(os.path.exists(path), f"Installer component {path} not found")

    def test_security_settings(self):
        """Test security configurations"""
        # Test firewall status
        result = subprocess.run(
            ["ufw", "status"],
            capture_output=True,
            text=True
        )
        self.assertIn("Status: active", result.stdout)
        
        # Test SSH configuration
        with open("/etc/ssh/sshd_config", "r") as f:
            ssh_config = f.read()
        self.assertIn("PermitRootLogin no", ssh_config)

    def test_dummy(self):
        # Dummy test to ensure test discovery works
        self.assertTrue(True)

    @classmethod
    def tearDownClass(cls):
        # Clean up test directory
        shutil.rmtree(cls.test_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main(verbosity=2)