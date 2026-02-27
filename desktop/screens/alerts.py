"""
CrashSense — Live Alerts Screen
=================================

Displays a live, auto-refreshing list of crash precursor alerts from the
backend process monitor.

Features:
  - Live data from /api/process-alerts (refreshed every 5 seconds)
  - Severity filter tabs: All / Critical / High / Medium / Low
  - Graphical icons per alert type (matching prediction screen)
  - Summary header (total counts per severity)
  - Expandable detail rows per alert
  - Empty-state illustration when no alerts exist
"""

import customtkinter as ctk
import requests
import threading
from datetime import datetime

from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, RED, YELLOW, GREEN, BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
)
from desktop.icons import get_icon

_API_BASE   = "http://127.0.0.1:5000"
_REFRESH_MS = 5000

# ── Severity styling ────────────────────────────────────────────────
_SEV_COLORS = {
    "critical": RED,
    "high":     ORANGE,
    "medium":   YELLOW,
    "low":      BLUE,
}
_SEV_BG = {
    "critical": "#2a0808",
    "high":     "#2a1a08",
    "medium":   "#2a2508",
    "low":      "#0f1a2a",
}
_SEV_BORDER = {
    "critical": "#5c1a1a",
    "high":     "#5c3a0a",
    "medium":   "#5c5c1a",
    "low":      "#0a2a5c",
}

# ── Icon mapping (shared with prediction screen) ────────────────────
_TYPE_ICON_NAMES = {
    "memory_leak":       "memory_leak",
    "cpu_runaway":       "cpu_runaway",
    "thread_explosion":  "thread_explosion",
    "high_thread_count": "thread_explosion",
    "fd_exhaustion":     "fd_exhaustion",
    "zombie":            "zombie",
    "oom_risk":          "oom_risk",
}

# ── Filter tabs ─────────────────────────────────────────────────────
_FILTERS = ["All", "Critical", "High", "Medium", "Low"]


class AlertsScreen(ctk.CTkFrame):
    """
    Live alerts screen. Fetches process-monitor crash precursors and renders
    them with severity-coded cards, graphical icons, and filter tabs.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        self._all_alerts: list[dict] = []
        self._active_filter = "All"
        self._update_id = None
        self._destroyed  = False

        self.bind("<Destroy>", self._on_destroy)
        self._build_ui()
        self._schedule_refresh()

    # ────────────────────────────────────────────────────────────────
    #  UI Construction
    # ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Page header ──────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            header, text="Active Alerts",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Refresh indicator / last-updated time
        self._updated_lbl = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self._updated_lbl.pack(side="right")

        # ── Summary bar (counts per severity) ───────────────────────
        self._summary_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        self._summary_bar.pack(fill="x", padx=24, pady=(12, 0))

        self._summary_labels: dict[str, ctk.CTkLabel] = {}
        for sev, color in [("Critical", RED), ("High", ORANGE), ("Medium", YELLOW), ("Low", BLUE)]:
            col = ctk.CTkFrame(self._summary_bar, fg_color="transparent")
            col.pack(side="left", expand=True, padx=10, pady=10)
            count_lbl = ctk.CTkLabel(
                col, text="0",
                font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
                text_color=color,
            )
            count_lbl.pack()
            ctk.CTkLabel(
                col, text=sev,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_MUTED,
            ).pack()
            self._summary_labels[sev.lower()] = count_lbl

        # ── Filter tab bar ───────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.pack(fill="x", padx=24, pady=(12, 0))

        self._filter_btns: dict[str, ctk.CTkButton] = {}
        for f in _FILTERS:
            btn = ctk.CTkButton(
                tab_bar, text=f, width=80, height=32, corner_radius=8,
                fg_color=ORANGE if f == "All" else BG_CARD,
                text_color=TEXT_PRIMARY if f == "All" else TEXT_MUTED,
                hover_color="#2a2c36",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                command=lambda val=f: self._set_filter(val),
            )
            btn.pack(side="left", padx=(0, 8))
            self._filter_btns[f] = btn

        # ── Scrollable card container ────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_ROOT,
            scrollbar_button_color="#1e2028",
            scrollbar_button_hover_color="#2a2c36",
        )
        self._scroll.pack(fill="both", expand=True, padx=24, pady=12)
        self._scroll.bind_all("<Button-4>", lambda e: self._scroll._parent_canvas.yview_scroll(-3, "units"))
        self._scroll.bind_all("<Button-5>", lambda e: self._scroll._parent_canvas.yview_scroll( 3, "units"))

    # ────────────────────────────────────────────────────────────────
    #  Data Fetching
    # ────────────────────────────────────────────────────────────────

    def _schedule_refresh(self):
        if self._destroyed:
            return
        self._update_id = self.after(_REFRESH_MS, self._fetch)
        # Fetch immediately on first load
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _fetch(self):
        if self._destroyed:
            return
        threading.Thread(target=self._do_fetch, daemon=True).start()
        self._update_id = self.after(_REFRESH_MS, self._fetch)

    def _do_fetch(self):
        try:
            resp = requests.get(f"{_API_BASE}/api/process-alerts", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                alerts = data.get("alerts", [])
                if not self._destroyed:
                    self.after(0, lambda: self._apply_data(alerts))
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────
    #  UI Update
    # ────────────────────────────────────────────────────────────────

    def _apply_data(self, alerts: list[dict]):
        if self._destroyed:
            return

        self._all_alerts = alerts

        # Update summary counts
        for sev in ("critical", "high", "medium", "low"):
            count = sum(1 for a in alerts if a.get("severity") == sev)
            lbl = self._summary_labels.get(sev)
            if lbl:
                lbl.configure(text=str(count))

        # Update last-refreshed time
        self._updated_lbl.configure(
            text=f"Last updated {datetime.now().strftime('%H:%M:%S')}"
        )

        # Re-render the card list
        self._render_cards()

    def _set_filter(self, val: str):
        self._active_filter = val
        for name, btn in self._filter_btns.items():
            active = name == val
            btn.configure(
                fg_color=ORANGE if active else BG_CARD,
                text_color=TEXT_PRIMARY if active else TEXT_MUTED,
            )
        self._render_cards()

    def _render_cards(self):
        # Clear existing cards
        for child in self._scroll.winfo_children():
            child.destroy()

        filtered = self._filter_alerts()

        if not filtered:
            self._render_empty_state()
            return

        for alert in filtered:
            self._make_alert_card(alert)

    def _filter_alerts(self) -> list[dict]:
        if self._active_filter == "All":
            return self._all_alerts
        return [
            a for a in self._all_alerts
            if a.get("severity", "low").lower() == self._active_filter.lower()
        ]

    # ────────────────────────────────────────────────────────────────
    #  Card Rendering
    # ────────────────────────────────────────────────────────────────

    def _make_alert_card(self, alert: dict):
        sev    = alert.get("severity", "low")
        color  = _SEV_COLORS.get(sev, BLUE)
        bg     = _SEV_BG.get(sev, BG_CARD)
        border = _SEV_BORDER.get(sev, BORDER)

        card = ctk.CTkFrame(
            self._scroll, fg_color=bg,
            corner_radius=12, border_width=1, border_color=border,
        )
        card.pack(fill="x", pady=5)

        try:
            # ── Left accent bar ──────────────────────────────────────
            accent = ctk.CTkFrame(card, width=4, fg_color=color, corner_radius=2)
            accent.place(x=0, y=8, relheight=0.84)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=(14, 12), pady=12)

            # ── Icon box ─────────────────────────────────────────────
            icon_name = _TYPE_ICON_NAMES.get(alert.get("type", ""), "active_alerts")
            icon_img  = get_icon(icon_name, size=28, color=color)
            icon_box  = ctk.CTkFrame(inner, width=50, height=50, corner_radius=12, fg_color=BG_CARD_INNER)
            icon_box.pack(side="left")
            icon_box.pack_propagate(False)
            ctk.CTkLabel(icon_box, image=icon_img, text="").pack(expand=True)

            # ── Main content ─────────────────────────────────────────
            content = ctk.CTkFrame(inner, fg_color="transparent")
            content.pack(side="left", fill="x", expand=True, padx=14)

            # Title row: name + severity badge + PID
            title_row = ctk.CTkFrame(content, fg_color="transparent")
            title_row.pack(fill="x")

            title = alert.get("title", alert.get("type", "?").replace("_", " ").title())
            ctk.CTkLabel(
                title_row, text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=color,
            ).pack(side="left")

            # Severity badge
            badge = ctk.CTkLabel(
                title_row,
                text=f"  {sev.upper()}  ",
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color=color, fg_color=border, corner_radius=6, height=18,
            )
            badge.pack(side="left", padx=(8, 0))

            # Process name + PID
            name = alert.get("name", "Unknown")
            pid  = alert.get("pid",  "?")
            ctk.CTkLabel(
                title_row,
                text=f"   {name}  (PID {pid})",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
            ).pack(side="left", padx=(8, 0))

            # Detail line
            detail = alert.get("detail", "")
            if detail:
                ctk.CTkLabel(
                    content, text=detail,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=TEXT_SECONDARY, anchor="w",
                ).pack(fill="x", pady=(4, 0))

            # Bottom row: metric chip + detected time
            meta_row = ctk.CTkFrame(content, fg_color="transparent")
            meta_row.pack(fill="x", pady=(6, 0))

            metric = alert.get("metric", "")
            if metric:
                chip = ctk.CTkLabel(
                    meta_row,
                    text=f"  {metric}  ",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    text_color=color, fg_color=BG_CARD_INNER, corner_radius=6, height=22,
                )
                chip.pack(side="left")

            time_str = alert.get("time_str", "")
            if time_str:
                ctk.CTkLabel(
                    meta_row, text=f"Detected {time_str}",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=TEXT_MUTED,
                ).pack(side="left", padx=(10, 0))

            # ── Right: metric value (large) ──────────────────────────
            right = ctk.CTkFrame(inner, fg_color="transparent")
            right.pack(side="right", padx=(8, 0))

            type_label = alert.get("type", "").replace("_", " ").upper()
            if metric:
                ctk.CTkLabel(
                    right, text=metric,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                    text_color=TEXT_PRIMARY,
                ).pack(anchor="e")
            ctk.CTkLabel(
                right, text=type_label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color=TEXT_MUTED,
            ).pack(anchor="e")

        except Exception as exc:
            ctk.CTkLabel(
                card,
                text=f"  Alert rendering error: {exc}",
                font=ctk.CTkFont(size=10),
                text_color=TEXT_MUTED,
            ).pack(pady=8, padx=12, anchor="w")

    def _render_empty_state(self):
        """Show a friendly 'all clear' message when no alerts match the filter."""
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(expand=True, fill="both", pady=60)

        icon_img = get_icon("checkmark", size=48, color=GREEN)
        ctk.CTkLabel(frame, image=icon_img, text="").pack()
        ctk.CTkLabel(
            frame,
            text="No alerts" if self._active_filter == "All" else f"No {self._active_filter} alerts",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=GREEN,
        ).pack(pady=(12, 4))
        ctk.CTkLabel(
            frame,
            text="All monitored processes are behaving normally." if self._active_filter == "All"
                 else f"No {self._active_filter.lower()}-severity issues detected.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        ).pack()

    # ────────────────────────────────────────────────────────────────
    #  Lifecycle
    # ────────────────────────────────────────────────────────────────

    def _on_destroy(self, event):
        if event.widget is self:
            self._destroyed = True
            if self._update_id:
                self.after_cancel(self._update_id)
