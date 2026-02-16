"""
CrashSense — Sidebar Navigation Component
==========================================

A 260px-wide vertical sidebar that provides:
    - Application branding (logo, title, tagline)
    - Six navigation buttons mapped to application screens
    - A logout button pinned to the bottom

Visual Design:
    The active navigation item is highlighted with an orange-tinted background
    and orange text. All other items use the secondary text colour. A subtle
    divider separates the branding area from the navigation list.

Usage:
    sidebar = Sidebar(parent, on_navigate=callback, on_logout=callback)
    sidebar.set_active("alerts")  # programmatically change the active item
"""

import customtkinter as ctk
from desktop.theme import (
    BG_SIDEBAR, ORANGE, ORANGE_BG, TEXT_SECONDARY, TEXT_MUTED,
    BORDER, FONT_FAMILY, NAV_ITEMS, TEXT_PRIMARY,
)
from desktop.icons import get_icon
import os
from PIL import Image


class Sidebar(ctk.CTkFrame):
    """
    Left navigation sidebar with branding, navigation items, and logout.

    Args:
        master:       Parent widget.
        on_navigate:  Callback invoked with a screen_id (str) when the user
                      clicks a nav item.
        on_logout:    Callback invoked when the user clicks the Logout button.

    Attributes:
        _active (str):              Currently highlighted screen id.
        _buttons (dict[str, btn]):  Map of screen_id → CTkButton for
                                    programmatic style updates.
    """

    def __init__(self, master, on_navigate, on_logout, **kwargs):
        super().__init__(master, width=260, fg_color=BG_SIDEBAR, corner_radius=0, **kwargs)
        self.pack_propagate(False)   # Enforce fixed 260px width

        self._on_navigate = on_navigate
        self._on_logout = on_logout
        self._active = "dashboard"   # Default active screen
        self._buttons = {}
        self._icons = {}             # Store icon references to prevent GC

        # ── Branding Section ────────────────────────────────────
        brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        brand_frame.pack(fill="x", padx=20, pady=(24, 4))

        # App logo icon (loaded from assets/icon.png)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "desktop", "assets", "icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "assets", "icon.png")
        pil_icon = Image.open(icon_path).resize((36, 36), Image.LANCZOS)
        self._brand_icon = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(36, 36))

        logo_label = ctk.CTkLabel(brand_frame, image=self._brand_icon, text="")
        logo_label.pack(side="left")

        # App name and tagline
        title_frame = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_frame.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(
            title_frame, text="CRASH SENSE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="Crash Detection System",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")

        # Horizontal divider below branding
        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(20, 12))

        # ── Navigation Items ────────────────────────────────────
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=12)

        for item in NAV_ITEMS:
            btn = self._make_nav_button(nav_frame, item)
            self._buttons[item["id"]] = btn

        # ── Spacer (pushes logout to bottom) ────────────────────
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # ── Logout Button (bottom) ──────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(0, 8))

        logout_icon = get_icon("logout", size=18, color=TEXT_SECONDARY)
        self._icons["logout"] = logout_icon
        logout_btn = ctk.CTkButton(
            self, text="  Logout", anchor="w",
            image=logout_icon, compound="left",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            fg_color="transparent", hover_color="#2a0f0f",
            text_color=TEXT_SECONDARY, height=44, corner_radius=10,
            command=self._on_logout,
        )
        logout_btn.pack(fill="x", padx=12, pady=(0, 20))

        # Apply initial active state
        self.set_active("dashboard")

    # ── Private Helpers ─────────────────────────────────────────

    def _make_nav_button(self, parent, item):
        """
        Create a single navigation button with a PIL-drawn icon.

        Args:
            parent: Parent frame to pack the button into.
            item:   Dict with keys 'id', 'label', 'icon' from NAV_ITEMS.

        Returns:
            CTkButton: The created button reference (stored in _buttons).
        """
        icon_default = get_icon(item["id"], size=18, color=TEXT_SECONDARY)
        icon_active = get_icon(item["id"], size=18, color=ORANGE)
        self._icons[item["id"]] = {"default": icon_default, "active": icon_active}

        btn = ctk.CTkButton(
            parent,
            text=f"  {item['label']}",
            image=icon_default,
            compound="left",
            anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            fg_color="transparent",
            hover_color="#1a1c24",
            text_color=TEXT_SECONDARY,
            height=44,
            corner_radius=10,
            command=lambda sid=item["id"]: self._handle_click(sid),
        )
        btn.pack(fill="x", pady=2)
        return btn

    def _handle_click(self, screen_id):
        """Handle a navigation item click: update visual state and notify parent."""
        self.set_active(screen_id)
        self._on_navigate(screen_id)

    # ── Public API ──────────────────────────────────────────────

    def set_active(self, screen_id):
        """
        Programmatically set the active navigation item.

        Highlights the target item with orange styling and resets all
        others to the default secondary colour.

        Args:
            screen_id: Identifier matching one of NAV_ITEMS[*]['id'].
        """
        self._active = screen_id
        for sid, btn in self._buttons.items():
            icons = self._icons.get(sid)
            if sid == screen_id:
                btn.configure(fg_color=ORANGE_BG, text_color=ORANGE,
                              image=icons["active"] if icons else None)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY,
                              image=icons["default"] if icons else None)
