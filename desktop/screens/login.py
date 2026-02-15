"""
CrashSense — Login Screen
==========================

Full-screen authentication view displayed on application launch.
"""

import customtkinter as ctk
from desktop.theme import (
    BG_ROOT, ORANGE, AMBER, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BG_INPUT, BORDER, FONT_FAMILY,
)


class LoginScreen(ctk.CTkFrame):
    """Full-screen login page with centered authentication card."""

    def __init__(self, master, on_login, on_signup, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        self._on_login = on_login
        self._on_signup = on_signup

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self, width=420, fg_color="#111318",
            corner_radius=24, border_width=1, border_color="#1e2028",
        )
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=420, height=560)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=40, pady=36)

        # Branding
        logo = ctk.CTkFrame(inner, width=64, height=64, corner_radius=16, fg_color=ORANGE)
        logo.pack(pady=(0, 12))
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="CS", font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"), text_color="#ffffff").pack(expand=True)

        ctk.CTkLabel(
            inner, text="CRASH SENSE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack()
        ctk.CTkLabel(
            inner, text="AI BASED CRASH DETECTION SYSTEM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).pack(pady=(2, 20))

        # Email
        ctk.CTkLabel(
            inner, text="Email / Username",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x")
        self._email = ctk.CTkEntry(
            inner, height=44, corner_radius=12,
            fg_color=BG_INPUT, border_color=BORDER,
            placeholder_text="admin@company.com",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_PRIMARY,
        )
        self._email.pack(fill="x", pady=(4, 12))

        # Password
        ctk.CTkLabel(
            inner, text="Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x")
        self._password = ctk.CTkEntry(
            inner, height=44, corner_radius=12, show="*",
            fg_color=BG_INPUT, border_color=BORDER,
            placeholder_text="Enter your password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_PRIMARY,
        )
        self._password.pack(fill="x", pady=(4, 20))

        # Login button
        ctk.CTkButton(
            inner, text="Login to Dashboard  ->", height=44, corner_radius=12,
            fg_color=ORANGE, hover_color="#ea6c10",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            command=self._on_login,
        ).pack(fill="x", pady=(0, 8))

        # Demo mode
        ctk.CTkButton(
            inner, text="Enter Demo Mode", height=44, corner_radius=12,
            fg_color="#1a1c24", hover_color="#2a2c36",
            border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_PRIMARY,
            command=self._on_login,
        ).pack(fill="x", pady=(0, 16))

        # Sign up link
        signup_frame = ctk.CTkFrame(inner, fg_color="transparent")
        signup_frame.pack()
        ctk.CTkLabel(
            signup_frame, text="Don't have an account?",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        ).pack(side="left")
        ctk.CTkButton(
            signup_frame, text="Sign Up", width=60,
            fg_color="transparent", hover_color=BG_ROOT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=ORANGE,
            command=self._on_signup,
        ).pack(side="left")

        # Footer
        ctk.CTkFrame(inner, height=1, fg_color=BORDER).pack(fill="x", pady=(16, 12))
        ctk.CTkLabel(
            inner, text="Secure AI-Powered Crash Prevention Platform",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).pack()
