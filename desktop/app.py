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
import subprocess

# ── Ensure the project root is on sys.path ──────────────────────
# This allows `from backend.core.collector import SystemMonitor`
# to work regardless of the working directory at launch time.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import customtkinter as ctk
from PIL import Image, ImageTk

def get_asset_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If running as a normal python script, use the project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

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
from desktop.screens.profile import ProfileScreen
from desktop import session
from desktop.notifier import crash_warning_notifier
from desktop.tray import SystemTrayManager
from desktop.components.notification_toast import NotificationToast


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
        self.title("CrashSense v1.1.3 — App Crash Detection & Prediction System")
        self.geometry("1280x800")
        self.minsize(1024, 640)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG_ROOT)

        # ── Set window icon ─────────────────────────────────────
        icon_path = get_asset_path("desktop/assets/icon.png")
            
        if os.path.exists(icon_path):
            icon_img = Image.open(icon_path)
            self._icon_photo = ImageTk.PhotoImage(icon_img)
            self.iconphoto(True, self._icon_photo)

        # Track which screen is currently visible
        self._current_screen_id = "dashboard"
        self._current_screen_widget = None
        self._warning_banner = None  # In-app crash warning banner

        # ── Background Daemon / System Tray ─────────────────────
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self._tray = SystemTrayManager(self, icon_path)
        self._tray.start_in_background()

        # ── Start Local Engine ──────────────────────────────────
        self._daemon_process = None
        self._start_backend_daemon()

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

        self._sidebar = Sidebar(
            self._main_frame,
            on_navigate=self._navigate,
            on_logout=self._handle_logout,
            on_quit=self.full_quit,
        )
        self._sidebar.pack(side="left", fill="y")

        # Right panel — top bar + dynamic content area
        right = ctk.CTkFrame(self._main_frame, fg_color=BG_ROOT, corner_radius=0)
        right.pack(side="right", fill="both", expand=True)

        self._topbar = TopBar(
            right,
            on_logout=self._handle_logout,
            on_back=self._go_dashboard,
            on_profile=lambda: self._navigate("profile"),
            on_alerts=lambda: self._navigate("alerts"),
        )
        self._topbar.pack(fill="x")

        # Content area — screens are placed here
        self._content_frame = ctk.CTkFrame(right, fg_color=BG_ROOT, corner_radius=0)
        self._content_frame.pack(fill="both", expand=True)

        # ── Start with the login screen ─────────────────────────
        self._show_login()

    # ═══════════════════════════════════════════════════════════
    #  BACKEND DAEMON MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def _start_backend_daemon(self):
        """
        Locate and launch the backend daemon in the background.
        If running as a compiled PyInstaller binary, it looks for the
        `crashsense-daemon` executable in the same directory.
        If running from source, it falls back to launching `backend/app.py` directly.

        Uses /api/health (always 200) to detect a running backend, not
        /api/users which requires an email param and returns 400.
        """
        import time
        import urllib.request

        # Check if the backend is already running (e.g. installed daemon from systemd)
        # NOTE: Use /api/health — it always returns 200. /api/users returns 400 without
        # the required email param and would cause a URLError, not a successful 200.
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:5000/api/health", timeout=1.5)
            if resp.getcode() == 200:
                print("[CrashSense] Backend already running — skipping daemon launch.")
                # Start the watchdog to monitor this externally-managed daemon
                self.after(10000, self._watchdog_backend)
                return
        except Exception:
            pass

        self._daemon_args = None   # store args for watchdog restarts

        if getattr(sys, 'frozen', False):
            # Running as compiled standalone executable.
            # Find the crashsense-daemon binary next to the UI binary.
            base_dir = os.path.dirname(sys.executable)
            daemon_path = os.path.join(base_dir, "crashsense-daemon")
            if os.path.exists(daemon_path):
                self._daemon_args = [daemon_path]
            else:
                print(f"[CrashSense] Warning: Expected daemon at {daemon_path} but it was not found.")
        else:
            # Running from source — use current python to launch the backend
            backend_script = os.path.join(PROJECT_ROOT, "backend", "app.py")
            if os.path.exists(backend_script):
                self._daemon_args = [sys.executable, backend_script]
            else:
                print(f"[CrashSense] Warning: Expected backend script at {backend_script} but it was not found.")

        if self._daemon_args:
            self._daemon_process = subprocess.Popen(
                self._daemon_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            # Give the backend a brief moment to boot up before showing the login screen
            time.sleep(1.5)
            # Schedule the watchdog to keep it alive
            self.after(10000, self._watchdog_backend)

    def _watchdog_backend(self):
        """
        Periodically called (every 10 s) to ensure the backend daemon is still alive.
        If it has exited unexpectedly, it is restarted automatically.
        """
        import urllib.request

        # If we own the process, check whether it died
        if self._daemon_process is not None:
            if self._daemon_process.poll() is not None:
                # Process has exited — restart it
                print("[CrashSense] Backend daemon exited unexpectedly — restarting...")
                daemon_args = getattr(self, '_daemon_args', None)
                if daemon_args:
                    try:
                        self._daemon_process = subprocess.Popen(
                            daemon_args,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL,
                        )
                        print("[CrashSense] Backend daemon restarted.")
                    except Exception as e:
                        print(f"[CrashSense] Failed to restart daemon: {e}")
        else:
            # We didn't launch the daemon (systemd manages it) — just check reachability
            try:
                resp = urllib.request.urlopen("http://127.0.0.1:5000/api/health", timeout=1.5)
                if resp.getcode() != 200:
                    print("[CrashSense] Backend health check failed — is systemd service running?")
            except Exception:
                print("[CrashSense] Backend unreachable — is the crashsense.service running?")

        # Reschedule (skip if app is shutting down)
        if not getattr(self, '_destroyed', False):
            self.after(10000, self._watchdog_backend)

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

    def _handle_login(self, user: dict = None):
        """
        Callback triggered on successful login or 'Demo Mode'.
        Accepts a user dict from auth (or None for backward compat).
        Hides auth screens and shows the main dashboard layout.
        """
        if user:
            session.set_user(user)
            uid = user.get("uid")
            if uid:
                import threading, requests
                def _sync():
                    try:
                        requests.get(f"http://127.0.0.1:5000/api/users/{uid}/settings", timeout=3)
                        requests.post(f"http://127.0.0.1:5000/api/session", json={"uid": uid}, timeout=3)
                    except Exception:
                        pass
                threading.Thread(target=_sync, daemon=True).start()

        # Start proactive crash warning notifier
        crash_warning_notifier._on_alert = self._on_crash_warning
        crash_warning_notifier.start()
        
        # Start automated resolution event polling loop
        self.after(5000, self._poll_resolution_events)

        self._topbar.update_avatar()
        self._login_screen.pack_forget()
        self._signup_screen.pack_forget()
        self._main_frame.pack(fill="both", expand=True)
        self._navigate("dashboard")

    def _handle_logout(self):
        """Prompt for confirmation before ending the current session."""
        from desktop.theme import BG_CARD, TEXT_PRIMARY, ORANGE, RED, FONT_FAMILY
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Logout Confirmation")
        dialog.geometry("400x180")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG_CARD)
        
        ctk.CTkLabel(dialog, text="Confirm Logout", font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"), text_color=TEXT_PRIMARY).pack(pady=(25, 10))
        ctk.CTkLabel(dialog, text="Are you sure you want to log out of CrashSense?", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=TEXT_PRIMARY, wraplength=350).pack(pady=(0, 25))
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        def _cancel():
            dialog.destroy()
            
        def _confirm():
            dialog.destroy()
            self._do_actual_logout()
            
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="#1a1c24", hover_color="#2a2c36", border_width=1, border_color="#3a3c46", text_color=TEXT_PRIMARY, command=_cancel, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(btn_frame, text="Log Out", fg_color=RED, hover_color="#991b1b", text_color="#fff", command=_confirm, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(side="right", expand=True, padx=10)

        dialog.transient(self)
        dialog.update_idletasks()
        
        # Center the dialog
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 180) // 2
        dialog.geometry(f"+{x}+{y}")
        
        dialog.grab_set()

    def _do_actual_logout(self):
        """End the current session and return to the login screen."""
        crash_warning_notifier.stop()
        session.clear_user()
        if self._current_screen_widget:
            self._current_screen_widget.destroy()
            self._current_screen_widget = None
        if self._warning_banner:
            try: self._warning_banner.destroy()
            except Exception: pass
            self._warning_banner = None
        self._main_frame.pack_forget()
        self._show_login()

    def _on_crash_warning(self, alerts: list):
        """In-app callback invoked when new crash precursors are detected."""
        if not alerts or self._destroyed if hasattr(self, '_destroyed') else False:
            return
        # Pick the highest-severity alert to show in the banner
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        top = sorted(alerts, key=lambda a: sev_order.get(a.get("severity", "low"), 3))[0]
        self.after(0, lambda: self._show_warning_banner(top))

    def _show_warning_banner(self, alert: dict):
        """Show a dismissible in-app warning banner at the top of the content area."""
        from desktop.theme import RED, ORANGE, YELLOW, BG_CARD, TEXT_PRIMARY, FONT_FAMILY
        import customtkinter as ctk
        # Remove existing banner first
        if self._warning_banner:
            try: self._warning_banner.destroy()
            except Exception: pass
            self._warning_banner = None

        sev = alert.get("severity", "medium")
        color = RED if sev == "critical" else ORANGE if sev == "high" else YELLOW
        name = alert.get("name", "?")
        pid = alert.get("pid", "?")
        title = alert.get("title", "Crash Precursor Detected")
        detail = alert.get("detail", "")

        banner = ctk.CTkFrame(self._content_frame, fg_color=BG_CARD, corner_radius=0,
                              border_width=2, border_color=color)
        banner.pack(fill="x", side="top")
        self._warning_banner = banner

        inner = ctk.CTkFrame(banner, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)

        # Warning graphical icon
        from desktop.icons import get_icon
        _warn_icon = get_icon("active_alerts", size=22, color=color)
        ctk.CTkLabel(inner, image=_warn_icon, text="").pack(side="left")

        msg = ctk.CTkLabel(inner,
                           text=f"  {title}  ·  {name} (PID {pid})  ·  {detail}",
                           font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                           text_color=TEXT_PRIMARY, anchor="w")
        msg.pack(side="left", fill="x", expand=True)

        # Dismiss button (plain ASCII "X" — unicode ✕ renders inconsistently)
        def _dismiss():
            try: banner.destroy()
            except Exception: pass
            self._warning_banner = None
        dismiss_btn = ctk.CTkButton(inner, text="X", width=28, height=28, corner_radius=6,
                                    fg_color="transparent", border_width=1, border_color=color,
                                    text_color=color, hover_color="#2a0808",
                                    command=_dismiss,
                                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"))
        dismiss_btn.pack(side="right", padx=(4, 0))

        # Navigate to prediction screen button
        def _go_prediction():
            _dismiss()
            self._navigate("prediction")
            self._sidebar.set_active("prediction")
        view_btn = ctk.CTkButton(inner, text="View Details", width=100, height=28, corner_radius=6,
                                 fg_color=color, text_color="#000000",
                                 hover_color=ORANGE,
                                 command=_go_prediction,
                                 font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"))
        view_btn.pack(side="right", padx=(0, 4))

        # Auto-dismiss after 12 seconds
        self.after(12000, lambda: _dismiss() if self._warning_banner is banner else None)

    def _show_resolution_toast(self, action_type: str, process_name: str, detail: str = ""):
        """
        Trigger a sliding Toast Notification indicating an automated system
        resolution (Throttle, Terminate, CacheDrop) has occurred.
        """
        if getattr(self, "_destroyed", False):
            return
            
        import subprocess
        import threading
        
        urgency = "critical" if action_type in ("Terminate", "CacheDrop", "critical") else "normal"
        title = "CrashSense: Threat Neutralized"
        body = f"[{action_type}] {process_name}\n{detail}"
        
        def _notify():
            try:
                subprocess.run(["notify-send", "-a", "CrashSense", "-u", urgency, title, body], check=False)
            except Exception as e:
                print(f"[UI] Failed to send native notification: {e}")
                
        threading.Thread(target=_notify, daemon=True).start()
            
        if self.wm_state() not in ("iconic", "withdrawn"):
            toast = NotificationToast(
                self, 
                action_type=action_type, 
                process_name=process_name, 
                detail=detail
            )
            toast.show()

    def _poll_resolution_events(self):
        """
        Periodically checks the backend API for new automated resolution actions
        that occurred, triggering the Toast notification.
        """
        import requests
        try:
            # Endpoint logic placeholder: Real implementation would pull from SQLite/history
            # For demonstration and test bounds, we safely pass if no endpoint exists yet.
            # res = requests.get("http://127.0.0.1:5000/api/resolutions/recent", timeout=1)
            # if res.status_code == 200:
            #     for action in res.json().get("events", []):
            #         self._show_resolution_toast(action["type"], action["process"], action["detail"])
            pass
        except Exception:
            pass
            
        self.after(5000, self._poll_resolution_events)

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
            "profile":       lambda: ProfileScreen(self._content_frame),
            "settings":      lambda: SettingsScreen(self._content_frame, on_logout=self._handle_logout),
        }

        factory = screen_factories.get(screen_id, screen_factories["dashboard"])
        self._current_screen_widget = factory()
        self._current_screen_widget.pack(fill="both", expand=True)

    # ── Window Lifecycle ─────────────────────────────────────────

    def hide_window(self):
        """Prompt to quit or hide in tray."""
        from desktop.theme import BG_CARD, TEXT_PRIMARY, ORANGE, RED, FONT_FAMILY
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Exit CrashSense")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG_CARD)
        
        ctk.CTkLabel(dialog, text="Close Application?", font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"), text_color=TEXT_PRIMARY).pack(pady=(30, 10))
        ctk.CTkLabel(dialog, text="Do you want to quit completely, or keep monitoring in the background?", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=TEXT_PRIMARY, wraplength=350).pack(pady=(0, 30))
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        def _bg():
            dialog.destroy()
            self.withdraw()
            
        def _quit():
            dialog.destroy()
            self.full_quit()
            
        ctk.CTkButton(btn_frame, text="Keep in Background", fg_color=ORANGE, hover_color="#c2570a", text_color="#000", command=_bg, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(btn_frame, text="Quit Everything", fg_color=RED, hover_color="#991b1b", text_color="#fff", command=_quit, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(side="right", expand=True, padx=10)

        dialog.transient(self)
        dialog.update_idletasks()
        
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        dialog.grab_set()

    def restore_window(self):
        """Restore window from system tray."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def full_quit(self):
        """Completely exit the application and terminate the background daemon."""
        crash_warning_notifier.stop()
        if self._daemon_process:
            try:
                self._daemon_process.terminate()
                self._daemon_process.wait(timeout=2)
            except Exception:
                try: self._daemon_process.kill()
                except Exception: pass
        
        self.quit()
        self.destroy()
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    """Create and run the CrashSense desktop application."""
    # Attempt to self-register in Linux App Menus for easy portal launching
    try:
        from desktop.linux_integration import create_desktop_shortcut
        create_desktop_shortcut()
    except Exception as e:
        print(f"[CrashSense] Non-fatal shortcut registration error: {e}")

    app = CrashSenseApp()

    import signal
    def handle_signal(sig, frame):
        print(f"\n[CrashSense] Received signal {sig}. Terminating gracefully...")
        # Fire-and-forget daemon termination
        if getattr(app, '_daemon_process', None):
            try:
                app._daemon_process.terminate()
            except Exception:
                pass
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    except Exception:
        pass

    app.mainloop()

if __name__ == "__main__":
    main()
