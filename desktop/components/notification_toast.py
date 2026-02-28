"""
CrashSense — Toast Notifications
=================================

A non-blocking sliding toast notification component built entirely within
the CustomTkinter mainloop. Uses `.after()` recursion to handle smooth
slide-in and slide-out animations without freezing the application.

Used to notify the user when the backend SystemResolver proactively 
intervenes (e.g., throttles a process, drops caches).
"""

import customtkinter as ctk

# Wait before sliding out
TOAST_DURATION_MS = 4000
# Slower, smoother animation values
ANIMATION_STEP_MS = 6
ANIMATION_DELTA = 0.02


class NotificationToast(ctk.CTkFrame):
    """
    A floating, auto-dismissible notification card.
    Requires its master to be the root ctk.CTk window, or a frame that 
    spans the whole view, as it uses relative placement to slide in from
    the bottom-right corner.
    """

    def __init__(self, master, action_type: str, process_name: str, detail: str, **kwargs):
        """
        :param action_type: 'Throttle', 'Terminate', or 'CacheDrop'
        """
        from desktop.theme import BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, FONT_FAMILY
        
        # Color mapping based on backend resolution action
        if action_type == "Throttle":
            self.accent_color = "#eab308" # Yellow
            icon_char = "\u26A0" # Warning
        elif action_type == "Terminate":
            self.accent_color = "#ef4444" # Red
            icon_char = "\u274C" # Cross
        elif action_type == "CacheDrop":
            self.accent_color = "#3b82f6" # Blue
            icon_char = "\u267B" # Recycle
        else:
            self.accent_color = "#22c55e" # Green
            icon_char = "\u2714" # Check
            
        # Give border-width to allow the accent color to frame the toast
        super().__init__(
            master, 
            fg_color=BG_CARD,
            border_width=2,
            border_color=self.accent_color,
            corner_radius=8,
            width=320,
            height=80,
            **kwargs
        )
        # Prevent auto-resizing to children so slide calculations are steady
        self.pack_propagate(False)

        # ── UI Layout ── 
        
        # Icon
        icon_lbl = ctk.CTkLabel(
            self, text=icon_char, 
            font=ctk.CTkFont(size=24), text_color=self.accent_color
        )
        icon_lbl.pack(side="left", padx=16)
        
        # Text Column
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=12)
        
        ctk.CTkLabel(
            text_frame, text=f"Threat Neutralized: {action_type}", 
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w"
        ).pack(fill="x")
        
        msg = f"{process_name}: {detail}" if detail else process_name
        ctk.CTkLabel(
            text_frame, text=msg, 
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY, anchor="w"
        ).pack(fill="x")
        
        # ── Animation State ──
        # Starts entirely off-screen to the right (relx = 1.0 + width offset proxy)
        # However relative placement with an anchor='se' means 1.0 is exactly the right edge
        # So we start relx = 1.5 and slide to 0.98
        self._current_relx = 1.2
        self._target_relx = 0.98  # Just inside the right padding
        self._rely = 0.95         # Just above the bottom edge

    def show(self):
        """Begin the slide-in animation."""
        self.place(relx=self._current_relx, rely=self._rely, anchor="se")
        self.lift() # Guarantee it sits on top of all other widgets
        self._slide_in()
        
    def _slide_in(self):
        """Recursive `.after()` animation moving leftward."""
        if self._current_relx > self._target_relx:
            self._current_relx -= ANIMATION_DELTA
            # Bound it down to exact target
            if self._current_relx < self._target_relx:
                self._current_relx = self._target_relx
                
            self.place(relx=self._current_relx, rely=self._rely, anchor="se")
            self.after(ANIMATION_STEP_MS, self._slide_in)
        else:
            # Reached target, pause for duration then slide out
            self.after(TOAST_DURATION_MS, self._slide_out)

    def _slide_out(self):
        """Recursive `.after()` animation moving rightward back off-screen."""
        # Target off-screen is 1.2
        if self._current_relx < 1.2:
            self._current_relx += ANIMATION_DELTA
            self.place(relx=self._current_relx, rely=self._rely, anchor="se")
            self.after(ANIMATION_STEP_MS, self._slide_out)
        else:
            # Animation complete, clean up memory
            self.destroy()
