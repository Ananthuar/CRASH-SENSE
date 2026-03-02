import os
import sys
import shutil

def create_desktop_shortcut():
    """
    Creates a .desktop application menu shortcut for the CrashSense application
    so users can easily launch it from their GNOME/KDE menus.
    """
    if sys.platform != "linux":
        return

    try:
        # Determine the absolute path of the running executable
        binary_path = os.path.abspath(sys.argv[0])

        # Define permanent user directories for desktop integration
        user_icons_dir = os.path.expanduser("~/.local/share/icons")
        user_apps_dir = os.path.expanduser("~/.local/share/applications")

        # Ensure target directories exist
        os.makedirs(user_icons_dir, exist_ok=True)
        os.makedirs(user_apps_dir, exist_ok=True)

        # Extract Icon since PyInstaller bundles it internally, 
        # and standard Linux launchers need it visible on the hard drive
        from desktop.app import get_asset_path
        bundled_icon = get_asset_path("desktop/assets/icon.png")
        target_icon = os.path.join(user_icons_dir, "crashsense.png")

        if os.path.exists(bundled_icon):
            shutil.copyfile(bundled_icon, target_icon)
        else:
            target_icon = "utilities-system-monitor" # System fallback

        # Generate the .desktop shortcut content
        desktop_entry = f"""[Desktop Entry]
Name=CrashSense
Comment=AI Predictive Resolution Engine
Exec="{binary_path}"
Icon="{target_icon}"
Terminal=false
Type=Application
Categories=System;Monitor;Utility;
"""

        # Save to the user's application menu directory
        desktop_file = os.path.join(user_apps_dir, "CrashSense.desktop")
        
        with open(desktop_file, "w") as f:
            f.write(desktop_entry)

        # Ensure the .desktop file is executable
        os.chmod(desktop_file, 0o755)
        
    except Exception as e:
        print(f"[CrashSense] Failed to create desktop shortcut: {e}")
