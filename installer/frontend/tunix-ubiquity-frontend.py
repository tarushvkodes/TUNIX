#!/usr/bin/python3
import sys
import os
import platform
from pathlib import Path
import json
from typing import Dict, List, Tuple

if platform.system() != 'Linux':
    print("ERROR: This installer can only run on Linux systems")
    print(f"Current platform: {platform.system()}")
    print("\nNote: You can still develop and test other TUNIX components on non-Linux systems.")
    sys.exit(1)

def check_dependencies():
    """Check for required system dependencies"""
    missing_deps = []
    
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GLib
    except ImportError as e:
        missing_deps.append('python3-gi')
    except ValueError as e:
        missing_deps.append('gir1.2-gtk-3.0')
        
    if missing_deps:
        print("ERROR: Missing required dependencies:")
        print("\nTo install on Ubuntu/Debian:")
        print("sudo apt-get install " + " ".join(missing_deps))
        print("\nTo install on Fedora:")
        print("sudo dnf install " + " ".join(dep.replace('python3-gi', 'python3-gobject') for dep in missing_deps))
        print("\nTo install on Arch Linux:")
        print("sudo pacman -S " + " ".join(dep.replace('python3-gi', 'python-gobject') for dep in missing_deps))
        sys.exit(1)

    return gi, Gtk, GLib

# Check dependencies before proceeding
gi, Gtk, GLib = check_dependencies()

# Add the installer package to Python path
repo_root = Path(__file__).parent.parent.parent
sys.path.append(str(repo_root))
from installer.modules.hardware_detection import HardwareDetector

class TunixInstallerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="TUNIX Installer")
        self.set_default_size(800, 600)
        self.hardware_detector = HardwareDetector()
        
        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.main_box)
        
        # Header
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "TUNIX Installer"
        self.set_titlebar(header)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.main_box.pack_start(self.progress_bar, False, False, 0)
        
        # Stack for different pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_box.pack_start(self.stack, True, True, 0)
        
        # Stack switcher
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self.stack)
        header.set_custom_title(stack_switcher)
        
        # Create pages
        self.create_welcome_page()
        self.create_hardware_check_page()
        self.create_install_options_page()
        
        # Navigation buttons
        self.nav_box = Gtk.Box(spacing=6)
        self.main_box.pack_end(self.nav_box, False, False, 0)
        
        self.back_button = Gtk.Button.new_with_label("Back")
        self.back_button.connect("clicked", self.on_back_clicked)
        self.nav_box.pack_start(self.back_button, False, False, 0)
        
        self.next_button = Gtk.Button.new_with_label("Next")
        self.next_button.connect("clicked", self.on_next_clicked)
        self.nav_box.pack_end(self.next_button, False, False, 0)
        
        self.current_page = 0
        self.update_navigation()

    def create_welcome_page(self):
        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        welcome_box.set_margin_start(20)
        welcome_box.set_margin_end(20)
        
        # Welcome text
        welcome_label = Gtk.Label()
        welcome_label.set_markup(
            "<span size='xx-large'>Welcome to TUNIX</span>\n\n"
            "TUNIX will now check your system compatibility\n"
            "and configure optimal settings for your hardware."
        )
        welcome_box.pack_start(welcome_label, True, True, 0)
        
        self.stack.add_titled(welcome_box, "welcome", "Welcome")

    def create_hardware_check_page(self):
        hardware_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hardware_box.set_margin_start(20)
        hardware_box.set_margin_end(20)
        
        # Hardware detection status
        self.hardware_status = Gtk.Label()
        self.hardware_status.set_markup("<span size='large'>Checking hardware compatibility...</span>")
        hardware_box.pack_start(self.hardware_status, False, False, 0)
        
        # Hardware details
        self.hardware_details = Gtk.TextView()
        self.hardware_details.set_editable(False)
        self.hardware_details.set_wrap_mode(Gtk.WrapMode.WORD)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.hardware_details)
        hardware_box.pack_start(scroll, True, True, 0)
        
        # Recommendations
        self.recommendations_label = Gtk.Label()
        self.recommendations_label.set_markup("<span size='large'>Recommendations</span>")
        hardware_box.pack_start(self.recommendations_label, False, False, 0)
        
        self.recommendations_view = Gtk.TextView()
        self.recommendations_view.set_editable(False)
        self.recommendations_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scroll2 = Gtk.ScrolledWindow()
        scroll2.add(self.recommendations_view)
        hardware_box.pack_start(scroll2, True, True, 0)
        
        self.stack.add_titled(hardware_box, "hardware", "Hardware Check")

    def create_install_options_page(self):
        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        options_box.set_margin_start(20)
        options_box.set_margin_end(20)
        
        # Performance profile selection
        profile_label = Gtk.Label()
        profile_label.set_markup("<span size='large'>Select Performance Profile</span>")
        options_box.pack_start(profile_label, False, False, 0)
        
        self.profile_combo = Gtk.ComboBoxText()
        self.profile_combo.append_text("Balanced (Recommended)")
        self.profile_combo.append_text("Performance")
        self.profile_combo.append_text("Power Saver")
        self.profile_combo.set_active(0)
        options_box.pack_start(self.profile_combo, False, False, 0)
        
        # Additional options
        self.proprietary_drivers = Gtk.CheckButton.new_with_label(
            "Install proprietary drivers (Recommended for better performance)"
        )
        self.proprietary_drivers.set_active(True)
        options_box.pack_start(self.proprietary_drivers, False, False, 10)
        
        self.stack.add_titled(options_box, "options", "Installation Options")

    def check_hardware(self):
        self.hardware_status.set_markup("<span size='large'>Detecting hardware...</span>")
        GLib.idle_add(self._do_hardware_check)

    def _do_hardware_check(self):
        # Detect hardware
        hardware_info = self.hardware_detector.detect_all()
        is_compatible, warnings, recommendations = self.hardware_detector.check_compatibility()
        
        # Update hardware details
        buffer = self.hardware_details.get_buffer()
        details_text = "Hardware Detection Results:\n\n"
        
        if 'cpu' in hardware_info:
            details_text += f"CPU: {hardware_info['cpu'].get('model', 'Unknown')}\n"
            details_text += f"Cores: {hardware_info['cpu'].get('cores', 'Unknown')}\n"
        
        if 'gpu' in hardware_info:
            details_text += "\nGraphics:\n"
            for gpu_type, info in hardware_info['gpu'].items():
                details_text += f"- {gpu_type.upper()}: {info}\n"
        
        if warnings:
            details_text += "\nWarnings:\n"
            for warning in warnings:
                details_text += f"- {warning}\n"
        
        buffer.set_text(details_text)
        
        # Update recommendations
        if recommendations:
            rec_buffer = self.recommendations_view.get_buffer()
            rec_text = "System Recommendations:\n\n"
            for component, rec in recommendations.items():
                rec_text += f"{component}: {rec}\n"
            rec_buffer.set_text(rec_text)
        
        # Update status
        if is_compatible:
            self.hardware_status.set_markup(
                "<span size='large' color='green'>✓ Your system is compatible with TUNIX</span>"
            )
            self.next_button.set_sensitive(True)
        else:
            self.hardware_status.set_markup(
                "<span size='large' color='red'>⚠ Some hardware compatibility issues detected</span>"
            )
            self.next_button.set_sensitive(False)
        
        return False

    def on_back_clicked(self, button):
        if self.current_page > 0:
            self.current_page -= 1
            self.stack.set_visible_child_name(
                ["welcome", "hardware", "options"][self.current_page]
            )
            self.update_navigation()

    def on_next_clicked(self, button):
        if self.current_page == 0:
            self.current_page += 1
            self.stack.set_visible_child_name("hardware")
            self.check_hardware()
        elif self.current_page < 2:
            self.current_page += 1
            self.stack.set_visible_child_name(
                ["welcome", "hardware", "options"][self.current_page]
            )
        self.update_navigation()

    def update_navigation(self):
        self.back_button.set_sensitive(self.current_page > 0)
        if self.current_page == 2:
            self.next_button.set_label("Install")
        else:
            self.next_button.set_label("Next")

def main():
    win = TunixInstallerWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()