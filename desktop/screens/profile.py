"""
CrashSense — Profile Screen (Desktop)
=======================================

Displays the logged-in user's Firestore profile with an inline edit mode.

Layout:
    ┌───────────────────────────────┐
    │   [Avatar circle / initials]  │
    │   Full Name       [Edit ✎]   │
    │   Email (read-only)           │
    │   Role                        │
    │   Member Since                │
    └───────────────────────────────┘

"Edit Profile" reveals an editable Full Name field and a Save button
that calls PUT /api/users/<uid>/profile on the backend.
"""

import threading
import requests
import customtkinter as ctk
from desktop.theme import (
    BG_ROOT, BG_CARD, BG_CARD_INNER, ORANGE, ORANGE_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_FAMILY,
    RED, GREEN,
)
from desktop import session

BACKEND_BASE = "http://127.0.0.1:5000"


class ProfileScreen(ctk.CTkFrame):
    """User profile screen with display and inline edit mode."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_ROOT, **kwargs)
        self._user = session.get_user()
        self._edit_mode = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build()

    def _build(self):
        user = self._user

        # Outer centering wrapper
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=0, column=0)

        # ── Profile Card ────────────────────────────────────────
        card = ctk.CTkFrame(
            outer, width=520, fg_color=BG_CARD,
            corner_radius=24, border_width=1, border_color=BORDER,
        )
        card.pack(pady=48)
        card.pack_propagate(False)
        card.configure(width=520, height=540)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=48, pady=36)

        # Avatar
        initials = session.get_initials()
        avatar_frame = ctk.CTkFrame(inner, width=90, height=90, corner_radius=45, fg_color=ORANGE)
        avatar_frame.pack(pady=(0, 20))
        avatar_frame.pack_propagate(False)
        ctk.CTkLabel(
            avatar_frame, text=initials,
            font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
            text_color="#ffffff",
        ).pack(expand=True)

        # Header row: name + edit button
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))

        display_name = user.get("display_name") or user.get("email") or "Guest User"
        self._name_label = ctk.CTkLabel(
            header, text=display_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        self._name_label.pack(side="left")

        self._edit_btn = ctk.CTkButton(
            header, text="Edit Profile", width=110, height=34, corner_radius=8,
            fg_color=ORANGE_BG, hover_color="#5a2d0a",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=ORANGE,
            command=self._toggle_edit,
        )
        self._edit_btn.pack(side="right")

        # ── Inline edit field (hidden by default) ───────────────
        self._edit_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._name_entry = ctk.CTkEntry(
            self._edit_frame, height=40, corner_radius=10,
            fg_color=BG_CARD_INNER, border_color=BORDER,
            placeholder_text="Full Name",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_PRIMARY,
        )
        self._name_entry.insert(0, display_name)
        self._name_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._save_btn = ctk.CTkButton(
            self._edit_frame, text="Save", width=80, height=40, corner_radius=10,
            fg_color=ORANGE, hover_color="#ea6c10",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._save_profile,
        )
        self._save_btn.pack(side="left")
        # Not packed yet — shown when _toggle_edit() is called

        # ── Status message ───────────────────────────────────────
        self._status_label = ctk.CTkLabel(
            inner, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=GREEN,
        )
        self._status_label.pack(fill="x")

        # ── Divider ─────────────────────────────────────────────
        ctk.CTkFrame(inner, height=1, fg_color=BORDER).pack(fill="x", pady=16)

        # ── Profile Fields ───────────────────────────────────────
        fields = [
            ("Email",        user.get("email", "—")),
            ("Role",         user.get("role", "User")),
            ("Member Since", user.get("joined", "—") or "—"),
        ]
        for label, value in fields:
            self._field_row(inner, label, value)

    def _field_row(self, parent, label: str, value: str):
        row = ctk.CTkFrame(parent, fg_color=BG_CARD_INNER, corner_radius=10, border_width=1, border_color=BORDER)
        row.pack(fill="x", pady=4)
        ri = ctk.CTkFrame(row, fg_color="transparent")
        ri.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(ri, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                     text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkLabel(ri, text=value, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w")

    # ── Edit Mode ────────────────────────────────────────────────

    def _toggle_edit(self):
        self._edit_mode = not self._edit_mode
        if self._edit_mode:
            self._edit_btn.configure(text="Cancel")
            self._edit_frame.pack(fill="x", pady=(0, 8))
        else:
            self._edit_btn.configure(text="Edit Profile")
            self._edit_frame.pack_forget()
            self._status_label.configure(text="")

    def _save_profile(self):
        new_name = self._name_entry.get().strip()
        if not new_name:
            self._status_label.configure(text="Name cannot be empty.", text_color=RED)
            return

        uid = self._user.get("uid")
        if not uid:
            # Demo mode — just update in-memory
            session.set_user({**self._user, "display_name": new_name})
            self._name_label.configure(text=new_name)
            self._toggle_edit()
            self._status_label.configure(text="Profile updated locally (Demo Mode).", text_color=TEXT_MUTED)
            return

        self._save_btn.configure(state="disabled", text="Saving…")

        def _do_save():
            try:
                resp = requests.put(
                    f"{BACKEND_BASE}/api/users/{uid}/profile",
                    json={"display_name": new_name},
                    timeout=5,
                )
                success = resp.ok
                error_msg = "" if success else f"Save failed: {resp.status_code}"
            except Exception as exc:
                success = False
                error_msg = f"Save failed: {exc}"

            self.after(0, lambda: self._after_save(success, new_name, error_msg))

        threading.Thread(target=_do_save, daemon=True).start()

    def _after_save(self, success: bool, new_name: str, error_msg: str):
        self._save_btn.configure(state="normal", text="Save")
        if success:
            # Update session and label
            updated = {**self._user, "display_name": new_name}
            session.set_user(updated)
            self._user = session.get_user()
            self._name_label.configure(text=new_name)
            self._toggle_edit()
            self._status_label.configure(text="✓ Profile saved successfully.", text_color=GREEN)
        else:
            self._status_label.configure(text=error_msg, text_color=RED)
