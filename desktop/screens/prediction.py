"""
CrashSense — Prediction Screen
================================

AI-powered crash probability prediction and risk assessment.
"""

import customtkinter as ctk
import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, AMBER, RED, YELLOW, GREEN,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
)


class PredictionScreen(ctk.CTkFrame):
    """Crash prediction dashboard — single scroll container."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_ROOT, scrollbar_button_color="#1e2028", scrollbar_button_hover_color="#2a2c36")
        scroll.pack(fill="both", expand=True)

        # ── Top Row: Gauge + Risk ────────────────────────────────
        top_row = ctk.CTkFrame(scroll, fg_color="transparent")
        top_row.pack(fill="x", padx=24, pady=(20, 0))
        top_row.columnconfigure(0, weight=2)
        top_row.columnconfigure(1, weight=1)

        # Probability Gauge
        gauge_card = ctk.CTkFrame(top_row, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        gauge_card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(gauge_card, text="Crash Probability", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 0))

        probability = 0.73
        fig = Figure(figsize=(5, 3), dpi=100)
        fig.patch.set_facecolor(BG_CARD)
        ax = fig.add_subplot(111, projection="polar")
        ax.set_facecolor(BG_CARD)

        ax.barh(1, np.pi, left=0, height=0.3, color="#1e1e2a", alpha=0.8)
        ax.barh(1, np.pi * probability, left=0, height=0.3, color=ORANGE, alpha=0.9)

        needle_angle = np.pi * probability
        ax.plot([needle_angle, needle_angle], [0, 1.2], color=TEXT_PRIMARY, linewidth=2)
        ax.plot(needle_angle, 1.2, "o", color=ORANGE, markersize=6)

        ax.set_thetamin(0)
        ax.set_thetamax(180)
        ax.set_ylim(0, 1.6)
        ax.set_yticks([])
        ax.set_xticks([0, np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], color=TEXT_MUTED, fontsize=8)
        ax.spines["polar"].set_visible(False)
        ax.grid(False)
        fig.tight_layout(pad=0.5)

        canvas = FigureCanvasTkAgg(fig, master=gauge_card)
        canvas.get_tk_widget().pack(padx=12, pady=(0, 4))
        canvas.draw()

        ctk.CTkLabel(gauge_card, text="73%", font=ctk.CTkFont(family=FONT_FAMILY, size=36, weight="bold"), text_color=ORANGE).pack(pady=(0, 4))
        ctk.CTkLabel(gauge_card, text="Crash probability in next 24 hours", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(pady=(0, 16))

        # Risk Assessment
        risk_card = ctk.CTkFrame(top_row, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        risk_card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        ctk.CTkLabel(risk_card, text="Risk Assessment", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 12))

        levels = [
            ("Low",    "< 30%",      GREEN,  "#0a2a14", False),
            ("Medium", "30% - 60%",  YELLOW, "#2a2508", False),
            ("High",   "> 60%",      RED,    "#2a0f0f", True),
        ]
        for label, range_text, color, bg, is_active in levels:
            row = ctk.CTkFrame(
                risk_card,
                fg_color=bg if is_active else "transparent",
                corner_radius=10,
                border_width=1 if is_active else 0,
                border_color=color if is_active else "transparent",
            )
            row.pack(fill="x", padx=16, pady=4)
            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=12, pady=10)

            ctk.CTkLabel(ri, text="*", font=ctk.CTkFont(size=12, weight="bold"), text_color=color).pack(side="left")
            ctk.CTkLabel(ri, text=f"  {label}", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=color if is_active else TEXT_SECONDARY).pack(side="left")

            ctk.CTkLabel(ri, text=range_text, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

            if is_active:
                ctk.CTkLabel(ri, text="< Current", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=color).pack(side="right", padx=(0, 8))

        ctk.CTkFrame(risk_card, height=20, fg_color="transparent").pack()

        # ── 7-Day Forecast ───────────────────────────────────────
        forecast_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        forecast_card.pack(fill="x", padx=24, pady=(12, 0))

        ctk.CTkLabel(forecast_card, text="7-Day Crash Forecast", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 0))

        fig2 = Figure(figsize=(8, 2.5), dpi=100)
        fig2.patch.set_facecolor(BG_CARD)
        ax2 = fig2.add_subplot(111)
        ax2.set_facecolor(BG_CARD)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        probs = [45, 52, 68, 73, 65, 58, 42]

        ax2.fill_between(range(len(probs)), probs, alpha=0.15, color=ORANGE)
        ax2.plot(range(len(probs)), probs, color=ORANGE, linewidth=2.5, marker="o", markersize=6, markerfacecolor=ORANGE)

        ax2.axhline(y=60, color=RED, linewidth=1, linestyle="--", alpha=0.5)
        ax2.text(6.2, 61, "Danger", color=RED, fontsize=8, alpha=0.7)

        ax2.set_xticks(range(len(days)))
        ax2.set_xticklabels(days)
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("Crash Probability %", color=TEXT_MUTED, fontsize=9)
        ax2.tick_params(colors=TEXT_MUTED, labelsize=9)
        for spine in ax2.spines.values():
            spine.set_color(BORDER)
        ax2.grid(True, color="#1e1e2a", linewidth=0.5, alpha=0.5)
        fig2.tight_layout(pad=1.5)

        canvas2 = FigureCanvasTkAgg(fig2, master=forecast_card)
        canvas2.get_tk_widget().pack(fill="x", padx=12, pady=(4, 16))
        canvas2.draw()

        # ── Preventive Actions ───────────────────────────────────
        actions_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        actions_card.pack(fill="x", padx=24, pady=(12, 24))

        ctk.CTkLabel(actions_card, text="Suggested Preventive Actions", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 8))

        actions = [
            ("[R]", "Restart Service",   "Restart the AuthService to clear memory leaks",   "High Priority"),
            ("[M]", "Increase Memory",   "Scale memory allocation from 4GB to 8GB",         "Medium Priority"),
            ("[?]", "Inspect Module",    "Run diagnostic on affected authentication module", "Recommended"),
        ]
        for icon, title, desc, priority in actions:
            row = ctk.CTkFrame(actions_card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)

            action_inner = ctk.CTkFrame(row, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
            action_inner.pack(fill="x")
            ai = ctk.CTkFrame(action_inner, fg_color="transparent")
            ai.pack(fill="x", padx=14, pady=12)

            icon_frame = ctk.CTkFrame(ai, width=36, height=36, corner_radius=10, fg_color="#2a1a08")
            icon_frame.pack(side="left")
            icon_frame.pack_propagate(False)
            ctk.CTkLabel(icon_frame, text=icon, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=ORANGE).pack(expand=True)

            txt = ctk.CTkFrame(ai, fg_color="transparent")
            txt.pack(side="left", padx=(10, 0), fill="x", expand=True)
            ctk.CTkLabel(txt, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
            ctk.CTkLabel(txt, text=desc, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")

            ctk.CTkLabel(ai, text=priority, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=ORANGE).pack(side="right")

        ctk.CTkFrame(actions_card, height=8, fg_color="transparent").pack()
