"""
CrashSense — Settings Screen
==============================

Application settings panel with thresholds, ML toggle, notifications,
user management, and logout.
"""

import customtkinter as ctk
import threading
import customtkinter as ctk
import requests
from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, RED, RED_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY, GREEN
)
from desktop.icons import get_icon
from desktop import session

BACKEND_BASE = "http://127.0.0.1:5000"


class SettingsScreen(ctk.CTkFrame):
    """Settings panel — single scroll container."""

    def __init__(self, master, on_logout, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)
        self._on_logout = on_logout
        self._user = session.get_user()
        self._settings = {}
        
        # Debounce timer for saving
        self._save_timer = None

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_ROOT, scrollbar_button_color="#1e2028", scrollbar_button_hover_color="#2a2c36")
        scroll.pack(fill="both", expand=True)
        scroll.bind_all("<Button-4>", lambda e: scroll._parent_canvas.yview_scroll(-3, "units"))
        scroll.bind_all("<Button-5>", lambda e: scroll._parent_canvas.yview_scroll(3, "units"))

        self._section_icons = []  # prevent GC
        self._scroll = scroll
        
        # Load settings from backend before building UI
        self._load_settings()

    def _load_settings(self):
        uid = self._user.get("uid")
        if uid:
            try:
                resp = requests.get(f"{BACKEND_BASE}/api/users/{uid}/settings", timeout=3)
                if resp.ok:
                    self._settings = resp.json() or {}
            except Exception:
                pass  # Use defaults if backend offline
        self._build_sections()

    def _schedule_save(self):
        """Debounce saving to the backend."""
        if self._save_timer is not None:
            self.after_cancel(self._save_timer)
        self._save_timer = self.after(1000, self._save_to_backend)

    def _save_to_backend(self):
        uid = self._user.get("uid")
        if not uid:
            return  # Demo mode
            
        def _put():
            try:
                requests.put(f"{BACKEND_BASE}/api/users/{uid}/settings", json=self._settings, timeout=5)
            except Exception:
                pass
                
        threading.Thread(target=_put, daemon=True).start()

    def _build_sections(self):
        scroll = self._scroll
        
        # Section 0: My Profile
        self._section(scroll, "profile", "My Profile", "Your currently logged in account details", self._build_profile)

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

    def _build_profile(self, parent, header):
        row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
        row.pack(fill="x", pady=4)
        ri = ctk.CTkFrame(row, fg_color="transparent")
        ri.pack(fill="x", padx=14, pady=10)

        # Basic placeholder based on local session email until fetch
        raw_email = self._user.get("email", "User")
        initials = raw_email[0].upper() if raw_email else "U"
        
        av = ctk.CTkFrame(ri, width=38, height=38, corner_radius=19, fg_color=ORANGE)
        av.pack(side="left")
        av.pack_propagate(False)
        ctk.CTkLabel(av, text=initials, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color="#ffffff").pack(expand=True)

        txt = ctk.CTkFrame(ri, fg_color="transparent")
        txt.pack(side="left", padx=(10, 0))
        
        name_lbl = ctk.CTkLabel(txt, text="Loading Firebase Profile...", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY)
        name_lbl.pack(anchor="w")
        email_lbl = ctk.CTkLabel(txt, text=raw_email, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY)
        email_lbl.pack(anchor="w")

        role_lbl = ctk.CTkLabel(ri, text=" Fetching... ", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=ORANGE, fg_color="#2a1a08", corner_radius=10)
        role_lbl.pack(side="right")

        def _fetch_profile():
            uid = self._user.get("uid")
            if not uid: return
            try:
                resp = requests.get(f"{BACKEND_BASE}/api/users/{uid}/profile", timeout=3)
                if resp.ok:
                    data = resp.json()
                    def _update():
                        name_lbl.configure(text=data.get("display_name", data.get("email", "Unknown User")))
                        role_lbl.configure(text=f" {data.get('role', 'User')} ")
                    self.after(0, _update)
            except Exception:
                self.after(0, lambda: name_lbl.configure(text="Offline (No Data)"))

        threading.Thread(target=_fetch_profile, daemon=True).start()

    def _build_thresholds(self, parent, header):
        thresholds = [
            ("CPU Usage Alert",        self._settings.get("cpu_alert", 85), "%", "cpu_alert", 100),
            ("Memory Usage Alert",     self._settings.get("memory_alert", 90), "%", "memory_alert", 100),
            ("Max Threads Per Process", self._settings.get("thread_alert", 50), "threads", "thread_alert", 500),
            ("Response Time Alert",    self._settings.get("response_alert", 3), "seconds", "response_alert", 30),
        ]

        for label, val, unit, key, max_val in thresholds:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=6)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
            
            val_label = ctk.CTkLabel(top, text=f"{val} {unit}", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=ORANGE)
            val_label.pack(side="right")
            
            def on_change(new_val, lbl=val_label, k=key, u=unit):
                v = int(new_val)
                lbl.configure(text=f"{v} {u}")
                self._settings[k] = v
                self._schedule_save()

            slider = ctk.CTkSlider(
                row, from_=0, to=max_val, number_of_steps=max_val,
                progress_color=ORANGE, button_color=ORANGE,
                button_hover_color="#ea6c10", fg_color=BG_CARD_INNER,
                height=8,
                command=on_change
            )
            slider.set(val)
            slider.pack(fill="x", pady=(4, 0))

    def _build_ml(self, parent, header):
        # ── Enable/Disable toggle ──────────────────────────────────
        toggle_row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
        toggle_row.pack(fill="x", pady=(0, 8))
        ti = ctk.CTkFrame(toggle_row, fg_color="transparent")
        ti.pack(fill="x", padx=14, pady=12)

        txt = ctk.CTkFrame(ti, fg_color="transparent")
        txt.pack(side="left")
        ctk.CTkLabel(txt, text="Enable ML Prediction", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(txt, text="Use AI to predict potential crashes", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

        def on_ml_toggle():
            enabled = bool(switch.get())
            self._settings["ml_enabled"] = enabled
            self._schedule_save()
            # Push to backend immediately so prediction loop respects it
            def _push():
                try:
                    requests.put(f"{BACKEND_BASE}/api/ml-status", json={"enabled": enabled}, timeout=3)
                except Exception:
                    pass
            threading.Thread(target=_push, daemon=True).start()

        switch = ctk.CTkSwitch(
            ti, text="", onvalue=1, offvalue=0,
            progress_color=ORANGE, button_color=TEXT_PRIMARY, fg_color=TEXT_MUTED,
            command=on_ml_toggle
        )
        if self._settings.get("ml_enabled", True):
            switch.select()
        else:
            switch.deselect()
        switch.pack(side="right")

        # ── Model metadata cards (loaded from backend) ─────────────
        info_row = ctk.CTkFrame(parent, fg_color="transparent")
        info_row.pack(fill="x")
        info_row.columnconfigure(0, weight=1)
        info_row.columnconfigure(1, weight=1)
        info_row.columnconfigure(2, weight=1)

        # Placeholder labels updated once API returns
        meta_labels: dict[str, ctk.CTkLabel] = {}
        for col, (key, label, default) in enumerate([
            ("model_version", "Model Version",  "loading…"),
            ("accuracy",      "Accuracy",        "loading…"),
            ("trained_at",    "Last Training",   "loading…"),
        ]):
            box = ctk.CTkFrame(info_row, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
            col_pad = (0 if col == 0 else 4, 4 if col < 2 else 0)
            box.grid(row=0, column=col, padx=col_pad, sticky="nsew")
            bi = ctk.CTkFrame(box, fg_color="transparent")
            bi.pack(padx=14, pady=12)
            ctk.CTkLabel(bi, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")
            val_lbl = ctk.CTkLabel(bi, text=default, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY)
            val_lbl.pack(anchor="w")
            meta_labels[key] = val_lbl

        def _fetch_ml_status():
            try:
                resp = requests.get(f"{BACKEND_BASE}/api/ml-status", timeout=3)
                if resp.ok:
                    data = resp.json()
                    def _update():
                        meta_labels["model_version"].configure(text=data.get("model_version", "N/A"))
                        acc = data.get("accuracy", "N/A")
                        meta_labels["accuracy"].configure(text=acc, text_color=GREEN if acc != "N/A" else TEXT_MUTED)
                        meta_labels["trained_at"].configure(text=data.get("trained_at", "Unknown"))
                        # Sync switch state with backend
                        if data.get("enabled", True):
                            switch.select()
                        else:
                            switch.deselect()
                    self.after(0, _update)
            except Exception:
                def _err():
                    for lbl in meta_labels.values():
                        lbl.configure(text="Backend offline", text_color=TEXT_MUTED)
                self.after(0, _err)

        threading.Thread(target=_fetch_ml_status, daemon=True).start()

    def _build_notifications(self, parent, header):
        from desktop.notifier import crash_warning_notifier

        # ── Desktop OS Notifications (notify-send) ────────────────
        # ── In-App Banners ────────────────────────────────────────
        live_notifs = [
            ("Desktop Notifications",  "Native OS pop-up when a crash precursor is detected",
             crash_warning_notifier.desktop_enabled,  "notif_desktop"),
            ("In-App Banners",         "Warning banner inside CrashSense on new alerts",
             crash_warning_notifier.inapp_enabled,    "notif_inapp"),
        ]

        def make_live_toggle(key):
            def _toggle(w):
                enabled = bool(w.get())
                self._settings[key] = enabled
                self._schedule_save()
                if key == "notif_desktop":
                    crash_warning_notifier.desktop_enabled = enabled
                elif key == "notif_inapp":
                    crash_warning_notifier.inapp_enabled = enabled
            return _toggle

        for label, sub, default_on, key in live_notifs:
            row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=4)
            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=14, pady=12)

            txt_f = ctk.CTkFrame(ri, fg_color="transparent")
            txt_f.pack(side="left")
            ctk.CTkLabel(txt_f, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(txt_f, text=sub,   font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

            sw = ctk.CTkSwitch(ri, text="", progress_color=ORANGE, button_color=TEXT_PRIMARY, fg_color=TEXT_MUTED)
            handler = make_live_toggle(key)
            sw.configure(command=lambda w=sw: handler(w))
            # Initialise from persisted settings (fall back to live value)
            saved = self._settings.get(key, default_on)
            if saved:
                sw.select()
            else:
                sw.deselect()
                if key == "notif_desktop":
                    crash_warning_notifier.desktop_enabled = False
                elif key == "notif_inapp":
                    crash_warning_notifier.inapp_enabled = False
            sw.pack(side="right")

        # ── Separator ─────────────────────────────────────────────
        ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(parent, text="Cloud / External Channels",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                     text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 6))

        # ── External channel toggles (saved to backend) ─────────
        ext_notifs = [
            ("Email Notifications",  "Receive alerts via email",     self._settings.get("notif_email", True),  "notif_email"),
            ("Slack Integration",    "Push alerts to Slack channel", self._settings.get("notif_slack", False), "notif_slack"),
            ("SMS Alerts",           "Critical alerts via SMS",      self._settings.get("notif_sms",   False), "notif_sms"),
        ]

        for label, sub, default_on, key in ext_notifs:
            row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=4)
            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=14, pady=12)

            txt_f = ctk.CTkFrame(ri, fg_color="transparent")
            txt_f.pack(side="left")
            ctk.CTkLabel(txt_f, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(txt_f, text=sub,   font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY).pack(anchor="w")

            sw = ctk.CTkSwitch(ri, text="", progress_color=ORANGE, button_color=TEXT_PRIMARY, fg_color=TEXT_MUTED)
            sw.configure(command=lambda w=sw, k=key: self._on_notif_toggle(k, w.get()))
            if default_on:
                sw.select()
            else:
                sw.deselect()
            sw.pack(side="right")

    def _on_notif_toggle(self, key, val):
        self._settings[key] = bool(val)
        self._schedule_save()

    def _build_users(self, parent, header):
        def on_add_user():
            # Simply create a temporary popup to suggest logging out and using signup
            popup = ctk.CTkToplevel(self)
            popup.title("Add User")
            popup.geometry("300x150")
            popup.attributes("-topmost", True)
            popup.configure(fg_color=BG_ROOT)
            
            ctk.CTkLabel(
                popup, 
                text="To add a new user to the organization,\nplease log out and use the Sign Up page.", 
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_PRIMARY
            ).pack(expand=True, padx=20, pady=20)
            
            ctk.CTkButton(
                popup, text="OK", width=80, corner_radius=8,
                fg_color=ORANGE, hover_color="#ea6c10",
                command=popup.destroy
            ).pack(pady=(0, 20))

        ctk.CTkButton(
            header, text="Add User", width=90, height=34, corner_radius=8,
            fg_color=ORANGE, hover_color="#ea6c10",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=on_add_user
        ).pack(side="right")

        # Try to fetch live users from Firestore via backend
        users = []
        try:
            resp = requests.get(f"{BACKEND_BASE}/api/users", timeout=3)
            if resp.ok:
                remote = resp.json()
                if remote:
                    # Normalise: backend returns {display_name, email, role, uid}
                    users = [
                        {
                            "name":  u.get("display_name", u.get("email", "Unknown")),
                            "email": u.get("email", ""),
                            "role":  u.get("role", "User"),
                        }
                        for u in remote
                    ]
        except Exception:
            pass  # backend offline

        if not users:
            ctk.CTkLabel(parent, text="No users found or backend offline.", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_MUTED).pack(pady=20)
            return

        for user in users:
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

