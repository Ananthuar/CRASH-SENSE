"""
CrashSense — Login Screen
==========================

Full-screen authentication view displayed on application launch.
"""

import customtkinter as ctk
from desktop.theme import (
    BG_ROOT, ORANGE, AMBER, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BG_INPUT, BORDER, FONT_FAMILY, RED,
)
import os
from PIL import Image


class LoginScreen(ctk.CTkFrame):
    """Full-screen login page with centered authentication card."""

    def __init__(self, master, on_login, on_signup, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)

        self._on_login = on_login
        self._on_signup = on_signup

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self, width=580, fg_color="#111318",
            corner_radius=24, border_width=1, border_color="#1e2028",
        )
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=580, height=720)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=48, pady=40)

        # Branding — App icon from assets
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "assets", "icon.png")
        pil_icon = Image.open(icon_path).resize((80, 80), Image.LANCZOS)
        self._brand_icon = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(80, 80))
        ctk.CTkLabel(inner, image=self._brand_icon, text="").pack(pady=(0, 16))

        ctk.CTkLabel(
            inner, text="CRASH SENSE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack()
        ctk.CTkLabel(
            inner, text="AI-Based Crash Detection System",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_MUTED,
        ).pack(pady=(4, 28))

        # Username
        ctk.CTkLabel(
            inner, text="Username",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x")
        self._email = ctk.CTkEntry(
            inner, height=48, corner_radius=12,
            fg_color=BG_INPUT, border_color=BORDER,
            placeholder_text="Enter your username",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            text_color=TEXT_PRIMARY,
        )
        self._email.pack(fill="x", pady=(6, 16))

        # Password
        ctk.CTkLabel(
            inner, text="Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            text_color=TEXT_SECONDARY, anchor="w",
        ).pack(fill="x")
        self._password = ctk.CTkEntry(
            inner, height=48, corner_radius=12, show="*",
            fg_color=BG_INPUT, border_color=BORDER,
            placeholder_text="Enter your password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            text_color=TEXT_PRIMARY,
        )
        self._password.pack(fill="x", pady=(6, 10))

        # Error message label (hidden by default)
        self._error_label = ctk.CTkLabel(
            inner, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#ffffff", anchor="w",
        )
        self._error_label.pack(fill="x", pady=(0, 10))

        # Login button
        ctk.CTkButton(
            inner, text="Login to Dashboard", height=50, corner_radius=12,
            fg_color=ORANGE, hover_color="#ea6c10",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            command=self._attempt_login,
        ).pack(fill="x", pady=(0, 10))

        # Demo mode
        ctk.CTkButton(
            inner, text="Enter Demo Mode", height=50, corner_radius=12,
            fg_color="#1a1c24", hover_color="#2a2c36",
            border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            text_color=TEXT_PRIMARY,
            command=self._on_login,
        ).pack(fill="x", pady=(0, 20))

        # Sign up link
        signup_frame = ctk.CTkFrame(inner, fg_color="transparent")
        signup_frame.pack()
        ctk.CTkLabel(
            signup_frame, text="Don't have an account?",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        ).pack(side="left")
        ctk.CTkButton(
            signup_frame, text="Sign Up", width=60,
            fg_color="transparent", hover_color=BG_ROOT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=ORANGE,
            command=self._on_signup,
        ).pack(side="left")

        # Footer
        ctk.CTkFrame(inner, height=1, fg_color=BORDER).pack(fill="x", pady=(20, 12))
        ctk.CTkLabel(
            inner, text="Use credentials:  test / test",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        ).pack()

    def _attempt_login(self):
        """Validate credentials and show error or proceed."""
        username = self._email.get().strip()
        password = self._password.get().strip()

        if username == "test" and password == "test":
            self._error_label.configure(text="")
            self._on_login()
        else:
            self._error_label.configure(text="Invalid credentials. Use test / test")
