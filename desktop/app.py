"""
CrashSense — Main Application Entry Point
==========================================

Orchestrates the entire desktop application lifecycle:
    1. Initialises the CustomTkinter window and dark theme.
    2. Manages the **authentication flow** (Login ↔ SignUp ↔ Main Dashboard).
    3. Handles **screen navigation** via sidebar — each navigation event
       destroys the old screen widget and lazily creates the new one to keep
       memory usage minimal.
    4. Provides a unified logout handler that tears down the current session
       and returns to the login screen.

Architecture:
    ┌────────────────────────────────────────────────────────────┐
    │  CrashSenseApp (CTk root window)                          │
    │  ├── LoginScreen   ← shown first                          │
    │  ├── SignUpScreen   ← shown when user clicks "Sign Up"    │
    │  └── _main_frame    ← shown after successful login        │
    │       ├── Sidebar   (left, fixed 260px)                   │
    │       └── right_panel                                     │
    │            ├── TopBar   (top, fixed 72px)                 │
    │            └── _content_frame  (fills remaining space)    │
    │                 └── <ActiveScreen>  (lazy-loaded)         │
    └────────────────────────────────────────────────────────────┘

Usage:
    python desktop/app.py          # Direct execution
    ./crash_sense.sh               # Via the universal launcher
"""

import sys
import os

# ── Ensure the project root is on sys.path ──────────────────────
# This allows `from backend.core.collector import SystemMonitor`
# to work regardless of the working directory at launch time.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import customtkinter as ctk
from PIL import Image, ImageTk

# ── Internal imports ────────────────────────────────────────────
from desktop.theme import BG_ROOT, FONT_FAMILY
from desktop.components.sidebar import Sidebar
from desktop.components.topbar import TopBar
from desktop.screens.login import LoginScreen
from desktop.screens.signup import SignUpScreen
from desktop.screens.dashboard import DashboardScreen
from desktop.screens.alerts import AlertsScreen
from desktop.screens.crash_details import CrashDetailsScreen
from desktop.screens.logs import LogsScreen
from desktop.screens.prediction import PredictionScreen
from desktop.screens.settings import SettingsScreen


class CrashSenseApp(ctk.CTk):
    """
    Root application window.

    Responsibilities:
        - Window configuration (title, geometry, dark theme)
        - Authentication flow management (login ↔ signup ↔ main)
        - Screen lifecycle management (create / destroy on navigation)

    Attributes:
        _current_screen_id (str):           Active screen identifier (e.g. 'dashboard').
        _current_screen_widget (CTkFrame):  Reference to the currently displayed screen
                                            widget; destroyed on every navigation event.
    """

    def __init__(self):
        super().__init__()

        # ── Window configuration ────────────────────────────────
        self.title("CrashSense — App Crash Detection & Prediction System")
        self.geometry("1280x800")
        self.minsize(1024, 640)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG_ROOT)

        # ── Set window icon ─────────────────────────────────────
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            icon_img = Image.open(icon_path)
            self._icon_photo = ImageTk.PhotoImage(icon_img)
            self.iconphoto(True, self._icon_photo)

        # Track which screen is currently visible
        self._current_screen_id = "dashboard"
        self._current_screen_widget = None

        # ── Auth screens (created once, toggled with pack/pack_forget) ──
        self._login_screen = LoginScreen(
            self,
            on_login=self._handle_login,
            on_signup=self._show_signup,
        )
        self._signup_screen = SignUpScreen(
            self,
            on_signup=self._handle_login,        # Successful signup → enter app
            on_back_to_login=self._show_login,
        )

        # ── Main layout container (sidebar + right panel) ───────
        self._main_frame = ctk.CTkFrame(self, fg_color=BG_ROOT, corner_radius=0)

        # Left sidebar — persistent navigation
        self._sidebar = Sidebar(
            self._main_frame,
            on_navigate=self._navigate,
            on_logout=self._handle_logout,
        )
        self._sidebar.pack(side="left", fill="y")

        # Right panel — top bar + dynamic content area
        right = ctk.CTkFrame(self._main_frame, fg_color=BG_ROOT, corner_radius=0)
        right.pack(side="right", fill="both", expand=True)

        self._topbar = TopBar(
            right,
            on_logout=self._handle_logout,
            on_back=self._go_dashboard,
        )
        self._topbar.pack(fill="x")

        # Content area — screens are placed here
        self._content_frame = ctk.CTkFrame(right, fg_color=BG_ROOT, corner_radius=0)
        self._content_frame.pack(fill="both", expand=True)

        # ── Start with the login screen ─────────────────────────
        self._show_login()

    # ═══════════════════════════════════════════════════════════
    #  AUTHENTICATION FLOW
    # ═══════════════════════════════════════════════════════════

    def _show_login(self):
        """Display the login screen, hiding all other views."""
        self._signup_screen.pack_forget()
        self._main_frame.pack_forget()
        self._login_screen.pack(fill="both", expand=True)

    def _show_signup(self):
        """Display the sign-up screen, hiding all other views."""
        self._login_screen.pack_forget()
        self._main_frame.pack_forget()
        self._signup_screen.pack(fill="both", expand=True)

    def _handle_login(self):
        """
        Callback triggered on successful login or 'Demo Mode'.
        Hides auth screens and shows the main dashboard layout.
        """
        self._login_screen.pack_forget()
        self._signup_screen.pack_forget()
        self._main_frame.pack(fill="both", expand=True)
        self._navigate("dashboard")

    def _handle_logout(self):
        """
        End the current session.
        Destroys the active screen widget to free memory, hides the main
        layout, and returns to the login screen.
        """
        if self._current_screen_widget:
            self._current_screen_widget.destroy()
            self._current_screen_widget = None
        self._main_frame.pack_forget()
        self._show_login()

    # ═══════════════════════════════════════════════════════════
    #  SCREEN NAVIGATION
    # ═══════════════════════════════════════════════════════════

    def _go_dashboard(self):
        """Navigate back to the dashboard (used by the top-bar back button)."""
        self._navigate("dashboard")
        self._sidebar.set_active("dashboard")

    def _navigate(self, screen_id: str):
        """
        Switch to a different screen.

        Args:
            screen_id: One of 'dashboard', 'alerts', 'crash-details',
                       'logs', 'prediction', 'settings'.

        The previous screen widget is destroyed before the new one is created.
        This ensures only one screen's widgets exist in memory at a time.
        """
        # Tear down the previous screen
        if self._current_screen_widget:
            self._current_screen_widget.destroy()
            self._current_screen_widget = None

        self._current_screen_id = screen_id

        # Update the top bar title and back-button visibility
        self._topbar.set_screen(screen_id)

        # Highlight the active item in the sidebar
        self._sidebar.set_active(screen_id)

        # Lazy-create the requested screen via a factory map
        screen_factories = {
            "dashboard":     lambda: DashboardScreen(self._content_frame),
            "alerts":        lambda: AlertsScreen(self._content_frame),
            "crash-details": lambda: CrashDetailsScreen(self._content_frame),
            "logs":          lambda: LogsScreen(self._content_frame),
            "prediction":    lambda: PredictionScreen(self._content_frame),
            "settings":      lambda: SettingsScreen(self._content_frame, on_logout=self._handle_logout),
        }

        factory = screen_factories.get(screen_id, screen_factories["dashboard"])
        self._current_screen_widget = factory()
        self._current_screen_widget.pack(fill="both", expand=True)


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    """Create and run the CrashSense desktop application."""
    app = CrashSenseApp()
    app.mainloop()


if __name__ == "__main__":
    main()
