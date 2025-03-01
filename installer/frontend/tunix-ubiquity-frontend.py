#!/usr/bin/env python3

import os
import sys

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk, GLib, Gdk
except ImportError:
    print("Error: PyGObject (GTK4) is required. Please install python3-gi and gir1.2-gtk-4.0", file=sys.stderr)
    sys.exit(1)

try:
    from ubiquity.frontend.gtk_ui import GtkUI
    from ubiquity import misc
except ImportError:
    print("Error: Ubiquity is required. This module should be run in the Ubuntu installer environment.", file=sys.stderr)
    sys.exit(1)

class TunixUI(GtkUI):
    def __init__(self):
        super().__init__()
        self.tunix_branding = True
        self.custom_theme = True
        self.pages = []  # Initialize pages list

    def setup_branding(self):
        # Load TUNIX branding
        logo_path = '/usr/share/tunix/branding/tunixlogo.png'
        if os.path.exists(logo_path):
            self.logo.set_from_file(logo_path)
        
        # Set TUNIX colors and styling
        style_provider = Gtk.CssProvider()
        style_provider.load_from_path('/usr/share/tunix/themes/TUNIX-Light/gtk-4.0/gtk.css')
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def setup_custom_pages(self):
        # Add TUNIX-specific installer pages
        self.add_theme_selection_page()
        self.add_software_bundle_page()
        self.add_hardware_detection_page()

    def add_theme_selection_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(20)

        # Theme selection options
        theme_label = Gtk.Label(label="Choose your preferred theme:")
        theme_combo = Gtk.ComboBoxText()
        theme_combo.append_text("TUNIX Light")
        theme_combo.append_text("TUNIX Dark")
        theme_combo.set_active(0)

        page.pack_start(theme_label, False, False, 0)
        page.pack_start(theme_combo, False, False, 0)
        self.pages.append(page)

    def add_software_bundle_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(20)

        # Software bundle selection
        bundles = [
            ("Productivity", "Office suite, email client, and productivity tools"),
            ("Development", "Programming IDEs, version control, and dev tools"),
            ("Multimedia", "Video/audio players, editors, and creative tools"),
            ("Gaming", "Steam, Lutris, and gaming optimizations")
        ]

        for name, desc in bundles:
            check = Gtk.CheckButton(label=f"{name}: {desc}")
            page.pack_start(check, False, False, 0)

        self.pages.append(page)

    def add_hardware_detection_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_border_width(20)

        # Hardware detection results
        hardware_label = Gtk.Label(
            label="Detected Hardware:\n" +
            "Click 'Configure' to customize settings for each component"
        )
        page.pack_start(hardware_label, False, False, 0)

        # Add hardware configuration buttons
        components = ["Graphics", "Audio", "Network", "Printer"]
        for comp in components:
            button = Gtk.Button(label=f"Configure {comp}")
            page.pack_start(button, False, False, 0)

        self.pages.append(page)