"""
CrashSense — Alerts Screen
===========================

Displays a scrollable list of real-time system alerts with severity-coded cards.
"""

import customtkinter as ctk
from desktop.theme import (
    BG_ROOT, BG_CARD, ORANGE, RED, RED_BG, YELLOW, YELLOW_BG,
    GREEN, GREEN_BG, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER, FONT_FAMILY,
)
from desktop.data import ALERTS

SEVERITY_STYLES = {
    "Critical": {"color": RED,    "bg": RED_BG,    "border": "#5c1a1a"},
    "High":     {"color": RED,    "bg": RED_BG,    "border": "#5c1a1a"},
    "Medium":   {"color": YELLOW, "bg": YELLOW_BG, "border": "#5c5c1a"},
    "Low":      {"color": GREEN,  "bg": GREEN_BG,  "border": "#1a5c2a"},
}


class AlertsScreen(ctk.CTkFrame):
    """Scrollable alert list with severity-coded cards. Single scroll container."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_ROOT, scrollbar_button_color="#1e2028", scrollbar_button_hover_color="#2a2c36")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            scroll, text="Real-Time Alerts",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=24, pady=(20, 12))

        for alert in ALERTS:
            self._make_alert_card(scroll, alert)

    def _make_alert_card(self, parent, alert):
        sev = alert["severity"]
        style = SEVERITY_STYLES.get(sev, SEVERITY_STYLES["Low"])
        is_critical = sev in ("Critical", "High")

        card = ctk.CTkFrame(
            parent, fg_color=BG_CARD, corner_radius=14,
            border_width=1, border_color=style["border"] if is_critical else BORDER,
        )
        card.pack(fill="x", padx=24, pady=5)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        if is_critical:
            bar = ctk.CTkFrame(card, width=4, fg_color=style["color"], corner_radius=0)
            bar.place(x=0, y=8, relheight=0.7)

        content = ctk.CTkFrame(inner, fg_color="transparent")
        content.pack(side="left", fill="x", expand=True)

        top = ctk.CTkFrame(content, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(top, text=alert["module"], font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        badge = ctk.CTkLabel(top, text=f" {sev} ", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=style["color"], fg_color=style["bg"], corner_radius=8, height=24)
        badge.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(content, text=alert["msg"], font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(content, text=f"Time: {alert['time']}", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_MUTED, anchor="w").pack(fill="x", pady=(2, 0))

        btn = ctk.CTkButton(
            inner, text="View Details", width=100, height=32, corner_radius=8,
            fg_color="#1a1c24", hover_color="#2a2c36",
            border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
        )
        btn.pack(side="right")
