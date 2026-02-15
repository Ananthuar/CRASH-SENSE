"""
CrashSense — Sign Up Screen
============================

Full-screen registration view accessible from the login screen.
"""

import customtkinter as ctk
from desktop.theme import (
    BG_ROOT, ORANGE, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BG_INPUT, BORDER, FONT_FAMILY,
)


class SignUpScreen(ctk.CTkFrame):
    """Full-screen sign-up page with centered registration card."""

    def __init__(self, master, on_signup, on_back_to_login, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        self._on_signup = on_signup
        self._on_back_to_login = on_back_to_login

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self, width=420, fg_color="#111318",
            corner_radius=24, border_width=1, border_color="#1e2028",
        )
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=420, height=640)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=40, pady=32)

        # Branding
        logo = ctk.CTkFrame(inner, width=64, height=64, corner_radius=16, fg_color=ORANGE)
        logo.pack(pady=(0, 12))
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="CS", font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"), text_color="#ffffff").pack(expand=True)

        ctk.CTkLabel(
            inner, text="Create New Account",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack()
        ctk.CTkLabel(
            inner, text="Join the Security Operations Center",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).pack(pady=(2, 16))

        # Form fields
        fields = [
            ("Full Name",         "John Doe",                  False),
            ("Email Address",     "john.doe@company.com",      False),
            ("Password",          "Create a strong password",  True),
            ("Confirm Password",  "Re-enter your password",    True),
        ]
        self._entries = []
        for label, placeholder, is_password in fields:
            ctk.CTkLabel(
                inner, text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_SECONDARY, anchor="w",
            ).pack(fill="x")
            entry = ctk.CTkEntry(
                inner, height=42, corner_radius=12,
                fg_color=BG_INPUT, border_color=BORDER,
                placeholder_text=placeholder,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=TEXT_PRIMARY,
                show="*" if is_password else "",
            )
            entry.pack(fill="x", pady=(4, 10))
            self._entries.append(entry)

        # Create Account button
        ctk.CTkButton(
            inner, text="Create Account  ->", height=44, corner_radius=12,
            fg_color=ORANGE, hover_color="#ea6c10",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            command=self._on_signup,
        ).pack(fill="x", pady=(8, 12))

        # Back to login link
        back_frame = ctk.CTkFrame(inner, fg_color="transparent")
        back_frame.pack()
        ctk.CTkLabel(
            back_frame, text="<- Already have an account?",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        ).pack(side="left")
        ctk.CTkButton(
            back_frame, text="Login", width=50,
            fg_color="transparent", hover_color=BG_ROOT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=ORANGE,
            command=self._on_back_to_login,
        ).pack(side="left")

        # Footer
        ctk.CTkFrame(inner, height=1, fg_color=BORDER).pack(fill="x", pady=(12, 8))
        ctk.CTkLabel(
            inner, text="By signing up, you agree to our Terms of Service",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).pack()
