"""
CrashSense — Login Screen
==========================

Email + Password login — everything happens inside the desktop app.
Google Sign-In available as a secondary browser-based option.
Checks email verification status on login.
"""

import customtkinter as ctk
import threading
from desktop import auth
from desktop import theme


class LoginScreen(ctk.CTkFrame):
    """Login screen with in-app email/password form."""

    def __init__(self, parent, on_login, on_signup):
        super().__init__(parent, fg_color=theme.BG_ROOT)
        self.on_login_success = on_login
        self.switch_to_signup = on_signup
        self._build_ui()

    def _build_ui(self):
        # Scrollable container
        container = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=theme.BG_CARD,
            scrollbar_button_hover_color=theme.ORANGE,
        )
        container.pack(fill="both", expand=True, padx=40, pady=30)

        # Header
        ctk.CTkLabel(
            container, text="Welcome Back",
            font=ctk.CTkFont(size=28, weight="bold"), text_color=theme.TEXT_PRIMARY,
        ).pack(pady=(30, 2))
        ctk.CTkLabel(
            container, text="Sign in to CrashSense",
            font=ctk.CTkFont(size=14), text_color=theme.TEXT_SECONDARY,
        ).pack(pady=(0, 30))

        # ── Email + Password Form Card ──────────────────────────
        form_card = ctk.CTkFrame(container, fg_color=theme.BG_CARD, corner_radius=12)
        form_card.pack(fill="x", pady=(0, 16))

        # Email field
        ctk.CTkLabel(
            form_card, text="Email Address",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme.TEXT_SECONDARY,
        ).pack(padx=24, pady=(24, 6), anchor="w")

        self.email_entry = ctk.CTkEntry(
            form_card, height=42, corner_radius=8,
            fg_color=theme.BG_INPUT, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, placeholder_text="you@example.com",
            placeholder_text_color=theme.TEXT_DARK, border_width=1,
            font=ctk.CTkFont(size=14),
        )
        self.email_entry.pack(fill="x", padx=24, pady=(0, 12))

        # Password field
        ctk.CTkLabel(
            form_card, text="Password",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme.TEXT_SECONDARY,
        ).pack(padx=24, pady=(4, 6), anchor="w")

        self.password_entry = ctk.CTkEntry(
            form_card, height=42, corner_radius=8, show="\u2022",
            fg_color=theme.BG_INPUT, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, placeholder_text="Enter your password",
            placeholder_text_color=theme.TEXT_DARK, border_width=1,
            font=ctk.CTkFont(size=14),
        )
        self.password_entry.pack(fill="x", padx=24, pady=(0, 20))

        # Login button
        ctk.CTkButton(
            form_card, text="Sign In", height=44, corner_radius=10,
            fg_color=theme.ORANGE, hover_color=theme.AMBER,
            text_color="white", font=ctk.CTkFont(size=15, weight="bold"),
            command=self._do_email_login,
        ).pack(fill="x", padx=24, pady=(0, 24))

        # ── Divider ────────────────────────────────────────────
        divider_frame = ctk.CTkFrame(container, fg_color="transparent", height=30)
        divider_frame.pack(fill="x", pady=(4, 4))
        ctk.CTkFrame(divider_frame, fg_color=theme.BORDER, height=1).place(
            relx=0, rely=0.5, relwidth=0.4)
        ctk.CTkLabel(
            divider_frame, text="OR", font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_MUTED, fg_color="transparent",
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkFrame(divider_frame, fg_color=theme.BORDER, height=1).place(
            relx=0.6, rely=0.5, relwidth=0.4)

        # ── Google button ──────────────────────────────────────
        ctk.CTkButton(
            container, text="\u25CF  Continue with Google", height=44,
            corner_radius=10,
            fg_color=theme.BG_CARD, hover_color=theme.BG_HOVER,
            border_color=theme.BORDER, border_width=1,
            text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=14),
            command=self._do_google_login,
        ).pack(fill="x", pady=(0, 16))

        # ── Error / Status ─────────────────────────────────────
        self.error_label = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=13),
            text_color=theme.RED, wraplength=380,
        )
        self.error_label.pack(pady=(0, 4))

        self.status_label = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=12),
            text_color=theme.TEXT_MUTED, wraplength=380,
        )
        self.status_label.pack(pady=(0, 10))

        # ── Signup link ────────────────────────────────────────
        signup_frame = ctk.CTkFrame(container, fg_color="transparent")
        signup_frame.pack(pady=(5, 20))
        ctk.CTkLabel(
            signup_frame, text="Don't have an account?",
            font=ctk.CTkFont(size=13), text_color=theme.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 5))
        ctk.CTkButton(
            signup_frame, text="Sign Up", width=60,
            fg_color="transparent", hover_color=theme.BG_HOVER,
            text_color=theme.ORANGE, font=ctk.CTkFont(size=13, weight="bold"),
            command=self.switch_to_signup,
        ).pack(side="left")

        # Bind Enter key
        self.password_entry.bind("<Return>", lambda e: self._do_email_login())

    def _show_error(self, msg):
        self.status_label.configure(text="")
        self.error_label.configure(text=msg)

    def _show_status(self, msg):
        self.error_label.configure(text="")
        self.status_label.configure(text=msg)

    # ── Email + Password Login ──────────────────────────────────
    def _do_email_login(self):
        email    = self.email_entry.get().strip()
        password = self.password_entry.get()

        if not email:
            self._show_error("Please enter your email address.")
            return
        if not password:
            self._show_error("Please enter your password.")
            return

        self._show_status("Signing in...")

        def _run():
            try:
                user = auth.sign_in_email_password(email, password)
                self.after(0, lambda: self.status_label.configure(text=""))
                self.after(0, lambda: self.email_entry.delete(0, 'end'))
                self.after(0, lambda: self.password_entry.delete(0, 'end'))
                self.after(0, lambda: self.on_login_success(user))
            except auth.AuthError as exc:
                err_msg = str(exc)
                self.after(0, lambda: self._show_error(err_msg))
            except Exception as exc:
                err_msg = f"Unexpected error: {exc}"
                self.after(0, lambda: self._show_error(err_msg))

        threading.Thread(target=_run, daemon=True).start()

    # ── Google Login ────────────────────────────────────────────
    def _do_google_login(self):
        self._show_status("Opening browser for Google sign-in...")

        def _run():
            try:
                user = auth.sign_in_with_google()
                self.after(0, lambda: self.status_label.configure(text=""))
                self.after(0, lambda: self.on_login_success(user))
            except auth.AuthError as exc:
                err_msg = str(exc)
                self.after(0, lambda: self._show_error(err_msg))
            except Exception as exc:
                err_msg = f"Unexpected error: {exc}"
                self.after(0, lambda: self._show_error(err_msg))

        threading.Thread(target=_run, daemon=True).start()
