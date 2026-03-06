"""
CrashSense — Enhanced Prediction Dashboard
============================================

Live per-process crash detection dashboard with:
  - System Health Gauge (Speedometer-style)
  - Health Score Trend Chart
  - Live Alert Feed with Per-Process Evidence
  - Top Processes Table
"""

import customtkinter as ctk
import requests
import threading
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import numpy as np

from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, RED, YELLOW, GREEN,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY, BLUE,
)
from desktop.icons import get_icon

_API_BASE = "http://127.0.0.1:5000"
_REFRESH_MS = 5000

# ─────────────────────────────────────────────────────────────────
#  Visual Config
# ─────────────────────────────────────────────────────────────────

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

# Map alert types to icon names in icons.py
_TYPE_ICON_NAMES = {
    "memory_leak":       "memory_leak",
    "cpu_runaway":       "cpu_runaway",
    "thread_explosion":  "thread_explosion",
    "high_thread_count": "high_thread_count",
    "fd_exhaustion":     "fd_exhaustion",
    "zombie":            "zombie",
    "oom_risk":          "oom_risk",
}

class PredictionScreen(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)
        self._update_id = None
        self._destroyed = False
        self._last_score = 100
        
        self._build_ui()
        self.bind("<Destroy>", self._on_destroy)
        self._schedule_update()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_ROOT,
            scrollbar_button_color="#1e2028",
            scrollbar_button_hover_color="#2a2c36",
        )
        scroll.pack(fill="both", expand=True)

        def _scroll_up(e):
            try: scroll._parent_canvas.yview_scroll(-3, "units")
            except Exception: pass
        def _scroll_down(e):
            try: scroll._parent_canvas.yview_scroll(3, "units")
            except Exception: pass
        scroll.bind_all("<Button-4>", _scroll_up)
        scroll.bind_all("<Button-5>", _scroll_down)

        self._scroll = scroll

        # ─── Top Row: Gauge and Trend Chart ─────────────────────
        top_grid = ctk.CTkFrame(scroll, fg_color="transparent")
        top_grid.pack(fill="x", padx=24, pady=(20, 0))
        top_grid.columnconfigure(0, weight=1)
        top_grid.columnconfigure(1, weight=2)

        # Gauge Card
        gauge_card = ctk.CTkFrame(top_grid, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        gauge_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(gauge_card, text="SYSTEM HEALTH", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_MUTED).pack(pady=(15, 0))
        
        self._canvas_gauge = ctk.CTkCanvas(gauge_card, width=200, height=120, bg=BG_CARD, highlightthickness=0)
        self._canvas_gauge.pack(pady=10)
        
        self._score_label = ctk.CTkLabel(gauge_card, text="100", font=ctk.CTkFont(family=FONT_FAMILY, size=32, weight="bold"), text_color=GREEN)
        self._score_label.pack(pady=(0, 5))
        
        self._health_status_label = ctk.CTkLabel(gauge_card, text="HEALTHY", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=GREEN)
        self._health_status_label.pack(pady=(0, 15))

        # Trend Chart Card
        chart_card = ctk.CTkFrame(top_grid, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        chart_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(chart_card, text="HEALTH TREND (LATEST 3 MIN)", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(pady=(10, 0), padx=15, anchor="w")
        
        self._fig, self._ax = plt.subplots(figsize=(5, 2), dpi=100)
        self._fig.patch.set_facecolor(BG_CARD)
        self._ax.set_facecolor(BG_CARD)
        self._ax.tick_params(colors=TEXT_MUTED, labelsize=8)
        self._ax.spines['bottom'].set_color(BORDER)
        self._ax.spines['top'].set_visible(False)
        self._ax.spines['right'].set_visible(False)
        self._ax.spines['left'].set_color(BORDER)
        
        self._canvas_chart = FigureCanvasTkAgg(self._fig, master=chart_card)
        self._canvas_chart.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # ─── Alert Feed Section ────────────────────────────────
        alerts_header = ctk.CTkFrame(scroll, fg_color="transparent")
        alerts_header.pack(fill="x", padx=24, pady=(20, 5))
        
        ctk.CTkLabel(alerts_header, text="ACTIVE CRASH PRECURSORS", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self._alert_count_badge = ctk.CTkLabel(alerts_header, text="0", fg_color=BG_CARD_INNER, corner_radius=6, font=ctk.CTkFont(size=10, weight="bold"), width=30)
        self._alert_count_badge.pack(side="left", padx=10)

        self._alerts_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self._alerts_container.pack(fill="x", padx=24)

        # ─── Top Processes Section ─────────────────────────────
        procs_title = ctk.CTkLabel(scroll, text="TOP PROCESSES BY RISK SCORE", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY, anchor="w")
        procs_title.pack(fill="x", padx=24, pady=(20, 5))

        self._procs_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        self._procs_card.pack(fill="x", padx=24, pady=(0, 24))

        # Table Header
        th = ctk.CTkFrame(self._procs_card, fg_color=BG_CARD_INNER, corner_radius=8)
        th.pack(fill="x", padx=12, pady=(12, 4))
        for i, h in enumerate(["Process", "PID", "CPU%", "Mem%", "RSS", "Threads"]):
            th.columnconfigure(i, weight=1 if i > 0 else 3, uniform="col")
            ctk.CTkLabel(th, text=h, font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED, anchor="w" if i==0 else "center").grid(row=0, column=i, padx=8, pady=6, sticky="nsew")

        self._procs_body = ctk.CTkFrame(self._procs_card, fg_color="transparent")
        self._procs_body.pack(fill="x", padx=12, pady=(0, 12))

        self._draw_gauge(100)

    def _draw_gauge(self, score):
        """Draws a semi-circular gauge on the canvas."""
        self._canvas_gauge.delete("all")
        w, h = 200, 120
        cx, cy = w/2, h-10
        r = 80
        
        # Background arc
        self._canvas_gauge.create_arc(cx-r, cy-r, cx+r, cy+r, start=0, extent=180, outline="#1e2028", width=12, style="arc")
        
        # Active arc
        color = GREEN if score >= 80 else ORANGE if score >= 50 else RED
        extent = (score / 100) * 180
        self._canvas_gauge.create_arc(cx-r, cy-r, cx+r, cy+r, start=180, extent=-extent, outline=color, width=12, style="arc")
        
        # Needle
        angle = np.pi - (max(0.001, score) / 100) * np.pi
        nx = cx + (r-15) * np.cos(angle)
        ny = cy - (r-15) * np.sin(angle)
        self._canvas_gauge.create_line(cx, cy, nx, ny, fill=TEXT_PRIMARY, width=3, capstyle="round")
        self._canvas_gauge.create_oval(cx-5, cy-5, cx+5, cy+5, fill=TEXT_PRIMARY, outline=BG_CARD)

    def _animate_gauge(self, target_score, current_score=None, steps=30, current_step=0):
        if self._destroyed: return
        
        if current_score is None:
            current_score = getattr(self, '_last_score', 100)
            
        if current_score == target_score and current_step == 0:
            self._draw_gauge(target_score)
            return

        if current_step > steps:
            self._last_score = target_score
            self._draw_gauge(target_score)
            return

        # Interpolate using ease-out-back for speedometer bounce effect
        t = current_step / steps
        c1 = 1.70158
        c3 = c1 + 1
        
        ease = 1 + c3 * ((t - 1) ** 3) + c1 * ((t - 1) ** 2)
        
        interpolated = current_score + (target_score - current_score) * ease
        
        # Clamp slightly outside 0-100 to allow bounce but not crazy clipping
        interpolated = max(-5.0, min(105.0, interpolated))
        self._draw_gauge(interpolated)
        
        self.after(16, self._animate_gauge, target_score, current_score, steps, current_step + 1)

    def _schedule_update(self):
        if self._destroyed: return
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        try:
            alerts  = requests.get(f"{_API_BASE}/api/process-alerts",       timeout=3).json()
            stats   = requests.get(f"{_API_BASE}/api/process-stats",         timeout=3).json()
            trend   = requests.get(f"{_API_BASE}/api/process-alerts/trend",  timeout=3).json()
            ml_stat = requests.get(f"{_API_BASE}/api/ml-status",             timeout=3).json()

            if not self._destroyed:
                self.after(0, lambda: self._update_ui(alerts, stats, trend, ml_stat))
        except requests.exceptions.ConnectionError:
            if not self._destroyed:
                self.after(0, lambda: self._update_ui({"summary": {"status": "backend offline", "health_score": 0}, "alerts": []}, [], []))
        except Exception: 
            pass

        if not self._destroyed:
            self.after(_REFRESH_MS, self._schedule_update)

    def _update_ui(self, alerts_data, stats_data, trend_data, ml_stat=None):
        summary = alerts_data.get("summary", {})
        score  = summary.get("health_score", 100)
        status = summary.get("status", "healthy").upper()

        ml_enabled = (ml_stat or {}).get("enabled", True)

        # Update Gauge
        self._animate_gauge(score)
        score_color = GREEN if score >= 80 else ORANGE if score >= 50 else RED
        self._score_label.configure(text=str(int(score)), text_color=score_color)
        if not ml_enabled:
            self._health_status_label.configure(text="ML DISABLED", text_color=TEXT_MUTED)
        else:
            self._health_status_label.configure(text=status, text_color=score_color)
        
        # Update Trend Chart
        self._ax.clear()
        if trend_data:
            scores = [p['score'] for p in trend_data]
            times = [datetime.fromtimestamp(p['timestamp']) for p in trend_data]
            self._ax.plot(times, scores, color=BLUE, linewidth=2, marker='o', markersize=3)
            self._ax.fill_between(times, scores, 0, color=BLUE, alpha=0.1)
            self._ax.set_ylim(0, 105)
            self._ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self._ax.grid(True, linestyle='--', alpha=0.1)
        self._canvas_chart.draw()

        # Update Alerts
        self._alert_count_badge.configure(text=str(len(alerts_data.get("alerts", []))))
        for child in self._alerts_container.winfo_children(): child.destroy()
        
        alerts = alerts_data.get("alerts", [])
        if not alerts:
            card = ctk.CTkFrame(self._alerts_container, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
            card.pack(fill="x", pady=5)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(pady=15)
            _icon = get_icon("checkmark", size=28, color=GREEN)
            ctk.CTkLabel(row, image=_icon, text="").pack(side="left")
            ctk.CTkLabel(row, text="  All processes behaving normally", font=ctk.CTkFont(size=13), text_color=GREEN).pack(side="left")
        else:
            for alert in alerts:
                self._create_alert_card(alert)

        # Update Table
        for child in self._procs_body.winfo_children(): child.destroy()
        
        for i, p in enumerate(stats_data[:10]):
            row_bg = BG_CARD_INNER if i % 2 == 0 else "transparent"
            row = ctk.CTkFrame(self._procs_body, fg_color=row_bg, corner_radius=6)
            row.pack(fill="x", pady=1)
            
            # Values: Process, PID, CPU%, Mem%, RSS, Threads
            vals = [
                str(p['name']), 
                str(p['pid']), 
                f"{p['cpu_percent']:.1f}", 
                f"{p['memory_percent']:.1f}", 
                f"{p['rss_mb']:.0f}MB", 
                str(p['num_threads'])
            ]
            
            for j, val in enumerate(vals):
                row.columnconfigure(j, weight=1 if j > 0 else 3, uniform="col")
                
                # Style logic
                alignment = "w" if j == 0 else "center"
                color = TEXT_PRIMARY if j == 0 else TEXT_SECONDARY
                
                if j == 2 and p['cpu_percent'] > 50: color = ORANGE
                if j == 2 and p['cpu_percent'] > 80: color = RED
                
                if j == 3 and p['memory_percent'] > 50: color = ORANGE
                if j == 3 and p['memory_percent'] > 80: color = RED
                    
                lbl = ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=11), text_color=color, anchor=alignment)
                lbl.grid(row=0, column=j, padx=8, pady=6, sticky="nsew")

    def _create_alert_card(self, alert):
        sev   = alert.get("severity", "low")
        color = _SEV_COLORS.get(sev, BLUE)
        
        card = ctk.CTkFrame(self._alerts_container, fg_color=_SEV_BG.get(sev, BG_CARD),
                            corner_radius=12, border_width=1, border_color=color)
        card.pack(fill="x", pady=4)

        try:
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=15, pady=10)

            # ── Icon box ────────────────────────────────────────
            icon_name = _TYPE_ICON_NAMES.get(alert.get("type", ""), "active_alerts")
            icon_img  = get_icon(icon_name, size=26, color=color)
            type_box  = ctk.CTkFrame(inner, width=46, height=46, corner_radius=10, fg_color=BG_CARD_INNER)
            type_box.pack(side="left")
            type_box.pack_propagate(False)
            ctk.CTkLabel(type_box, image=icon_img, text="").pack(expand=True)

            # ── Details ─────────────────────────────────────────
            txt = ctk.CTkFrame(inner, fg_color="transparent")
            txt.pack(side="left", padx=15, fill="x", expand=True)

            title_row = ctk.CTkFrame(txt, fg_color="transparent")
            title_row.pack(fill="x")

            title  = alert.get("title",  alert.get("type", "Unknown Alert").replace("_", " ").title())
            name   = alert.get("name",   "Unknown")
            pid    = alert.get("pid",    "?")
            detail = alert.get("detail", "")
            metric = alert.get("metric", "")

            ctk.CTkLabel(title_row, text=title,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color).pack(side="left")
            ctk.CTkLabel(title_row, text=f" \u2022 {name} (PID {pid})",
                         font=ctk.CTkFont(size=11),
                         text_color=TEXT_MUTED).pack(side="left", padx=5)

            ctk.CTkLabel(txt, text=detail, font=ctk.CTkFont(size=11),
                         text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")

            # ── Right metric / time ──────────────────────────────
            info = ctk.CTkFrame(inner, fg_color="transparent")
            info.pack(side="right")
            ctk.CTkLabel(info, text=metric,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="e")
            ctk.CTkLabel(info, text=alert.get("time_str", ""),
                         font=ctk.CTkFont(size=10),
                         text_color=TEXT_MUTED).pack(anchor="e")

        except Exception as exc:
            # Fallback: show minimal error label so the card is never blank
            ctk.CTkLabel(card,
                         text=f"Alert ({alert.get('type', '?')}) rendering error: {exc}",
                         font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=10)

    def _on_destroy(self, event):
        if event.widget is self:
            self._destroyed = True
            if self._update_id: self.after_cancel(self._update_id)
            plt.close(self._fig)
