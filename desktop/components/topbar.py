"""
CrashSense — Top Bar Component
===============================

A fixed-height (72px) top bar that spans the full width of the content area.
Adapts its content based on the active screen:

    ┌──────────────────────────────────────────────────────────┐
    │  [←]  Page Title                      🔔  ⏻  [AD]  │
    │       Subtitle text                                      │
    └──────────────────────────────────────────────────────────┘

Features:
    - **Back button**   — Hidden on the dashboard; visible on all sub-screens.
    - **Page title**    — Dynamically updated via `set_screen()`.
    - **Notification**  — Bell icon (UI placeholder for future notification panel).
    - **Logout**        — Power-off icon with red background for quick logout.
    - **User avatar**   — Initials badge (hardcoded "AD" for demo).

Usage:
    topbar = TopBar(parent, on_logout=callback, on_back=callback)
    topbar.set_screen("alerts")  # updates title, shows back button
"""

import customtkinter as ctk
from desktop.theme import (
    BG_TOPBAR, BORDER, ORANGE, RED, RED_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, FONT_FAMILY,
)
from desktop.icons import get_icon
from desktop import session


class TopBar(ctk.CTkFrame):
    """
    Top navigation bar with contextual title, notifications, and logout.

    Args:
        master:     Parent widget.
        on_logout:  Callback invoked when the power-off button is clicked.
        on_back:    Optional callback for the back-arrow button.

    Attributes:
        _title (CTkLabel):     Dynamic page title label.
        _subtitle (CTkLabel):  Static subtitle below the title.
        _back_btn (CTkButton): Back arrow — pack/pack_forget toggles visibility.
    """

    # ── Screen-specific titles ──────────────────────────────────
    SCREEN_TITLES = {
        "dashboard":     "Dashboard",
        "alerts":        "Alerts",
        "crash-details": "Crash Details",
        "logs":          "System Logs",
        "prediction":    "Prediction",
        "settings":      "Settings",
        "profile":       "My Profile",
    }

    def __init__(self, master, on_logout, on_back=None, on_profile=None, **kwargs):
        super().__init__(master, height=72, fg_color=BG_TOPBAR, corner_radius=0, **kwargs)
        self.pack_propagate(False)    # Enforce fixed 72px height

        self._on_logout = on_logout
        self._on_back = on_back
        self._on_profile = on_profile

        # Keep icon references to prevent garbage collection
        self._icons = {}

        # ── Bottom border ───────────────────────────────────────
        border = ctk.CTkFrame(self, height=1, fg_color=BORDER)
        border.pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24)

        # ── Left section: back button + page title ──────────────
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="y")

        # Back button (hidden by default; shown on non-dashboard screens)
        back_icon = get_icon("back_arrow", size=16, color=TEXT_SECONDARY)
        self._icons["back"] = back_icon
        self._back_btn = ctk.CTkButton(
            left, text="", width=40, height=40, corner_radius=10,
            image=back_icon,
            fg_color="#1a1c24", hover_color="#2a2c36",
            text_color=TEXT_SECONDARY,
            command=self._handle_back,
        )
        self._back_btn.pack(side="left", padx=(0, 12))
        self._back_btn.pack_forget()   # Hidden for dashboard

        # Page title and subtitle
        title_frame = ctk.CTkFrame(left, fg_color="transparent")
        title_frame.pack(side="left")

        self._title = ctk.CTkLabel(
            title_frame, text="Dashboard",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        self._title.pack(anchor="w")

        self._subtitle = ctk.CTkLabel(
            title_frame, text="Real-time system monitoring and analysis",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
        )
        self._subtitle.pack(anchor="w")

        # ── Right section: actions ──────────────────────────────
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right", fill="y")

        # Notification bell
        bell_icon = get_icon("bell", size=16, color=TEXT_SECONDARY)
        self._icons["bell"] = bell_icon
        notif_btn = ctk.CTkButton(
            right, text="", width=40, height=40, corner_radius=10,
            image=bell_icon,
            fg_color="#1a1c24", hover_color="#2a2c36",
            text_color=TEXT_SECONDARY,
        )
        notif_btn.pack(side="left", padx=4)

        # Logout / power-off button (red-tinted)
        power_icon = get_icon("power", size=16, color=RED)
        self._icons["power"] = power_icon
        logout_btn = ctk.CTkButton(
            right, text="", width=40, height=40, corner_radius=10,
            image=power_icon,
            fg_color=RED_BG, hover_color="#3a1515",
            text_color=RED,
            command=self._on_logout,
        )
        logout_btn.pack(side="left", padx=4)

        # Test Button for Toast Notification Animation
        test_btn = ctk.CTkButton(
            right,
            text="Test Action Toast",
            width=120, height=32, corner_radius=6,
            fg_color="#1e1e2e", text_color=TEXT_PRIMARY, hover_color="#3b82f6",
            command=self._debug_trigger_toast,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
        )
        test_btn.pack(side="left", padx=(0, 4))

        # User avatar (initials badge — dynamic from session)

        initials = session.get_initials()
        self._avatar_frame = ctk.CTkFrame(right, width=40, height=40, corner_radius=10,
                                          fg_color=ORANGE, cursor="hand2")
        self._avatar_frame.pack(side="left", padx=(4, 0))
        self._avatar_frame.pack_propagate(False)
        self._avatar_label = ctk.CTkLabel(
            self._avatar_frame, text=initials,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#ffffff",
        )
        self._avatar_label.pack(expand=True)
        self._avatar_frame.bind("<Button-1>", lambda e: self._handle_profile())
        self._avatar_label.bind("<Button-1>", lambda e: self._handle_profile())

    # ── Public API ──────────────────────────────────────────────

    def set_screen(self, screen_id: str):
        """
        Update the top bar to reflect the active screen.

        - Changes the page title text.
        - Shows the back button on all screens except 'dashboard'.

        Args:
            screen_id: Identifier from NAV_ITEMS (e.g. 'alerts', 'logs').
        """
        self._title.configure(text=self.SCREEN_TITLES.get(screen_id, "Dashboard"))

        if screen_id == "dashboard":
            self._back_btn.pack_forget()
        else:
            # Re-pack the back button before the title frame
            self._back_btn.pack(side="left", padx=(0, 12), before=self._title.master)

    def _debug_trigger_toast(self):
        """Debug function to test the sliding UI animation."""
        import random
        # Must locate app instance
        app = self.winfo_toplevel()
        if hasattr(app, "_show_resolution_toast"):
            actions = [
                ("Throttle", "chrome", "CPU at 99%"),
                ("Terminate", "memory_leak_script", "RSS grew by 50MB/min"),
                ("CacheDrop", "system", "OOM Risk Critical")
            ]
            action = random.choice(actions)
            app._show_resolution_toast(action[0], action[1], action[2])

    def update_avatar(self):

        """Refresh the avatar initials from the current session (call after login)."""
        self._avatar_label.configure(text=session.get_initials())

    # ── Private Helpers ─────────────────────────────────────────

    def _handle_back(self):
        """Invoke the on_back callback (typically navigates to dashboard)."""
        if self._on_back:
            self._on_back()

    def _handle_profile(self):
        """Navigate to the profile screen."""
        if self._on_profile:
            self._on_profile()
