"""
CrashSense — System Tray Icon (Background Daemon)
=================================================

Provides a system tray icon using `pystray`. Enables CrashSense to run
in the background (headless) when the main UI window is closed.

Features:
  - "Open Dashboard" restores the main UI.
  - "Quit" gracefully exits the entire application tree.
"""

import sys
import os
import threading
from PIL import Image
import pystray

def get_asset_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If running as a normal python script, use the project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

class SystemTrayManager:
    """Manages the pystray background icon and menu lifecycle."""
    
    def __init__(self, app_instance, icon_path: str):
        self.app = app_instance
        self.icon_path = get_asset_path(icon_path) if not os.path.isabs(icon_path) else icon_path
        self._icon = None
        
        # We need a PIL Image for pystray
        try:
            self.image = Image.open(icon_path)
        except Exception:
            # Fallback to a solid color block if icon missing
            self.image = Image.new('RGB', (64, 64), color=(30, 32, 40))

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Open Dashboard", self._on_restore, default=True),
            pystray.MenuItem("Quit CrashSense", self._on_quit)
        )

    def start_in_background(self):
        """Starts the tray icon loop in a background daemon thread."""
        def run_tray():
            self._icon = pystray.Icon(
                "CrashSense",
                self.image,
                "CrashSense - Monitoring in background",
                menu=self._build_menu()
            )
            self._icon.run()
            
        threading.Thread(target=run_tray, daemon=True).start()

    def _on_restore(self, icon, item):
        """Called when user clicks 'Open Dashboard'."""
        # Must restore the Tkinter window from the main thread
        self.app.after(0, self.app.restore_window)

    def _on_quit(self, icon, item):
        """Called when user clicks 'Quit'."""
        # Tell pystray to stop blocking
        icon.stop()
        # Tell CustomTkinter to shut down the main loop completely
        self.app.after(0, self.app.full_quit)
