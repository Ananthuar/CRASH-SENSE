"""
CrashSense — Crash Details Screen
===================================

Deep-dive view for a single crash incident with AI root cause analysis.
"""

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, RED, RED_BG,
    BLUE, BLUE_BG, YELLOW, YELLOW_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
)
from desktop.data import CRASH_INCIDENT, LOG_ENTRIES, RESOURCE_METRICS
from desktop.icons import get_icon


class CrashDetailsScreen(ctk.CTkFrame):
    """Crash incident details — single scroll container."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_ROOT, scrollbar_button_color="#1e2028", scrollbar_button_hover_color="#2a2c36")
        scroll.pack(fill="both", expand=True)
        scroll.bind_all("<Button-4>", lambda e: scroll._parent_canvas.yview_scroll(-3, "units"))
        scroll.bind_all("<Button-5>", lambda e: scroll._parent_canvas.yview_scroll(3, "units"))

        self._icons_ref = []  # prevent GC

        inc = CRASH_INCIDENT

        # ── Incident Header ─────────────────────────────────────
        header_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        header_card.pack(fill="x", padx=24, pady=(20, 0))
        hi = ctk.CTkFrame(header_card, fg_color="transparent")
        hi.pack(fill="x", padx=20, pady=16)

        top = ctk.CTkFrame(hi, fg_color="transparent")
        top.pack(fill="x")

        icon_img = get_icon("crash_incident", size=22, color=RED)
        self._icons_ref.append(icon_img)
        icon = ctk.CTkFrame(top, width=48, height=48, corner_radius=12, fg_color=RED_BG)
        icon.pack(side="left")
        icon.pack_propagate(False)
        ctk.CTkLabel(icon, image=icon_img, text="").pack(expand=True)

        txt = ctk.CTkFrame(top, fg_color="transparent")
        txt.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(txt, text=f"Crash Incident #{inc['id']}", font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(txt, text=inc["date"], font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

        badge = ctk.CTkLabel(top, text=f" {inc['severity']} ", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=RED, fg_color=RED_BG, corner_radius=8, height=30)
        badge.pack(side="right")

        ctk.CTkFrame(hi, height=1, fg_color=BORDER).pack(fill="x", pady=(12, 10))
        info_row = ctk.CTkFrame(hi, fg_color="transparent")
        info_row.pack(fill="x")
        for i in range(3):
            info_row.columnconfigure(i, weight=1)

        for col, (label, val) in enumerate([
            ("Affected Module", inc["module"]),
            ("Recovery Time", inc["recovery"]),
            ("Impact", inc["impact"]),
        ]):
            f = ctk.CTkFrame(info_row, fg_color="transparent")
            f.grid(row=0, column=col, sticky="w", padx=4)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")
            ctk.CTkLabel(f, text=val, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")

        # ── Crash Summary ────────────────────────────────────────
        sum_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        sum_card.pack(fill="x", padx=24, pady=(12, 0))
        si = ctk.CTkFrame(sum_card, fg_color="transparent")
        si.pack(fill="x", padx=20, pady=16)

        h = ctk.CTkFrame(si, fg_color="transparent")
        h.pack(fill="x")
        info_icon = get_icon("info_circle", size=18, color=ORANGE)
        self._icons_ref.append(info_icon)
        ctk.CTkLabel(h, image=info_icon, text="").pack(side="left")
        ctk.CTkLabel(h, text="  Crash Summary", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        ctk.CTkLabel(si, text=inc["summary"], font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_SECONDARY, wraplength=700, justify="left").pack(fill="x", pady=(8, 0))

        # ── AI Root Cause Analysis ───────────────────────────────
        ai_card = ctk.CTkFrame(scroll, fg_color="#1a1208", corner_radius=16, border_width=1, border_color="#3d2a0a")
        ai_card.pack(fill="x", padx=24, pady=(12, 0))
        ai = ctk.CTkFrame(ai_card, fg_color="transparent")
        ai.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(ai, text="AI-Based Root Cause Analysis", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 8))

        for i, rc in enumerate(inc["root_causes"], 1):
            row = ctk.CTkFrame(ai, fg_color="transparent")
            row.pack(fill="x", pady=4)

            num = ctk.CTkFrame(row, width=28, height=28, corner_radius=14, fg_color=ORANGE)
            num.pack(side="left")
            num.pack_propagate(False)
            ctk.CTkLabel(num, text=str(i), font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#ffffff").pack(expand=True)

            t = ctk.CTkFrame(row, fg_color="transparent")
            t.pack(side="left", padx=(10, 0))
            ctk.CTkLabel(t, text=rc["title"], font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(t, text=f"Confidence: {rc['confidence']}", font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_SECONDARY).pack(anchor="w")

        # ── Error Logs ───────────────────────────────────────────
        log_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        log_card.pack(fill="x", padx=24, pady=(12, 0))
        li = ctk.CTkFrame(log_card, fg_color="transparent")
        li.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(li, text="Error Logs", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 8))

        log_box = ctk.CTkFrame(li, fg_color=BG_CARD_INNER, corner_radius=10)
        log_box.pack(fill="x")

        level_colors = {
            "ERROR": (RED, RED_BG),
            "WARN":  (YELLOW, YELLOW_BG),
            "INFO":  (BLUE, BLUE_BG),
        }

        for entry in LOG_ENTRIES:
            row = ctk.CTkFrame(log_box, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=3)

            ctk.CTkLabel(row, text=entry["time"], font=ctk.CTkFont(family="Courier", size=11), text_color=TEXT_MUTED, width=70).pack(side="left")

            lc, lb = level_colors.get(entry["level"], (TEXT_MUTED, BG_CARD_INNER))
            ctk.CTkLabel(row, text=f" {entry['level']} ", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=lc, fg_color=lb, corner_radius=4, width=50).pack(side="left", padx=(8, 8))

            ctk.CTkLabel(row, text=entry["msg"], font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY, anchor="w").pack(side="left", fill="x", expand=True)

        # ── Resource Metrics Chart ───────────────────────────────
        chart_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        chart_card.pack(fill="x", padx=24, pady=(12, 24))
        ctk.CTkLabel(chart_card, text="Resource Metrics at Time of Crash", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 0))

        fig = Figure(figsize=(8, 2.8), dpi=100)
        fig.patch.set_facecolor(BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG_CARD)

        times = [d["time"] for d in RESOURCE_METRICS]
        ax.plot(times, [d["cpu"] for d in RESOURCE_METRICS], color=ORANGE, linewidth=2, label="CPU %")
        ax.plot(times, [d["memory"] for d in RESOURCE_METRICS], color="#fb923c", linewidth=2, label="Memory %")
        ax.plot(times, [d["threads"] for d in RESOURCE_METRICS], color="#fbbf24", linewidth=2, label="Thread Count")

        ax.legend(facecolor=BG_CARD, edgecolor=BORDER, labelcolor=TEXT_SECONDARY, fontsize=8)
        ax.tick_params(colors=TEXT_MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.grid(True, color="#1e1e2a", linewidth=0.5, alpha=0.5)
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, master=chart_card)
        canvas.get_tk_widget().pack(fill="x", padx=12, pady=(4, 16))
        canvas.draw()
