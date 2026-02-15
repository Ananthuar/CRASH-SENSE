"""
CrashSense — Logs Screen
=========================

System log viewer with search, filters, analytics, and paginated table.
"""

import customtkinter as ctk
from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, BG_INPUT, ORANGE,
    RED, RED_BG, YELLOW, YELLOW_BG, GREEN, GREEN_BG, BLUE, BLUE_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DARK,
    BORDER, FONT_FAMILY,
)
from desktop.data import FULL_LOGS

LEVEL_COLORS = {
    "ERROR": (RED, RED_BG),
    "WARN":  (YELLOW, YELLOW_BG),
    "INFO":  (BLUE, BLUE_BG),
    "DEBUG": (TEXT_MUTED, BG_CARD_INNER),
}


class LogsScreen(ctk.CTkFrame):
    """System logs viewer — single scroll container."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_ROOT, scrollbar_button_color="#1e2028", scrollbar_button_hover_color="#2a2c36")
        scroll.pack(fill="both", expand=True)

        # ── Search & Filters ────────────────────────────────────
        search_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        search_card.pack(fill="x", padx=24, pady=(20, 0))
        si = ctk.CTkFrame(search_card, fg_color="transparent")
        si.pack(fill="x", padx=16, pady=14)

        search_row = ctk.CTkFrame(si, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 10))

        search_entry = ctk.CTkEntry(
            search_row, height=44, corner_radius=12,
            fg_color=BG_INPUT, border_color=BORDER,
            placeholder_text="Search logs...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_PRIMARY,
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        filter_btn = ctk.CTkButton(
            search_row, text="Filters", width=100, height=44, corner_radius=12,
            fg_color="#1a1c24", hover_color="#2a2c36",
            border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_PRIMARY,
        )
        filter_btn.pack(side="right")

        dropdown_row = ctk.CTkFrame(si, fg_color="transparent")
        dropdown_row.pack(fill="x")

        for label in ["All Dates", "All Error Types", "All Modules"]:
            dd = ctk.CTkOptionMenu(
                dropdown_row, values=[label, "Option 1", "Option 2"],
                width=160, height=36, corner_radius=8,
                fg_color=BG_INPUT, button_color="#1a1c24",
                button_hover_color="#2a2c36",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_PRIMARY, dropdown_fg_color=BG_CARD,
            )
            dd.set(label)
            dd.pack(side="left", padx=(0, 8))

        # ── Analytics Cards ─────────────────────────────────────
        analytics_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        analytics_frame.pack(fill="x", padx=24, pady=(12, 0))
        for i in range(3):
            analytics_frame.columnconfigure(i, weight=1, uniform="an")

        analytics = [
            ("Total Errors",        "156",  "+12% from yesterday", RED,    "^"),
            ("Warnings",            "87",   "-8% from yesterday",  GREEN,  "v"),
            ("Most Affected Module","Auth",  "42 errors logged",   ORANGE, None),
        ]
        for col, (title, value, sub, color, icon) in enumerate(analytics):
            card = ctk.CTkFrame(analytics_frame, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
            card.grid(row=0, column=col, padx=6, sticky="nsew")
            ci = ctk.CTkFrame(card, fg_color="transparent")
            ci.pack(fill="x", padx=16, pady=14)

            top = ctk.CTkFrame(ci, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(side="left")
            if icon:
                ctk.CTkLabel(top, text=icon, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=color).pack(side="right")

            ctk.CTkLabel(ci, text=value, font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"), text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", pady=(6, 0))
            ctk.CTkLabel(ci, text=sub, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=color, anchor="w").pack(fill="x")

        # ── Log Table ────────────────────────────────────────────
        table_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        table_card.pack(fill="x", padx=24, pady=(12, 0))

        header = ctk.CTkFrame(table_card, fg_color="transparent", height=40)
        header.pack(fill="x", padx=4)
        cols = [("Timestamp", 170), ("Level", 70), ("Module", 130), ("Error Type", 100), ("Message", 300)]
        for label, w in cols:
            ctk.CTkLabel(header, text=label, width=w, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_SECONDARY, anchor="w").pack(side="left", padx=10, pady=10)

        ctk.CTkFrame(table_card, height=1, fg_color=BORDER).pack(fill="x")

        for log in FULL_LOGS:
            row = ctk.CTkFrame(table_card, fg_color="transparent", height=40)
            row.pack(fill="x", padx=4)

            ctk.CTkLabel(row, text=log["time"], width=170, font=ctk.CTkFont(family="Courier", size=11), text_color=TEXT_SECONDARY, anchor="w").pack(side="left", padx=10, pady=8)

            lc, lb = LEVEL_COLORS.get(log["level"], (TEXT_MUTED, BG_CARD_INNER))
            ctk.CTkLabel(row, text=f" {log['level']} ", width=70, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=lc, fg_color=lb, corner_radius=10).pack(side="left", padx=10, pady=8)

            ctk.CTkLabel(row, text=log["module"], width=130, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_PRIMARY, anchor="w").pack(side="left", padx=10, pady=8)

            err_type = log["type"] if log["type"] else "-"
            err_color = TEXT_SECONDARY if log["type"] else TEXT_DARK
            ctk.CTkLabel(row, text=err_type, width=100, font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=err_color, anchor="w").pack(side="left", padx=10, pady=8)

            ctk.CTkLabel(row, text=log["msg"], font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY, anchor="w").pack(side="left", padx=10, pady=8, fill="x", expand=True)

            ctk.CTkFrame(table_card, height=1, fg_color=BORDER).pack(fill="x")

        # ── Pagination ──────────────────────────────────────────
        pag = ctk.CTkFrame(table_card, fg_color="transparent", height=50)
        pag.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(pag, text="Showing 1-10 of 156 entries", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(side="left")

        pag_right = ctk.CTkFrame(pag, fg_color="transparent")
        pag_right.pack(side="right")
        for i, label in enumerate(["<", "1", "2", "3", ">"]):
            is_active = label == "1"
            ctk.CTkButton(
                pag_right, text=label, width=34, height=34, corner_radius=8,
                fg_color=ORANGE if is_active else "#1a1c24",
                hover_color="#ea6c10" if is_active else "#2a2c36",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=TEXT_PRIMARY if is_active else TEXT_SECONDARY,
            ).pack(side="left", padx=2)

        ctk.CTkFrame(scroll, height=20, fg_color="transparent").pack()
