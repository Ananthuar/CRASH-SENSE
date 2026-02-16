"""
CrashSense — Settings Screen
==============================

Application settings panel with thresholds, ML toggle, notifications,
user management, and logout.
"""

import customtkinter as ctk
from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, RED, RED_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
)
from desktop.data import USERS
from desktop.icons import get_icon


class SettingsScreen(ctk.CTkFrame):
    """Settings panel — single scroll container."""

    def __init__(self, master, on_logout, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)
        self._on_logout = on_logout

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_ROOT, scrollbar_button_color="#1e2028", scrollbar_button_hover_color="#2a2c36")
        scroll.pack(fill="both", expand=True)
        scroll.bind_all("<Button-4>", lambda e: scroll._parent_canvas.yview_scroll(-3, "units"))
        scroll.bind_all("<Button-5>", lambda e: scroll._parent_canvas.yview_scroll(3, "units"))

        self._section_icons = []  # prevent GC

        # Section 1: Alert Thresholds
        self._section(scroll, "thresholds", "Alert Thresholds", "Configure system monitoring thresholds", self._build_thresholds)

        # Section 2: ML Prediction
        self._section(scroll, "ml_brain", "Machine Learning Prediction", "AI-powered crash prediction settings", self._build_ml)

        # Section 3: Notifications
        self._section(scroll, "notification_bell", "Notification Settings", "Configure how you receive alerts", self._build_notifications)

        # Section 4: User Management
        self._section(scroll, "user_group", "User Management", "Manage team access and permissions", self._build_users)

        # Section 5: Logout
        logout_card = ctk.CTkFrame(scroll, fg_color=RED_BG, corner_radius=16, border_width=1, border_color="#5c1a1a")
        logout_card.pack(fill="x", padx=24, pady=(12, 24))
        li = ctk.CTkFrame(logout_card, fg_color="transparent")
        li.pack(fill="x", padx=20, pady=16)

        sec_icon = get_icon("shield_lock", size=22, color=RED)
        self._section_icons.append(sec_icon)
        icon = ctk.CTkFrame(li, width=48, height=48, corner_radius=12, fg_color="#3a1515")
        icon.pack(side="left")
        icon.pack_propagate(False)
        ctk.CTkLabel(icon, image=sec_icon, text="").pack(expand=True)

        txt = ctk.CTkFrame(li, fg_color="transparent")
        txt.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(txt, text="Account Security", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(txt, text="End your current session securely", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

        ctk.CTkButton(
            li, text="Logout", width=100, height=40, corner_radius=10,
            fg_color=RED, hover_color="#dc2626",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._on_logout,
        ).pack(side="right")

    def _section(self, parent, icon_name, title, subtitle, builder):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=24, pady=(12, 0))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 12))

        sec_icon = get_icon(icon_name, size=22, color=ORANGE)
        self._section_icons.append(sec_icon)
        icon = ctk.CTkFrame(header, width=48, height=48, corner_radius=12, fg_color="#2a1a08")
        icon.pack(side="left")
        icon.pack_propagate(False)
        ctk.CTkLabel(icon, image=sec_icon, text="").pack(expand=True)

        txt = ctk.CTkFrame(header, fg_color="transparent")
        txt.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(txt, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(txt, text=subtitle, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=(0, 16))
        builder(content, header)

    def _build_thresholds(self, parent, header):
        thresholds = [
            ("CPU Usage Alert",        85, "%"),
            ("Memory Usage Alert",     90, "%"),
            ("Thread Count Alert",     50, "threads"),
            ("Response Time Alert",     3, "seconds"),
        ]
        for label, val, unit in thresholds:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=6)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(top, text=f"{val} {unit}", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=ORANGE).pack(side="right")

            slider = ctk.CTkSlider(
                row, from_=0, to=100, number_of_steps=100,
                progress_color=ORANGE, button_color=ORANGE,
                button_hover_color="#ea6c10", fg_color=BG_CARD_INNER,
                height=8,
            )
            slider.set(val)
            slider.pack(fill="x", pady=(4, 0))

    def _build_ml(self, parent, header):
        toggle_row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
        toggle_row.pack(fill="x", pady=(0, 8))
        ti = ctk.CTkFrame(toggle_row, fg_color="transparent")
        ti.pack(fill="x", padx=14, pady=12)

        txt = ctk.CTkFrame(ti, fg_color="transparent")
        txt.pack(side="left")
        ctk.CTkLabel(txt, text="Enable ML Prediction", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(txt, text="Use AI to predict potential crashes", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

        switch = ctk.CTkSwitch(ti, text="", onvalue=1, offvalue=0, progress_color=ORANGE, button_color=TEXT_PRIMARY, fg_color=TEXT_MUTED)
        switch.select()
        switch.pack(side="right")

        info_row = ctk.CTkFrame(parent, fg_color="transparent")
        info_row.pack(fill="x")
        info_row.columnconfigure(0, weight=1)
        info_row.columnconfigure(1, weight=1)

        for col, (label, val) in enumerate([("Model Version", "v1.0.0"), ("Last Training", "Pending...")]):
            box = ctk.CTkFrame(info_row, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
            box.grid(row=0, column=col, padx=(0 if col == 0 else 4, 4 if col == 0 else 0), sticky="nsew")
            bi = ctk.CTkFrame(box, fg_color="transparent")
            bi.pack(padx=14, pady=12)
            ctk.CTkLabel(bi, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")
            ctk.CTkLabel(bi, text=val, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")

    def _build_notifications(self, parent, header):
        notifs = [
            ("Email Notifications",  "Receive alerts via email",       True),
            ("Slack Integration",    "Push alerts to Slack channel",   False),
            ("SMS Alerts",           "Critical alerts via SMS",        False),
        ]
        for label, sub, default_on in notifs:
            row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=4)
            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=14, pady=12)

            txt = ctk.CTkFrame(ri, fg_color="transparent")
            txt.pack(side="left")
            ctk.CTkLabel(txt, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(txt, text=sub, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

            switch = ctk.CTkSwitch(ri, text="", progress_color=ORANGE, button_color=TEXT_PRIMARY, fg_color=TEXT_MUTED)
            if default_on:
                switch.select()
            switch.pack(side="right")

    def _build_users(self, parent, header):
        ctk.CTkButton(
            header, text="Add User", width=90, height=34, corner_radius=8,
            fg_color=ORANGE, hover_color="#ea6c10",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
        ).pack(side="right")

        for user in USERS:
            row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=4)
            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=14, pady=10)

            initials = "".join(n[0] for n in user["name"].split())
            av = ctk.CTkFrame(ri, width=38, height=38, corner_radius=19, fg_color=ORANGE)
            av.pack(side="left")
            av.pack_propagate(False)
            ctk.CTkLabel(av, text=initials, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color="#ffffff").pack(expand=True)

            txt = ctk.CTkFrame(ri, fg_color="transparent")
            txt.pack(side="left", padx=(10, 0))
            ctk.CTkLabel(txt, text=user["name"], font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(txt, text=user["email"], font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

            ctk.CTkLabel(ri, text=f" {user['role']} ", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=ORANGE, fg_color="#2a1a08", corner_radius=10).pack(side="right")
