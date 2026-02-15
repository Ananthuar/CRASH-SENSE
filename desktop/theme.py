"""
CrashSense — Design System / Theme Configuration
=================================================

Centralized design tokens for the CrashSense desktop application.
All colors, typography constants, and navigation definitions
are declared here to ensure visual consistency across every screen.

Design Reference:
    - Inspired by modern SOC (Security Operations Center) dashboards
    - Dark mode with orange/amber accent palette
    - Glassmorphism-inspired card styling

Usage:
    from desktop.theme import BG_ROOT, ORANGE, FONT_FAMILY
"""


# ─── Background Colors ─────────────────────────────────────────
# Layered dark backgrounds create depth:
#   BG_ROOT (deepest) → BG_SIDEBAR → BG_CARD → BG_CARD_INNER (lightest dark)
BG_ROOT = "#0a0a0a"           # Main window background (near-black)
BG_SIDEBAR = "#0f1218"        # Sidebar panel background
BG_TOPBAR = "#0d1017"         # Top navigation bar background
BG_CARD = "#111318"           # Card / panel surface color
BG_CARD_INNER = "#0c0e14"     # Nested inner panels (e.g. log viewer, form fields)
BG_INPUT = "#0a0c10"          # Text input field background
BG_HOVER = "#1a1c24"          # Hover state for interactive elements

# ─── Accent Colors ─────────────────────────────────────────────
# Primary accent is orange — used for CTAs, active nav, badges, and highlights.
ORANGE = "#f97316"             # Primary accent (CTA buttons, active indicators)
ORANGE_DIM = "#f97316"         # Dimmed variant (same for now, reserved for future)
ORANGE_BG = "#3d1d06"          # Low-opacity orange background (active nav item)
AMBER = "#fb923c"              # Secondary warm accent (charts, secondary highlights)
AMBER_BG = "#3b2308"           # Amber tinted background

# ─── Severity / Status Colors ──────────────────────────────────
# Used for alert badges, status indicators, and trend labels.
# Each color has a matching low-opacity background for badges.
RED = "#ef4444"                # Critical / Error / Trend Up (bad)
RED_BG = "#2a0f0f"             # Red badge background
YELLOW = "#eab308"             # Warning / Medium severity
YELLOW_BG = "#2a2508"          # Yellow badge background
GREEN = "#22c55e"              # Healthy / Low severity / Trend Down (good)
GREEN_BG = "#0a2a14"           # Green badge background
BLUE = "#3b82f6"               # Informational log level
BLUE_BG = "#0f1a2a"            # Blue badge background

# ─── Text Colors ───────────────────────────────────────────────
# Four-level text hierarchy for readability on dark backgrounds.
TEXT_PRIMARY = "#ffffff"        # Headings, metric values, primary content
TEXT_SECONDARY = "#9ca3af"      # Subtitles, descriptions, table content
TEXT_MUTED = "#6b7280"          # Timestamps, hints, footer text
TEXT_DARK = "#4b5563"           # Disabled / placeholder / lowest priority text

# ─── Border Colors ─────────────────────────────────────────────
# Subtle borders to separate elements without strong contrast.
BORDER = "#1e2028"              # Default card / section border
BORDER_LIGHT = "#2a2c36"       # Slightly visible border (hover states)
BORDER_ORANGE = "#5c2d0e"      # Orange-tinted border for highlighted cards

# ─── Typography ────────────────────────────────────────────────
# Inter is a modern sans-serif optimized for screen readability.
FONT_FAMILY = "Inter"

# ─── Sidebar Navigation Items ──────────────────────────────────
# Each entry maps to a screen in the application.
# The 'id' is used as the routing key in app.py, 'icon' is a Unicode symbol.
NAV_ITEMS = [
    {"id": "dashboard",     "label": "Dashboard",     "icon": "[#]"},
    {"id": "alerts",        "label": "Alerts",        "icon": "/!\\"},
    {"id": "crash-details", "label": "Crash Details", "icon": "[i]"},
    {"id": "logs",          "label": "Logs",          "icon": "[=]"},
    {"id": "prediction",    "label": "Prediction",    "icon": "[^]"},
    {"id": "settings",      "label": "Settings",      "icon": "{*}"},
]
