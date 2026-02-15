"""
CrashSense — Dashboard Screen
==============================

The primary view after login. Provides a high-level overview of system health
with KPI cards, crash trend chart, and resource usage charts.
"""

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, AMBER, GREEN, GREEN_BG, RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
)
from desktop.data import DASHBOARD_METRICS, CRASH_TREND_DATA, CPU_DATA, MEMORY_DATA


class DashboardScreen(ctk.CTkFrame):
    """
    Main dashboard view — uses a single internal CTkScrollableFrame.
    The outer CTkFrame ensures no nested scroll containers.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        # Single scroll container
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_ROOT, scrollbar_button_color="#1e2028", scrollbar_button_hover_color="#2a2c36")
        scroll.pack(fill="both", expand=True)

        # ── System Status Banner ────────────────────────────────
        status = ctk.CTkFrame(scroll, fg_color=GREEN_BG, corner_radius=16, border_width=1, border_color="#1a4a2a")
        status.pack(fill="x", padx=24, pady=(20, 0))
        status_inner = ctk.CTkFrame(status, fg_color="transparent")
        status_inner.pack(fill="x", padx=20, pady=16)

        left = ctk.CTkFrame(status_inner, fg_color="transparent")
        left.pack(side="left")

        shield = ctk.CTkFrame(left, width=32, height=32, corner_radius=8, fg_color=GREEN)
        shield.pack(side="left", padx=(0, 10))
        shield.pack_propagate(False)
        ctk.CTkLabel(shield, text="OK", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color="#ffffff").pack(expand=True)

        txt = ctk.CTkFrame(left, fg_color="transparent")
        txt.pack(side="left")
        ctk.CTkLabel(txt, text="System Status: Stable", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=GREEN).pack(anchor="w")
        ctk.CTkLabel(txt, text="All systems operational. No critical issues detected.", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#4ade80").pack(anchor="w")

        right = ctk.CTkFrame(status_inner, fg_color="transparent")
        right.pack(side="right")
        ctk.CTkLabel(right, text="*", font=ctk.CTkFont(size=14, weight="bold"), text_color=GREEN).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(right, text="Live", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=GREEN).pack(side="left")

        # ── KPI Metric Cards ────────────────────────────────────
        cards_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        cards_frame.pack(fill="x", padx=24, pady=(16, 0))
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1, uniform="mc")

        card_icons = ["[#]", "[T]", "/!\\", "[S]"]
        keys = list(DASHBOARD_METRICS.keys())
        for col, (key, icon) in enumerate(zip(keys, card_icons)):
            m = DASHBOARD_METRICS[key]
            self._make_metric_card(cards_frame, col, icon, m)

        # ── Crash Trend Chart ───────────────────────────────────
        self._make_chart_section(scroll, "Crash Trend - Last 24 Hours", CRASH_TREND_DATA, "crashes", ORANGE, "Crashes", True)

        # ── Resource Usage Charts ───────────────────────────────
        charts_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        charts_frame.pack(fill="x", padx=24, pady=(16, 24))
        charts_frame.columnconfigure(0, weight=1)
        charts_frame.columnconfigure(1, weight=1)

        self._make_resource_chart(charts_frame, 0, "CPU Usage", CPU_DATA, ORANGE, "52%")
        self._make_resource_chart(charts_frame, 1, "Memory Usage", MEMORY_DATA, AMBER, "68%")

    def _make_metric_card(self, parent, col, icon, m):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.grid(row=0, column=col, padx=6, sticky="nsew")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        icon_frame = ctk.CTkFrame(top, width=44, height=44, corner_radius=12, fg_color="#2a1a08")
        icon_frame.pack(side="left")
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text=icon, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=ORANGE).pack(expand=True)

        trend_color = RED if m["trend_up"] else GREEN
        trend_bg = "#2a0f0f" if m["trend_up"] else "#0a2a14"
        ctk.CTkLabel(top, text=m["trend"], font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=trend_color, fg_color=trend_bg, corner_radius=8, width=50, height=26).pack(side="right")

        ctk.CTkLabel(inner, text=m["value"], font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"), text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(inner, text=m["label"], font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(inner, text=m["sub"], font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_MUTED, anchor="w").pack(fill="x")

    def _make_chart_section(self, parent, title, data, key, color, ylabel, show_dots):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=24, pady=(16, 0))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 0))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        rt = ctk.CTkFrame(header, fg_color="transparent")
        rt.pack(side="right")
        ctk.CTkLabel(rt, text="*", font=ctk.CTkFont(size=10, weight="bold"), text_color=ORANGE).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(rt, text="Real-time data", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_MUTED).pack(side="left")

        fig = Figure(figsize=(8, 2.5), dpi=100)
        fig.patch.set_facecolor(BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG_CARD)

        times = [d["time"] for d in data]
        vals = [d[key] for d in data]

        ax.plot(times, vals, color=color, linewidth=2, marker="o" if show_dots else None, markersize=5, markerfacecolor=color)
        ax.fill_between(range(len(vals)), vals, alpha=0.1, color=color)

        ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=9)
        ax.tick_params(colors=TEXT_MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.grid(True, color="#1e1e2a", linewidth=0.5, alpha=0.5)
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().pack(fill="x", padx=12, pady=(4, 12))
        canvas.draw()

    def _make_resource_chart(self, parent, col, title, data, color, current_val):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.grid(row=0, column=col, padx=6, sticky="nsew")

        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 0))

        fig = Figure(figsize=(4, 2), dpi=100)
        fig.patch.set_facecolor(BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG_CARD)

        times = [d["time"] for d in data]
        vals = [d["usage"] for d in data]

        ax.fill_between(range(len(vals)), vals, alpha=0.15, color=color)
        ax.plot(range(len(vals)), vals, color=color, linewidth=2)
        ax.set_xticks(range(len(times)))
        ax.set_xticklabels(times, fontsize=7)
        ax.set_ylim(0, 100)
        ax.tick_params(colors=TEXT_MUTED, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.grid(True, color="#1e1e2a", linewidth=0.5, alpha=0.5)
        fig.tight_layout(pad=1.2)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().pack(fill="x", padx=12, pady=(4, 4))
        canvas.draw()

        btm = ctk.CTkFrame(card, fg_color="transparent")
        btm.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(btm, text="Current: ", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(btm, text=current_val, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=color).pack(side="left")
