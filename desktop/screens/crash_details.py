"""
CrashSense — Crash Details Screen
===================================

Keeps the same layout as the original screen but populates every section
with REAL live data from the backend:

  ┌─────────────────────────────────────┐
  │  Alert selector (dropdown)          │
  ├─────────────────────────────────────┤
  │  Incident Header                    │  ← live alert (pid, type, severity)
  │  Crash Summary                      │  ← detector detail string
  │  AI-Based Root Cause Analysis       │  ← derived from alert type + evidence
  │  Process Activity Log               │  ← snapshot history as log lines
  │  Resource Metrics Chart             │  ← cpu / rss / threads over time
  └─────────────────────────────────────┘

Data sources:
  GET /api/process-alerts          → alert list
  GET /api/process-history/<pid>   → per-process snapshots for chart + log
"""

import threading
import customtkinter as ctk
import requests
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, RED, RED_BG, YELLOW, YELLOW_BG,
    BLUE, BLUE_BG, GREEN, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
)
from desktop.icons import get_icon

_API_BASE   = "http://127.0.0.1:5000"
_REFRESH_MS = 7000

_SEV_COLORS = {"critical": RED, "high": ORANGE, "medium": YELLOW, "low": BLUE}
_SEV_BG     = {"critical": "#2a0808", "high": "#2a1a08", "medium": "#2a2508", "low": "#0f1a2a"}
_SEV_BORDER = {"critical": "#5c1a1a", "high": "#5c3a0a", "medium": "#5c5c1a", "low": "#0a2a5c"}
_SEV_ICON   = {"critical": RED_BG,   "high": "#2a1a08",  "medium": YELLOW_BG, "low": BLUE_BG}

_TYPE_ICON = {
    "memory_leak":       "memory_leak",
    "cpu_runaway":       "cpu_runaway",
    "thread_explosion":  "thread_explosion",
    "high_thread_count": "thread_explosion",
    "fd_exhaustion":     "fd_exhaustion",
    "zombie":            "zombie",
    "oom_risk":          "oom_risk",
}
_TYPE_HUMAN = {
    "memory_leak":       "Memory Leak",
    "cpu_runaway":       "CPU Runaway",
    "thread_explosion":  "Thread Explosion",
    "high_thread_count": "High Thread Count",
    "fd_exhaustion":     "FD Exhaustion",
    "zombie":            "Zombie Process",
    "oom_risk":          "OOM Kill Risk",
}

# Root cause templates — derived from detector evidence, not hardcoded fake text
_ROOT_CAUSES = {
    "memory_leak": [
        ("RSS growing monotonically",
         "Linear regression on RSS over time shows a positive slope exceeding the configured threshold."),
        ("No memory reclamation observed",
         "At least 65% of consecutive RSS samples increased — no GC / free events detected."),
    ],
    "cpu_runaway": [
        ("Sustained CPU above threshold",
         "Process has held CPU usage above the configured limit for over 30 seconds."),
        ("No voluntary yield detected",
         "CPU usage remained elevated across all scan intervals — likely an infinite loop or spin-wait."),
    ],
    "thread_explosion": [
        ("Thread count growing rapidly",
         "Thread count increased by more than 100% within a 1-minute window."),
        ("Possible thread pool leak",
         "New threads are being spawned faster than they terminate."),
    ],
    "high_thread_count": [
        ("Absolute thread count exceeded threshold",
         "Thread count surpassed the configured maximum. Process may be leaking threads."),
    ],
    "fd_exhaustion": [
        ("File descriptors near ulimit",
         "Open FD count exceeds 80% of the process's soft ulimit."),
        ("Possible resource leak",
         "Files, sockets, or pipes are not being closed after use."),
    ],
    "zombie": [
        ("Process in zombie/defunct state",
         "The process has exited but its parent has not called wait() to reap it."),
        ("Parent signal handling issue",
         "Parent process is not handling SIGCHLD or is itself stuck."),
    ],
    "oom_risk": [
        ("Process using large fraction of total RAM",
         "Single process RSS exceeds the configured OOM risk threshold."),
        ("Linux OOM killer may intervene",
         "If system memory pressure increases, the kernel may forcibly terminate this process without warning."),
    ],
}


class CrashDetailsScreen(ctk.CTkFrame):
    """
    Live Crash Details screen.
    Keeps the same original visual structure but driven by real backend data.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        self._alerts:    list[dict] = []
        self._selected_idx = 0
        self._update_id  = None
        self._destroyed  = False
        self._chart_fig  = None
        self._icon_refs  = []

        self.bind("<Destroy>", self._on_destroy)
        self._build_skeleton()
        self._schedule_refresh()

    # ────────────────────────────────────────────────────────────────
    #  Skeleton (selector bar + scroll area)
    # ────────────────────────────────────────────────────────────────

    def _build_skeleton(self):
        # ── Selector bar ──────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0)
        top.pack(fill="x")
        inner_top = ctk.CTkFrame(top, fg_color="transparent")
        inner_top.pack(fill="x", padx=24, pady=10)

        ctk.CTkLabel(
            inner_top, text="Viewing Alert:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        self._selector = ctk.CTkOptionMenu(
            inner_top,
            values=["No alerts detected"],
            command=self._on_select,
            width=380, height=30,
            fg_color=BG_CARD_INNER, button_color=BG_CARD_INNER,
            button_hover_color="#2a2c36", dropdown_fg_color=BG_CARD,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        )
        self._selector.pack(side="left", padx=(10, 0))

        self._updated_lbl = ctk.CTkLabel(
            inner_top, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self._updated_lbl.pack(side="right")

        # ── Scrollable content area ───────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_ROOT,
            scrollbar_button_color="#1e2028",
            scrollbar_button_hover_color="#2a2c36",
        )
        self._scroll.pack(fill="both", expand=True)
        self._scroll.bind_all("<Button-4>", lambda e: self._scroll._parent_canvas.yview_scroll(-3, "units"))
        self._scroll.bind_all("<Button-5>", lambda e: self._scroll._parent_canvas.yview_scroll( 3, "units"))

        self._render_empty()

    # ────────────────────────────────────────────────────────────────
    #  Data
    # ────────────────────────────────────────────────────────────────

    def _schedule_refresh(self):
        if self._destroyed:
            return
        self._update_id = self.after(_REFRESH_MS, self._refresh_tick)
        threading.Thread(target=self._fetch_alerts, daemon=True).start()

    def _refresh_tick(self):
        if self._destroyed:
            return
        threading.Thread(target=self._fetch_alerts, daemon=True).start()
        self._update_id = self.after(_REFRESH_MS, self._refresh_tick)

    def _fetch_alerts(self):
        try:
            resp = requests.get(f"{_API_BASE}/api/process-alerts", timeout=3)
            if resp.status_code == 200:
                alerts = resp.json().get("alerts", [])
                if not self._destroyed:
                    self.after(0, lambda: self._apply_alerts(alerts))
        except requests.exceptions.ConnectionError:
            if not self._destroyed:
                self.after(0, lambda: self._updated_lbl.configure(text="Backend offline"))
        except Exception:
            pass

    def _apply_alerts(self, alerts: list[dict]):
        if self._destroyed:
            return

        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        self._alerts = sorted(alerts, key=lambda a: sev_order.get(a.get("severity", "low"), 3))

        self._updated_lbl.configure(text=f"Updated {datetime.now().strftime('%H:%M:%S')}")

        if not self._alerts:
            self._selector.configure(values=["No alerts detected"])
            self._selector.set("No alerts detected")
            self._render_empty()
            return

        labels = [self._alert_label(a) for a in self._alerts]
        self._selector.configure(values=labels)
        # Keep current selection if still valid
        if self._selected_idx >= len(self._alerts):
            self._selected_idx = 0
        self._selector.set(labels[self._selected_idx])

        # Load history for the selected alert
        self._load_detail(self._alerts[self._selected_idx])

    def _on_select(self, label: str):
        labels = [self._alert_label(a) for a in self._alerts]
        if label in labels:
            self._selected_idx = labels.index(label)
            self._load_detail(self._alerts[self._selected_idx])

    @staticmethod
    def _alert_label(a: dict) -> str:
        sev  = a.get("severity", "low").upper()
        name = a.get("name", "?")
        pid  = a.get("pid", "?")
        typ  = _TYPE_HUMAN.get(a.get("type", ""), a.get("type", "?"))
        return f"[{sev}] {typ} — {name} (PID {pid})"

    def _load_detail(self, alert: dict):
        pid = alert.get("pid")
        if not pid:
            return
        def _fetch():
            try:
                resp = requests.get(f"{_API_BASE}/api/process-history/{pid}", timeout=3)
                if resp.status_code == 200 and not self._destroyed:
                    data = resp.json()
                    self.after(0, lambda: self._render_detail(alert, data))
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()

    # ────────────────────────────────────────────────────────────────
    #  Full-page Detail Render
    # ────────────────────────────────────────────────────────────────

    def _render_detail(self, alert: dict, history_data: dict):
        if self._destroyed:
            return

        if self._chart_fig:
            try: self._chart_fig.clf()
            except Exception: pass
            self._chart_fig = None

        for w in self._scroll.winfo_children():
            w.destroy()
        self._icon_refs.clear()

        sev    = alert.get("severity", "low")
        color  = _SEV_COLORS.get(sev, BLUE)
        border = _SEV_BORDER.get(sev, BORDER)
        icon_bg = _SEV_ICON.get(sev, BG_CARD_INNER)

        name     = alert.get("name",   "Unknown Process")
        pid      = alert.get("pid",    "?")
        atype    = alert.get("type",   "")
        title    = alert.get("title",  _TYPE_HUMAN.get(atype, "Crash Precursor"))
        detail   = alert.get("detail", "No details available.")
        metric   = alert.get("metric", "")
        time_str = alert.get("time_str", datetime.now().strftime("%H:%M:%S"))
        detected = datetime.now().strftime("%d %b %Y, %H:%M")

        # ── 1. Incident Header ────────────────────────────────────
        header_card = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        header_card.pack(fill="x", padx=24, pady=(16, 0))
        hi = ctk.CTkFrame(header_card, fg_color="transparent")
        hi.pack(fill="x", padx=20, pady=16)

        top = ctk.CTkFrame(hi, fg_color="transparent")
        top.pack(fill="x")

        icon_img = get_icon(_TYPE_ICON.get(atype, "active_alerts"), size=22, color=color)
        self._icon_refs.append(icon_img)
        icon_box = ctk.CTkFrame(top, width=48, height=48, corner_radius=12, fg_color=icon_bg)
        icon_box.pack(side="left")
        icon_box.pack_propagate(False)
        ctk.CTkLabel(icon_box, image=icon_img, text="").pack(expand=True)

        txt = ctk.CTkFrame(top, fg_color="transparent")
        txt.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(
            txt, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            txt, text=f"Detected at {time_str}  •  {detected}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")

        badge = ctk.CTkLabel(
            top, text=f"  {sev.upper()}  ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=color, fg_color=border, corner_radius=8, height=30,
        )
        badge.pack(side="right")

        ctk.CTkFrame(hi, height=1, fg_color=BORDER).pack(fill="x", pady=(12, 10))

        info_row = ctk.CTkFrame(hi, fg_color="transparent")
        info_row.pack(fill="x")
        for i in range(3):
            info_row.columnconfigure(i, weight=1)

        meta = [
            ("Process Name",   name),
            ("PID",            str(pid)),
            ("Key Metric",     metric if metric else "N/A"),
        ]
        for col, (label, val) in enumerate(meta):
            f = ctk.CTkFrame(info_row, fg_color="transparent")
            f.grid(row=0, column=col, sticky="w", padx=4)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")
            ctk.CTkLabel(f, text=val,   font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")

        # ── 2. Crash Summary ──────────────────────────────────────
        sum_card = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        sum_card.pack(fill="x", padx=24, pady=(12, 0))
        si = ctk.CTkFrame(sum_card, fg_color="transparent")
        si.pack(fill="x", padx=20, pady=16)

        h = ctk.CTkFrame(si, fg_color="transparent")
        h.pack(fill="x")
        info_icon = get_icon("info_circle", size=18, color=ORANGE)
        self._icon_refs.append(info_icon)
        ctk.CTkLabel(h, image=info_icon, text="").pack(side="left")
        ctk.CTkLabel(h, text="  Alert Summary", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        ctk.CTkLabel(
            si, text=detail,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, wraplength=700, justify="left",
        ).pack(fill="x", pady=(8, 0))

        # ── 3. AI Root Cause Analysis ─────────────────────────────
        ai_card = ctk.CTkFrame(self._scroll, fg_color="#1a1208", corner_radius=16, border_width=1, border_color="#3d2a0a")
        ai_card.pack(fill="x", padx=24, pady=(12, 0))
        ai = ctk.CTkFrame(ai_card, fg_color="transparent")
        ai.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(
            ai, text="AI-Based Root Cause Analysis",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 8))

        root_causes = _ROOT_CAUSES.get(atype, [
            (title, detail),
            ("Severity: " + sev.upper(), f"This alert has been classified as {sev} severity by the detection engine."),
        ])

        for i, (rc_title, rc_detail) in enumerate(root_causes, 1):
            row = ctk.CTkFrame(ai, fg_color="transparent")
            row.pack(fill="x", pady=4)

            num = ctk.CTkFrame(row, width=28, height=28, corner_radius=14, fg_color=ORANGE)
            num.pack(side="left", anchor="n", pady=2)
            num.pack_propagate(False)
            ctk.CTkLabel(num, text=str(i), font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#ffffff").pack(expand=True)

            t = ctk.CTkFrame(row, fg_color="transparent")
            t.pack(side="left", padx=(10, 0), fill="x", expand=True)
            ctk.CTkLabel(t, text=rc_title, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
            ctk.CTkLabel(t, text=rc_detail, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY, wraplength=620, justify="left", anchor="w").pack(fill="x")

        # ── 4. Process Activity Log ───────────────────────────────
        log_card = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        log_card.pack(fill="x", padx=24, pady=(12, 0))
        li = ctk.CTkFrame(log_card, fg_color="transparent")
        li.pack(fill="x", padx=20, pady=16)

        log_hdr = ctk.CTkFrame(li, fg_color="transparent")
        log_hdr.pack(fill="x")
        logs_icon = get_icon("logs", size=18, color=ORANGE)
        self._icon_refs.append(logs_icon)
        ctk.CTkLabel(log_hdr, image=logs_icon, text="").pack(side="left")
        ctk.CTkLabel(log_hdr, text="  Process Activity Log", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        log_box = ctk.CTkFrame(li, fg_color=BG_CARD_INNER, corner_radius=10)
        log_box.pack(fill="x", pady=(8, 0))

        # Build log lines from snapshot history
        history = history_data.get("history", [])
        log_entries = self._build_log_entries(alert, history)

        level_colors = {
            "CRIT": (RED,    RED_BG),
            "WARN": (YELLOW, YELLOW_BG),
            "INFO": (BLUE,   BLUE_BG),
            "OK":   (GREEN,  "#0a2a0a"),
        }

        for entry in log_entries[-15:]:   # Show last 15 entries
            row = ctk.CTkFrame(log_box, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=3)

            ctk.CTkLabel(row, text=entry["time"], font=ctk.CTkFont(family="Courier", size=11), text_color=TEXT_MUTED, width=70).pack(side="left")

            lc, lb = level_colors.get(entry["level"], (TEXT_MUTED, BG_CARD_INNER))
            ctk.CTkLabel(row, text=f" {entry['level']} ", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=lc, fg_color=lb, corner_radius=4, width=50).pack(side="left", padx=(8, 8))

            ctk.CTkLabel(row, text=entry["msg"], font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY, anchor="w").pack(side="left", fill="x", expand=True)

        # ── 5. Resource Metrics Chart ─────────────────────────────
        chart_card = ctk.CTkFrame(self._scroll, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        chart_card.pack(fill="x", padx=24, pady=(12, 24))
        ctk.CTkLabel(
            chart_card, text="Resource Metrics at Time of Alert",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=20, pady=(16, 0))

        self._render_chart(chart_card, history, color)

    # ────────────────────────────────────────────────────────────────
    #  Log Entry Builder
    # ────────────────────────────────────────────────────────────────

    def _build_log_entries(self, alert: dict, history: list[dict]) -> list[dict]:
        """Convert process snapshot history into log-like entries."""
        entries = []
        atype  = alert.get("type", "")
        metric = alert.get("metric", "")

        cpu_threshold  = 80.0
        mem_threshold  = 200.0   # MB
        thr_threshold  = 40

        for snap in history:
            ts  = snap.get("timestamp", 0)
            t   = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            cpu = snap.get("cpu_percent", 0)
            mem = snap.get("rss_mb", 0)
            thr = snap.get("num_threads", 0)
            fds = snap.get("num_fds", 0)
            sts = snap.get("status", "")

            if sts in ("zombie", "defunct"):
                entries.append({"time": t, "level": "CRIT", "msg": f"Process status: ZOMBIE/DEFUNCT — not collecting resources"})
            elif cpu > cpu_threshold:
                entries.append({"time": t, "level": "WARN", "msg": f"CPU spike: {cpu:.1f}%  |  RSS: {mem:.0f} MB  |  Threads: {thr}"})
            elif atype == "memory_leak" and mem > mem_threshold:
                entries.append({"time": t, "level": "WARN", "msg": f"RSS growing: {mem:.0f} MB  |  CPU: {cpu:.1f}%  |  Threads: {thr}"})
            elif atype in ("thread_explosion", "high_thread_count") and thr > thr_threshold:
                entries.append({"time": t, "level": "WARN", "msg": f"Thread count elevated: {thr}  |  CPU: {cpu:.1f}%  |  RSS: {mem:.0f} MB"})
            elif atype == "fd_exhaustion" and fds > 100:
                entries.append({"time": t, "level": "WARN", "msg": f"FD count: {fds}  |  CPU: {cpu:.1f}%  |  RSS: {mem:.0f} MB"})
            elif atype == "oom_risk" and mem > 100:
                entries.append({"time": t, "level": "CRIT", "msg": f"Memory critical: {mem:.0f} MB RSS  |  CPU: {cpu:.1f}%  |  Threads: {thr}"})
            else:
                entries.append({"time": t, "level": "INFO", "msg": f"CPU: {cpu:.1f}%  |  RSS: {mem:.0f} MB  |  Threads: {thr}  |  FDs: {fds}"})

        # Append the alert detection event
        entries.append({
            "time":  alert.get("time_str", datetime.now().strftime("%H:%M:%S")),
            "level": "CRIT" if alert.get("severity") in ("critical", "high") else "WARN",
            "msg":   f"ALERT FIRED: {alert.get('title', 'Crash precursor')}  [{metric}]",
        })

        return entries

    # ────────────────────────────────────────────────────────────────
    #  Resource Chart
    # ────────────────────────────────────────────────────────────────

    def _render_chart(self, parent, history: list[dict], accent_color: str):
        # If no data at all, show a helpful message
        if not history:
            ctk.CTkLabel(
                parent,
                text="History accumulates after the first few scan cycles (~15 s).\n"
                     "Leave the app running and revisit this screen.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED, justify="center",
            ).pack(pady=20, padx=20)
            return

        try:
            # ── Extract series ───────────────────────────────────────
            ts   = [h["timestamp"]   for h in history]
            cpu  = [h["cpu_percent"] for h in history]
            mem  = [h["rss_mb"]      for h in history]
            thrd = [h["num_threads"] for h in history]

            # Need at least 2 points to draw a line — duplicate the single point if needed
            if len(ts) == 1:
                ts   = [ts[0],   ts[0]   + 3]
                cpu  = [cpu[0],  cpu[0]]
                mem  = [mem[0],  mem[0]]
                thrd = [thrd[0], thrd[0]]

            # X axis: elapsed seconds
            t0 = ts[0]
            xs = [(t - t0) for t in ts]
            x_labels = [datetime.fromtimestamp(t).strftime("%H:%M:%S") for t in ts]

            # ── Build figure ─────────────────────────────────────────
            fig = Figure(figsize=(8, 3.2), dpi=100)
            fig.patch.set_facecolor(BG_CARD)
            self._chart_fig = fig

            # Dual Y-axis: CPU% + Threads (left)  |  RSS MB (right, different scale)
            ax1 = fig.add_subplot(111)
            ax1.set_facecolor(BG_CARD)
            ax2 = ax1.twinx()

            # CPU % — primary left
            ax1.plot(xs, cpu, color=ORANGE, linewidth=2, label="CPU %", zorder=3)
            ax1.fill_between(xs, cpu, alpha=0.12, color=ORANGE)

            # Thread count — also left axis
            ax1.plot(xs, thrd, color="#fbbf24", linewidth=1.5,
                     label="Threads", linestyle=":", zorder=2)

            # RSS MB — secondary right axis
            ax2.plot(xs, mem, color=accent_color, linewidth=2,
                     label="RSS MB", linestyle="--", zorder=2)
            ax2.fill_between(xs, mem, alpha=0.08, color=accent_color)
            ax2.set_ylabel("RSS MB", color=TEXT_MUTED, fontsize=8)
            ax2.tick_params(colors=TEXT_MUTED, labelsize=7)
            for sp in ax2.spines.values():
                sp.set_color(BORDER)

            # X-axis: show real clock times, spaced sensibly
            n    = len(xs)
            step = max(1, n // 6)
            ticks = list(range(0, n, step))
            ax1.set_xticks([xs[i] for i in ticks])
            ax1.set_xticklabels([x_labels[i] for i in ticks],
                                 rotation=20, ha="right", fontsize=7)

            ax1.set_ylabel("CPU % / Threads", color=TEXT_MUTED, fontsize=8)
            ax1.tick_params(colors=TEXT_MUTED, labelsize=7)

            # Combined legend
            l1, lb1 = ax1.get_legend_handles_labels()
            l2, lb2 = ax2.get_legend_handles_labels()
            ax1.legend(l1 + l2, lb1 + lb2,
                       facecolor=BG_CARD, edgecolor=BORDER,
                       labelcolor=TEXT_SECONDARY, fontsize=8, loc="upper left")

            for sp in ax1.spines.values():
                sp.set_color(BORDER)
            ax1.grid(True, color="#1e1e2a", linewidth=0.5, alpha=0.5)
            fig.tight_layout(pad=1.5)

            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.get_tk_widget().pack(fill="x", padx=12, pady=(4, 16))
            canvas.draw()

        except Exception as exc:
            ctk.CTkLabel(
                parent, text=f"Chart rendering error: {exc}",
                font=ctk.CTkFont(size=10), text_color=TEXT_MUTED,
            ).pack(pady=10, padx=20)

    # ────────────────────────────────────────────────────────────────
    #  Empty state
    # ────────────────────────────────────────────────────────────────

    def _render_empty(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(expand=True, pady=80)
        icon = get_icon("checkmark", size=48, color=GREEN)
        self._icon_refs.append(icon)
        ctk.CTkLabel(frame, image=icon, text="").pack()
        ctk.CTkLabel(frame, text="No Active Crash Precursors",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=GREEN).pack(pady=(12, 4))
        ctk.CTkLabel(frame, text="When the monitor detects a problem, details will appear here automatically.",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                     text_color=TEXT_MUTED).pack()

    # ────────────────────────────────────────────────────────────────
    #  Lifecycle
    # ────────────────────────────────────────────────────────────────

    def _on_destroy(self, event):
        if event.widget is self:
            self._destroyed = True
            if self._update_id:
                self.after_cancel(self._update_id)
            if self._chart_fig:
                try: self._chart_fig.clf()
                except Exception: pass
