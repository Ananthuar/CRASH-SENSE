"""
CrashSense — Live Logs Screen
==============================

Same layout as before, but powered by real data from /api/logs:

  - Search bar      → filters by module, type, or message text
  - Level filter    → All / ERROR / WARN / INFO
  - Type dropdown   → distinct alert types from the data
  - Analytics cards → real error/warn counts and top affected module
  - Log table       → live rows, newest first
  - Pagination      → 15 rows per page, working < / > buttons
  - Auto-refresh    → every 8 seconds
"""

import threading
import customtkinter as ctk
import requests
from datetime import datetime

from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, BG_INPUT, ORANGE,
    RED, RED_BG, YELLOW, YELLOW_BG, GREEN, GREEN_BG, BLUE, BLUE_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
)

_API_BASE    = "http://127.0.0.1:5000"
_REFRESH_MS  = 8000
_PAGE_SIZE   = 15

LEVEL_COLORS = {
    "ERROR": (RED,      RED_BG),
    "WARN":  (YELLOW,   YELLOW_BG),
    "INFO":  (BLUE,     BLUE_BG),
    "DEBUG": (TEXT_MUTED, BG_CARD_INNER),
}


class LogsScreen(ctk.CTkFrame):
    """Live system logs viewer — same structure, real data."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        self._all_entries:    list[dict] = []
        self._filtered:       list[dict] = []
        self._current_page    = 0
        self._search_text     = ""
        self._level_filter    = "All"
        self._type_filter     = "All Types"
        self._update_id       = None
        self._destroyed       = False

        self.bind("<Destroy>", self._on_destroy)
        self._build_ui()
        self._schedule_refresh()

    # ────────────────────────────────────────────────────────────────
    #  UI Construction (mirrors original layout exactly)
    # ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_ROOT,
            scrollbar_button_color="#1e2028",
            scrollbar_button_hover_color="#2a2c36",
        )
        scroll.pack(fill="both", expand=True)
        scroll.bind_all("<Button-4>", lambda e: scroll._parent_canvas.yview_scroll(-3, "units"))
        scroll.bind_all("<Button-5>", lambda e: scroll._parent_canvas.yview_scroll( 3, "units"))
        self._scroll = scroll

        # ── Search & Filters ──────────────────────────────────────
        search_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16,
                                   border_width=1, border_color=BORDER)
        search_card.pack(fill="x", padx=24, pady=(20, 0))
        si = ctk.CTkFrame(search_card, fg_color="transparent")
        si.pack(fill="x", padx=16, pady=14)

        search_row = ctk.CTkFrame(si, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 10))

        self._search_entry = ctk.CTkEntry(
            search_row, height=44, corner_radius=12,
            fg_color=BG_INPUT, border_color=BORDER,
            placeholder_text="Search logs by module, type, or message…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_PRIMARY,
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._search_entry.bind("<KeyRelease>", self._on_search_key)

        ctk.CTkButton(
            search_row, text="Clear", width=80, height=44, corner_radius=12,
            fg_color="#1a1c24", hover_color="#2a2c36",
            border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_PRIMARY,
            command=self._clear_search,
        ).pack(side="right")

        dropdown_row = ctk.CTkFrame(si, fg_color="transparent")
        dropdown_row.pack(fill="x")

        # Level filter
        self._level_menu = ctk.CTkOptionMenu(
            dropdown_row,
            values=["All", "ERROR", "WARN", "INFO"],
            command=self._on_level_change,
            width=140, height=36, corner_radius=8,
            fg_color=BG_INPUT, button_color="#1a1c24",
            button_hover_color="#2a2c36",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY, dropdown_fg_color=BG_CARD,
        )
        self._level_menu.set("All Levels")
        self._level_menu.pack(side="left", padx=(0, 8))

        # Type filter (populated when data arrives)
        self._type_menu = ctk.CTkOptionMenu(
            dropdown_row,
            values=["All Types"],
            command=self._on_type_change,
            width=180, height=36, corner_radius=8,
            fg_color=BG_INPUT, button_color="#1a1c24",
            button_hover_color="#2a2c36",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY, dropdown_fg_color=BG_CARD,
        )
        self._type_menu.set("All Types")
        self._type_menu.pack(side="left", padx=(0, 8))

        # Refresh indicator
        self._updated_lbl = ctk.CTkLabel(
            dropdown_row, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self._updated_lbl.pack(side="right")

        # ── Analytics Cards ───────────────────────────────────────
        self._analytics_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._analytics_frame.pack(fill="x", padx=24, pady=(12, 0))
        for i in range(3):
            self._analytics_frame.columnconfigure(i, weight=1, uniform="an")

        self._analytics_labels: dict = {}
        placeholder = [
            ("Total Errors",        "—",  "loading…",  RED,    "^"),
            ("Warnings",            "—",  "loading…",  YELLOW, "v"),
            ("Most Affected Module","—",  "loading…",  ORANGE,  None),
        ]
        for col, (title, value, sub, color, icon) in enumerate(placeholder):
            card = ctk.CTkFrame(self._analytics_frame, fg_color=BG_CARD,
                                corner_radius=16, border_width=1, border_color=BORDER)
            card.grid(row=0, column=col, padx=6, sticky="nsew")
            ci = ctk.CTkFrame(card, fg_color="transparent")
            ci.pack(fill="x", padx=16, pady=14)

            top = ctk.CTkFrame(ci, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                         text_color=TEXT_SECONDARY).pack(side="left")
            if icon:
                ctk.CTkLabel(top, text=icon, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                             text_color=color).pack(side="right")

            val_lbl = ctk.CTkLabel(ci, text=value,
                                   font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
                                   text_color=TEXT_PRIMARY, anchor="w")
            val_lbl.pack(fill="x", pady=(6, 0))
            sub_lbl = ctk.CTkLabel(ci, text=sub,
                                   font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                                   text_color=color, anchor="w")
            sub_lbl.pack(fill="x")
            self._analytics_labels[col] = (val_lbl, sub_lbl, color)

        # ── Log Table ─────────────────────────────────────────────
        self._table_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16,
                                        border_width=1, border_color=BORDER)
        self._table_card.pack(fill="x", padx=24, pady=(12, 0))

        header = ctk.CTkFrame(self._table_card, fg_color="transparent", height=40)
        header.pack(fill="x", padx=4)
        cols = [("Timestamp", 170), ("Level", 78), ("Module", 150),
                ("Type", 140), ("Message", 300)]
        for label, w in cols:
            ctk.CTkLabel(header, text=label, width=w,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                         text_color=TEXT_SECONDARY, anchor="w").pack(side="left", padx=10, pady=10)

        ctk.CTkFrame(self._table_card, height=1, fg_color=BORDER).pack(fill="x")

        # Rows container (rebuild on data update/filter/page)
        self._rows_frame = ctk.CTkFrame(self._table_card, fg_color="transparent")
        self._rows_frame.pack(fill="x")

        # ── Pagination ────────────────────────────────────────────
        self._pag_frame = ctk.CTkFrame(self._table_card, fg_color="transparent", height=50)
        self._pag_frame.pack(fill="x", padx=16, pady=8)
        self._pag_info   = ctk.CTkLabel(self._pag_frame, text="",
                                         font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                                         text_color=TEXT_SECONDARY)
        self._pag_info.pack(side="left")
        self._pag_btns_frame = ctk.CTkFrame(self._pag_frame, fg_color="transparent")
        self._pag_btns_frame.pack(side="right")

        ctk.CTkFrame(scroll, height=20, fg_color="transparent").pack()

    # ────────────────────────────────────────────────────────────────
    #  Data Fetching
    # ────────────────────────────────────────────────────────────────

    def _schedule_refresh(self):
        if self._destroyed:
            return
        self._update_id = self.after(_REFRESH_MS, self._refresh_tick)
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _refresh_tick(self):
        if self._destroyed:
            return
        threading.Thread(target=self._do_fetch, daemon=True).start()
        self._update_id = self.after(_REFRESH_MS, self._refresh_tick)

    def _do_fetch(self):
        try:
            from desktop import session
            user = session.get_user()
            params = {"uid": user.get("uid")} if user else {}
            resp = requests.get(f"{_API_BASE}/api/logs", params=params, timeout=3)
            if resp.status_code == 200 and not self._destroyed:
                data = resp.json()
                self.after(0, lambda: self._apply_data(data))
        except requests.exceptions.ConnectionError:
            if not self._destroyed:
                self.after(0, lambda: self._updated_lbl.configure(text="Backend offline"))
        except Exception:
            pass

    def _apply_data(self, data: dict):
        if self._destroyed:
            return

        self._all_entries = data.get("entries", [])
        self._updated_lbl.configure(
            text=f"Updated {datetime.now().strftime('%H:%M:%S')}"
        )

        # Update analytics
        ec = data.get("error_count", 0)
        wc = data.get("warn_count",  0)
        top_mod   = data.get("top_module",       "None")
        top_count = data.get("top_module_count", 0)
        total     = data.get("total", len(self._all_entries))

        analytics_data = [
            (str(ec), f"{ec} errors in {total} entries"),
            (str(wc), f"{wc} warnings active"),
            (top_mod, f"{top_count} errors logged"),
        ]
        for col, (val, sub) in enumerate(analytics_data):
            val_lbl, sub_lbl, color = self._analytics_labels[col]
            val_lbl.configure(text=val)
            sub_lbl.configure(text=sub)

        # Refresh type filter dropdown
        types = sorted(set(e.get("type", "") for e in self._all_entries if e.get("type")))
        self._type_menu.configure(values=["All Types"] + types)

        # Re-apply current filters
        self._apply_filters()

    # ────────────────────────────────────────────────────────────────
    #  Filtering & Search
    # ────────────────────────────────────────────────────────────────

    def _on_search_key(self, event=None):
        self._search_text  = self._search_entry.get().strip().lower()
        self._current_page = 0
        self._apply_filters()

    def _clear_search(self):
        self._search_entry.delete(0, "end")
        self._search_text  = ""
        self._level_filter = "All"
        self._type_filter  = "All Types"
        self._level_menu.set("All Levels")
        self._type_menu.set("All Types")
        self._current_page = 0
        self._apply_filters()

    def _on_level_change(self, val: str):
        self._level_filter = val
        self._current_page = 0
        self._apply_filters()

    def _on_type_change(self, val: str):
        self._type_filter  = val
        self._current_page = 0
        self._apply_filters()

    def _apply_filters(self):
        result = self._all_entries
        if self._level_filter not in ("All", "All Levels"):
            result = [e for e in result if e.get("level") == self._level_filter]
        if self._type_filter != "All Types":
            result = [e for e in result if e.get("type") == self._type_filter]
        if self._search_text:
            result = [
                e for e in result
                if self._search_text in e.get("module", "").lower()
                or self._search_text in e.get("type", "").lower()
                or self._search_text in e.get("msg", "").lower()
            ]
        self._filtered = result
        self._render_page()

    # ────────────────────────────────────────────────────────────────
    #  Table Rendering
    # ────────────────────────────────────────────────────────────────

    def _render_page(self):
        # Clear rows
        for w in self._rows_frame.winfo_children():
            w.destroy()

        total = len(self._filtered)
        total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        self._current_page = max(0, min(self._current_page, total_pages - 1))

        start = self._current_page * _PAGE_SIZE
        end   = min(start + _PAGE_SIZE, total)
        page_entries = self._filtered[start:end]

        if not page_entries:
            ctk.CTkLabel(
                self._rows_frame,
                text="No log entries match the current filter.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).pack(pady=20)
        else:
            for log in page_entries:
                row = ctk.CTkFrame(self._rows_frame, fg_color="transparent", height=40)
                row.pack(fill="x", padx=4)

                ctk.CTkLabel(
                    row, text=log.get("time", ""), width=170,
                    font=ctk.CTkFont(family="Courier", size=11),
                    text_color=TEXT_SECONDARY, anchor="w",
                ).pack(side="left", padx=10, pady=8)

                level = log.get("level", "INFO")
                lc, lb = LEVEL_COLORS.get(level, (TEXT_MUTED, BG_CARD_INNER))
                ctk.CTkLabel(
                    row, text=f" {level} ", width=78,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    text_color=lc, fg_color=lb, corner_radius=10,
                ).pack(side="left", padx=10, pady=8)

                ctk.CTkLabel(
                    row, text=log.get("module", ""), width=150,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).pack(side="left", padx=10, pady=8)

                err_type  = log.get("type", "") or "—"
                err_color = TEXT_SECONDARY if log.get("type") else TEXT_MUTED
                ctk.CTkLabel(
                    row, text=err_type, width=140,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=err_color, anchor="w",
                ).pack(side="left", padx=10, pady=8)

                ctk.CTkLabel(
                    row, text=log.get("msg", ""),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=TEXT_SECONDARY, anchor="w",
                ).pack(side="left", padx=10, pady=8, fill="x", expand=True)

                ctk.CTkFrame(self._rows_frame, height=1, fg_color=BORDER).pack(fill="x")

        # ── Pagination bar ────────────────────────────────────────
        self._pag_info.configure(
            text=f"Showing {start + 1}–{end} of {total} entries"
            if total > 0 else "No entries"
        )

        for w in self._pag_btns_frame.winfo_children():
            w.destroy()

        # Build page number buttons (show window of 5 around current)
        def _go(p):
            self._current_page = p
            self._render_page()

        # Prev button
        ctk.CTkButton(
            self._pag_btns_frame, text="<", width=34, height=34, corner_radius=8,
            fg_color="#1a1c24", hover_color="#2a2c36",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_SECONDARY,
            command=lambda: _go(max(0, self._current_page - 1)),
            state="normal" if self._current_page > 0 else "disabled",
        ).pack(side="left", padx=2)

        window_start = max(0, self._current_page - 2)
        window_end   = min(total_pages, window_start + 5)
        for p in range(window_start, window_end):
            is_active = p == self._current_page
            ctk.CTkButton(
                self._pag_btns_frame, text=str(p + 1), width=34, height=34, corner_radius=8,
                fg_color=ORANGE if is_active else "#1a1c24",
                hover_color="#ea6c10" if is_active else "#2a2c36",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=TEXT_PRIMARY if is_active else TEXT_SECONDARY,
                command=lambda pg=p: _go(pg),
            ).pack(side="left", padx=2)

        # Next button
        ctk.CTkButton(
            self._pag_btns_frame, text=">", width=34, height=34, corner_radius=8,
            fg_color="#1a1c24", hover_color="#2a2c36",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_SECONDARY,
            command=lambda: _go(min(total_pages - 1, self._current_page + 1)),
            state="normal" if self._current_page < total_pages - 1 else "disabled",
        ).pack(side="left", padx=2)

    # ────────────────────────────────────────────────────────────────
    #  Lifecycle
    # ────────────────────────────────────────────────────────────────

    def _on_destroy(self, event):
        if event.widget is self:
            self._destroyed = True
            if self._update_id:
                self.after_cancel(self._update_id)
