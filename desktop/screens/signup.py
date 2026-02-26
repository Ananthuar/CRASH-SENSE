"""
CrashSense — Signup Screen
===========================

Email + Password signup — everything happens inside the desktop app.
Google Sign-In available as a secondary browser-based option.
Sends email verification after account creation.
"""

import customtkinter as ctk
import threading
from desktop import auth
from desktop import theme


class SignUpScreen(ctk.CTkFrame):
    """Signup screen with in-app email/password form."""

    def __init__(self, parent, on_signup, on_back_to_login):
        super().__init__(parent, fg_color=theme.BG_ROOT)
        self.on_signup_success = on_signup
        self.switch_to_login = on_back_to_login
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
            container, text="Create Account",
            font=ctk.CTkFont(size=28, weight="bold"), text_color=theme.TEXT_PRIMARY,
        ).pack(pady=(20, 2))
        ctk.CTkLabel(
            container, text="Join CrashSense today",
            font=ctk.CTkFont(size=14), text_color=theme.TEXT_SECONDARY,
        ).pack(pady=(0, 24))

        # ── Signup Form Card ────────────────────────────────────
        form_card = ctk.CTkFrame(container, fg_color=theme.BG_CARD, corner_radius=12)
        form_card.pack(fill="x", pady=(0, 16))

        # Display Name
        ctk.CTkLabel(
            form_card, text="Display Name",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme.TEXT_SECONDARY,
        ).pack(padx=24, pady=(24, 6), anchor="w")

        self.name_entry = ctk.CTkEntry(
            form_card, height=42, corner_radius=8,
            fg_color=theme.BG_INPUT, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, placeholder_text="Your name",
            placeholder_text_color=theme.TEXT_DARK, border_width=1,
            font=ctk.CTkFont(size=14),
        )
        self.name_entry.pack(fill="x", padx=24, pady=(0, 12))

        # Email
        ctk.CTkLabel(
            form_card, text="Email Address",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme.TEXT_SECONDARY,
        ).pack(padx=24, pady=(4, 6), anchor="w")

        self.email_entry = ctk.CTkEntry(
            form_card, height=42, corner_radius=8,
            fg_color=theme.BG_INPUT, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, placeholder_text="you@example.com",
            placeholder_text_color=theme.TEXT_DARK, border_width=1,
            font=ctk.CTkFont(size=14),
        )
        self.email_entry.pack(fill="x", padx=24, pady=(0, 12))

        # Password
        ctk.CTkLabel(
            form_card, text="Password",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme.TEXT_SECONDARY,
        ).pack(padx=24, pady=(4, 6), anchor="w")

        self.password_entry = ctk.CTkEntry(
            form_card, height=42, corner_radius=8, show="\u2022",
            fg_color=theme.BG_INPUT, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, placeholder_text="Min 6 characters",
            placeholder_text_color=theme.TEXT_DARK, border_width=1,
            font=ctk.CTkFont(size=14),
        )
        self.password_entry.pack(fill="x", padx=24, pady=(0, 12))

        # Confirm Password
        ctk.CTkLabel(
            form_card, text="Confirm Password",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme.TEXT_SECONDARY,
        ).pack(padx=24, pady=(4, 6), anchor="w")

        self.confirm_entry = ctk.CTkEntry(
            form_card, height=42, corner_radius=8, show="\u2022",
            fg_color=theme.BG_INPUT, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, placeholder_text="Repeat password",
            placeholder_text_color=theme.TEXT_DARK, border_width=1,
            font=ctk.CTkFont(size=14),
        )
        self.confirm_entry.pack(fill="x", padx=24, pady=(0, 20))

        # Sign Up button
        ctk.CTkButton(
            form_card, text="Create Account", height=44, corner_radius=10,
            fg_color=theme.ORANGE, hover_color=theme.AMBER,
            text_color="white", font=ctk.CTkFont(size=15, weight="bold"),
            command=self._do_email_signup,
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
            command=self._do_google_signup,
        ).pack(fill="x", pady=(0, 16))

        # ── Success / Error / Status ───────────────────────────
        self.success_label = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=13),
            text_color=theme.GREEN, wraplength=380,
        )
        self.success_label.pack(pady=(0, 4))

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

        # ── Login link ─────────────────────────────────────────
        login_frame = ctk.CTkFrame(container, fg_color="transparent")
        login_frame.pack(pady=(5, 20))
        ctk.CTkLabel(
            login_frame, text="Already have an account?",
            font=ctk.CTkFont(size=13), text_color=theme.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 5))
        ctk.CTkButton(
            login_frame, text="Log In", width=60,
            fg_color="transparent", hover_color=theme.BG_HOVER,
            text_color=theme.ORANGE, font=ctk.CTkFont(size=13, weight="bold"),
            command=self.switch_to_login,
        ).pack(side="left")

        # Bind Enter key
        self.confirm_entry.bind("<Return>", lambda e: self._do_email_signup())

    def _show_error(self, msg):
        self.success_label.configure(text="")
        self.status_label.configure(text="")
        self.error_label.configure(text=msg)

    def _show_status(self, msg):
        self.success_label.configure(text="")
        self.error_label.configure(text="")
        self.status_label.configure(text=msg)

    def _show_success(self, msg):
        self.error_label.configure(text="")
        self.status_label.configure(text="")
        self.success_label.configure(text=msg)

    # ── Email + Password Signup ─────────────────────────────────
    def _do_email_signup(self):
        name     = self.name_entry.get().strip()
        email    = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm  = self.confirm_entry.get()

        if not name:
            self._show_error("Please enter your name.")
            return
        if not email:
            self._show_error("Please enter your email address.")
            return
        if not password:
            self._show_error("Please enter a password.")
            return
        if len(password) < 6:
            self._show_error("Password must be at least 6 characters.")
            return
        if password != confirm:
            self._show_error("Passwords do not match.")
            return

        self._show_status("Creating account...")

        def _run():
            try:
                user = auth.sign_up_email_password(email, password, name)
                
                # Clear fields
                self.after(0, lambda: self.name_entry.delete(0, 'end'))
                self.after(0, lambda: self.email_entry.delete(0, 'end'))
                self.after(0, lambda: self.password_entry.delete(0, 'end'))
                self.after(0, lambda: self.confirm_entry.delete(0, 'end'))
                
                # Show success message — user needs to verify email first
                self.after(0, lambda: self._show_success(
                    "Account created! A verification email has been sent to "
                    f"{email}. Please check your inbox and click the link, "
                    "then come back and log in."
                ))
            except auth.AuthError as exc:
                err_msg = str(exc)
                self.after(0, lambda: self._show_error(err_msg))
            except Exception as exc:
                err_msg = f"Unexpected error: {exc}"
                self.after(0, lambda: self._show_error(err_msg))

        threading.Thread(target=_run, daemon=True).start()

    # ── Google Signup ───────────────────────────────────────────
    def _do_google_signup(self):
        self._show_status("Opening browser for Google sign-in...")

        def _run():
            try:
                user = auth.sign_in_with_google()
                self.after(0, lambda: self.status_label.configure(text=""))
                self.after(0, lambda: self.on_signup_success(user))
            except auth.AuthError as exc:
                err_msg = str(exc)
                self.after(0, lambda: self._show_error(err_msg))
            except Exception as exc:
                err_msg = f"Unexpected error: {exc}"
                self.after(0, lambda: self._show_error(err_msg))

        threading.Thread(target=_run, daemon=True).start()
