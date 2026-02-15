"""
CrashSense — Custom Widgets
Reusable CustomTkinter widgets for the monitoring dashboard.
"""

import customtkinter as ctk


class MetricCard(ctk.CTkFrame):
    """
    A sleek metric card showing an icon, label, current value,
    and a color-coded progress bar.
    """

    # Color presets for different metric types
    THEMES = {
        "cpu":     {"accent": "#00d4ff", "gradient": "#0097b2"},
        "memory":  {"accent": "#ff00aa", "gradient": "#b20077"},
        "disk":    {"accent": "#ffaa00", "gradient": "#b27700"},
        "network": {"accent": "#00ff88", "gradient": "#00b25e"},
    }

    def __init__(self, master, title: str, icon: str, theme_key: str = "cpu", **kwargs):
        super().__init__(
            master,
            corner_radius=16,
            fg_color=("#1e1e2e", "#1e1e2e"),
            border_width=1,
            border_color=("#2a2a3e", "#2a2a3e"),
            **kwargs,
        )

        theme = self.THEMES.get(theme_key, self.THEMES["cpu"])
        self._accent = theme["accent"]

        # ── Icon + Title row ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 4))

        icon_label = ctk.CTkLabel(
            header,
            text=icon,
            font=ctk.CTkFont(size=22),
            text_color=self._accent,
        )
        icon_label.pack(side="left")

        title_label = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#8888aa",
        )
        title_label.pack(side="left", padx=(8, 0))

        # ── Value ──
        self._value_label = ctk.CTkLabel(
            self,
            text="—",
            font=ctk.CTkFont(family="Inter", size=36, weight="bold"),
            text_color="#e0e0f0",
        )
        self._value_label.pack(padx=18, anchor="w")

        # ── Sub-label ──
        self._sub_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color="#666688",
        )
        self._sub_label.pack(padx=18, anchor="w")

        # ── Progress bar ──
        self._progress = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            progress_color=self._accent,
            fg_color="#12121e",
        )
        self._progress.pack(fill="x", padx=18, pady=(8, 16))
        self._progress.set(0)

    def update_value(self, value_text: str, sub_text: str = "", progress: float = 0.0):
        """
        Update the card display.
        :param value_text: main value string, e.g. '42.3 %'
        :param sub_text: secondary info line
        :param progress: 0.0 – 1.0 for the progress bar
        """
        self._value_label.configure(text=value_text)
        self._sub_label.configure(text=sub_text)
        self._progress.set(max(0.0, min(1.0, progress)))


class StatusBar(ctk.CTkFrame):
    """
    Bottom status bar with a colored health dot, uptime counter, and version label.
    """

    def __init__(self, master, version: str = "0.1.0", **kwargs):
        super().__init__(
            master,
            height=36,
            corner_radius=0,
            fg_color=("#131320", "#131320"),
            **kwargs,
        )

        # Prevent the frame from shrinking
        self.pack_propagate(False)

        # ── Health dot ──
        self._dot = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color="#555555",
            width=20,
        )
        self._dot.pack(side="left", padx=(12, 0))

        self._status_label = ctk.CTkLabel(
            self,
            text="Starting…",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color="#888899",
        )
        self._status_label.pack(side="left", padx=(4, 0))

        # ── Version (right side) ──
        ver_label = ctk.CTkLabel(
            self,
            text=f"v{version}",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color="#44445a",
        )
        ver_label.pack(side="right", padx=12)

        # ── Uptime (right side) ──
        self._uptime_label = ctk.CTkLabel(
            self,
            text="Uptime: 0 s",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color="#66667a",
        )
        self._uptime_label.pack(side="right", padx=12)

    def set_online(self):
        self._dot.configure(text_color="#00ff88")
        self._status_label.configure(text="Monitoring Active")

    def set_offline(self):
        self._dot.configure(text_color="#ff4444")
        self._status_label.configure(text="Offline")

    def update_uptime(self, seconds: int):
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            text = f"Uptime: {hrs}h {mins}m {secs}s"
        elif mins > 0:
            text = f"Uptime: {mins}m {secs}s"
        else:
            text = f"Uptime: {secs}s"
        self._uptime_label.configure(text=text)
