"""
CrashSense — Icon Factory
===========================

Generates crisp, anti-aliased icons for the sidebar, topbar, and other UI
elements using **Pillow** (PIL) drawing primitives.  Each icon is rendered at
2× resolution and down-scaled to produce smooth edges, then wrapped in a
``customtkinter.CTkImage`` ready for direct use in buttons and labels.

Supported icons:
    dashboard, alerts, crash_details, logs, prediction, settings,
    logout, bell, power, back_arrow

Usage::

    from desktop.icons import get_icon
    img = get_icon("dashboard", size=20, color="#f97316")
    ctk.CTkButton(master, image=img, text="Dashboard", ...)
"""

from PIL import Image, ImageDraw
import customtkinter as ctk
import math


def _new_canvas(size: int, scale: int = 3):
    """Create a transparent RGBA canvas at *scale*× resolution."""
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    return img, draw, s, scale


def _finish(img: Image.Image, size: int) -> Image.Image:
    """Down-sample to target size with high-quality anti-aliasing."""
    return img.resize((size, size), Image.LANCZOS)


def _hex_to_rgba(hex_color: str, alpha: int = 255):
    """Convert a hex colour string to an RGBA tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


# ═══════════════════════════════════════════════════════════════
#  ICON DRAWING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _draw_dashboard(size: int, color: str) -> Image.Image:
    """Grid of four rounded squares — classic dashboard icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    pad = int(s * 0.15)
    gap = int(s * 0.10)
    cell_w = (s - 2 * pad - gap) // 2
    lw = max(2, int(s * 0.06))

    for row in range(2):
        for col in range(2):
            x0 = pad + col * (cell_w + gap)
            y0 = pad + row * (cell_w + gap)
            x1 = x0 + cell_w
            y1 = y0 + cell_w
            r = int(cell_w * 0.22)
            draw.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=c, width=lw)
    return _finish(img, size)


def _draw_alerts(size: int, color: str) -> Image.Image:
    """Bell icon — notification / alerts."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    cx = s // 2

    # Bell body (arc + rectangle)
    bell_top = int(s * 0.15)
    bell_bot = int(s * 0.68)
    bell_left = int(s * 0.18)
    bell_right = s - bell_left

    # Top dome
    draw.arc([bell_left, bell_top, bell_right, bell_bot + int(s * 0.1)],
             start=180, end=0, fill=c, width=lw)

    # Sides
    draw.line([(bell_left, (bell_top + bell_bot) // 2), (bell_left, bell_bot)], fill=c, width=lw)
    draw.line([(bell_right, (bell_top + bell_bot) // 2), (bell_right, bell_bot)], fill=c, width=lw)

    # Bottom rim (wider)
    rim_left = int(s * 0.12)
    rim_right = s - rim_left
    rim_y = bell_bot
    draw.line([(rim_left, rim_y), (rim_right, rim_y)], fill=c, width=lw)

    # Clapper (small circle at bottom)
    clap_r = int(s * 0.06)
    clap_y = int(s * 0.80)
    draw.ellipse([cx - clap_r, clap_y - clap_r, cx + clap_r, clap_y + clap_r], fill=c)

    # Top knob
    knob_r = int(s * 0.04)
    knob_y = bell_top
    draw.ellipse([cx - knob_r, knob_y - knob_r, cx + knob_r, knob_y + knob_r], fill=c)

    return _finish(img, size)


def _draw_crash_details(size: int, color: str) -> Image.Image:
    """Document with magnifying glass — crash details / info."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))

    # Document body
    doc_l = int(s * 0.18)
    doc_r = int(s * 0.68)
    doc_t = int(s * 0.12)
    doc_b = int(s * 0.85)
    r = int(s * 0.06)
    draw.rounded_rectangle([doc_l, doc_t, doc_r, doc_b], radius=r, outline=c, width=lw)

    # Text lines on document
    line_l = int(s * 0.26)
    line_r = int(s * 0.58)
    for i, frac in enumerate([0.30, 0.42, 0.54]):
        y = int(s * frac)
        right = line_r if i < 2 else int(s * 0.46)
        draw.line([(line_l, y), (right, y)], fill=c, width=max(1, lw // 2))

    # Magnifying glass
    mg_cx = int(s * 0.68)
    mg_cy = int(s * 0.65)
    mg_r = int(s * 0.14)
    draw.ellipse([mg_cx - mg_r, mg_cy - mg_r, mg_cx + mg_r, mg_cy + mg_r], outline=c, width=lw)
    # Handle
    hx = mg_cx + int(mg_r * 0.7)
    hy = mg_cy + int(mg_r * 0.7)
    draw.line([(hx, hy), (hx + int(s * 0.10), hy + int(s * 0.10))], fill=c, width=lw)

    return _finish(img, size)


def _draw_logs(size: int, color: str) -> Image.Image:
    """Stacked horizontal lines with bullets — log list icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))

    pad_l = int(s * 0.18)
    pad_r = int(s * 0.18)
    bullet_r = int(s * 0.04)

    for i, frac in enumerate([0.25, 0.42, 0.58, 0.75]):
        y = int(s * frac)
        # Bullet
        bx = pad_l
        draw.ellipse([bx - bullet_r, y - bullet_r, bx + bullet_r, y + bullet_r], fill=c)
        # Line
        draw.line([(pad_l + int(s * 0.10), y), (s - pad_r, y)], fill=c, width=lw)

    return _finish(img, size)


def _draw_prediction(size: int, color: str) -> Image.Image:
    """Ascending trend line with arrow — prediction / analytics."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))

    # Chart axes
    ax_l = int(s * 0.18)
    ax_b = int(s * 0.82)
    ax_r = int(s * 0.85)
    ax_t = int(s * 0.15)
    draw.line([(ax_l, ax_t), (ax_l, ax_b)], fill=c, width=lw)
    draw.line([(ax_l, ax_b), (ax_r, ax_b)], fill=c, width=lw)

    # Trend line (going up with slight curve)
    points = [
        (int(s * 0.25), int(s * 0.70)),
        (int(s * 0.40), int(s * 0.58)),
        (int(s * 0.55), int(s * 0.48)),
        (int(s * 0.70), int(s * 0.30)),
    ]
    draw.line(points, fill=c, width=lw, joint="curve")

    # Arrow head at end of trend
    tip = points[-1]
    arr_len = int(s * 0.08)
    draw.line([(tip[0] - arr_len, tip[1]), tip], fill=c, width=lw)
    draw.line([(tip[0], tip[1] + arr_len), tip], fill=c, width=lw)

    return _finish(img, size)


def _draw_settings(size: int, color: str) -> Image.Image:
    """Gear / cog icon — settings."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    cx, cy = s // 2, s // 2

    # Outer gear teeth
    outer_r = int(s * 0.40)
    inner_r = int(s * 0.30)
    teeth = 8
    tooth_half = math.pi / teeth / 2

    points = []
    for i in range(teeth):
        angle = 2 * math.pi * i / teeth
        # Outer point
        for da in [-tooth_half * 0.6, tooth_half * 0.6]:
            a = angle + da
            points.append((cx + int(outer_r * math.cos(a)), cy + int(outer_r * math.sin(a))))
        # Inner point
        mid = angle + math.pi / teeth
        for da in [-tooth_half * 0.4, tooth_half * 0.4]:
            a = mid + da
            points.append((cx + int(inner_r * math.cos(a)), cy + int(inner_r * math.sin(a))))

    draw.polygon(points, outline=c, width=lw)

    # Center hole
    hole_r = int(s * 0.12)
    draw.ellipse([cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r], outline=c, width=lw)

    return _finish(img, size)


def _draw_logout(size: int, color: str) -> Image.Image:
    """Door with arrow pointing out — logout icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))

    # Door frame (open bracket shape)
    dl = int(s * 0.45)
    dt = int(s * 0.15)
    dr = int(s * 0.82)
    db = int(s * 0.85)
    draw.line([(dl, dt), (dr, dt)], fill=c, width=lw)
    draw.line([(dr, dt), (dr, db)], fill=c, width=lw)
    draw.line([(dl, db), (dr, db)], fill=c, width=lw)

    # Arrow pointing left (exiting)
    arrow_y = s // 2
    arrow_l = int(s * 0.10)
    arrow_r = int(s * 0.52)
    draw.line([(arrow_l, arrow_y), (arrow_r, arrow_y)], fill=c, width=lw)
    # Arrow head
    ah = int(s * 0.10)
    draw.line([(arrow_l, arrow_y), (arrow_l + ah, arrow_y - ah)], fill=c, width=lw)
    draw.line([(arrow_l, arrow_y), (arrow_l + ah, arrow_y + ah)], fill=c, width=lw)

    return _finish(img, size)


def _draw_bell(size: int, color: str) -> Image.Image:
    """Alias for alerts bell — used in topbar."""
    return _draw_alerts(size, color)


def _draw_power(size: int, color: str) -> Image.Image:
    """Power button icon — circle with line at top."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.07))
    cx, cy = s // 2, s // 2
    r = int(s * 0.30)

    # Circle (open at top)
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=50, end=310, fill=c, width=lw)

    # Vertical line at top
    line_top = int(s * 0.15)
    line_bot = cy
    draw.line([(cx, line_top), (cx, line_bot)], fill=c, width=lw)

    return _finish(img, size)


def _draw_back_arrow(size: int, color: str) -> Image.Image:
    """Left-pointing arrow — back navigation."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.07))
    cy = s // 2

    # Shaft
    shaft_l = int(s * 0.20)
    shaft_r = int(s * 0.80)
    draw.line([(shaft_l, cy), (shaft_r, cy)], fill=c, width=lw)

    # Arrow head
    ah = int(s * 0.18)
    draw.line([(shaft_l, cy), (shaft_l + ah, cy - ah)], fill=c, width=lw)
    draw.line([(shaft_l, cy), (shaft_l + ah, cy + ah)], fill=c, width=lw)

    return _finish(img, size)


def _draw_crash_count(size: int, color: str) -> Image.Image:
    """Car with impact marks — crash count icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))

    # Car body
    body_l = int(s * 0.12)
    body_r = int(s * 0.75)
    body_t = int(s * 0.40)
    body_b = int(s * 0.68)
    r = int(s * 0.06)
    draw.rounded_rectangle([body_l, body_t, body_r, body_b], radius=r, outline=c, width=lw)

    # Car roof
    roof_l = int(s * 0.25)
    roof_r = int(s * 0.60)
    roof_t = int(s * 0.24)
    draw.line([(body_l + int(s * 0.10), body_t), (roof_l, roof_t)], fill=c, width=lw)
    draw.line([(roof_l, roof_t), (roof_r, roof_t)], fill=c, width=lw)
    draw.line([(roof_r, roof_t), (body_r - int(s * 0.05), body_t)], fill=c, width=lw)

    # Wheels
    wh_r = int(s * 0.07)
    wh_y = body_b
    for wx_frac in [0.28, 0.60]:
        wx = int(s * wx_frac)
        draw.ellipse([wx - wh_r, wh_y - wh_r, wx + wh_r, wh_y + wh_r], outline=c, width=lw)

    # Impact lines (right side)
    for dy in [-int(s * 0.10), 0, int(s * 0.10)]:
        x0 = int(s * 0.80)
        x1 = int(s * 0.90)
        y = int(s * 0.50) + dy
        draw.line([(x0, y), (x1, y)], fill=c, width=max(1, lw // 2))

    return _finish(img, size)


def _draw_recovery_time(size: int, color: str) -> Image.Image:
    """Clock with circular arrow — recovery time icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    cx, cy = s // 2, s // 2
    r = int(s * 0.34)

    # Clock circle
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=lw)

    # Hour hand (pointing to 12)
    draw.line([(cx, cy), (cx, cy - int(r * 0.65))], fill=c, width=lw)
    # Minute hand (pointing to 3)
    draw.line([(cx, cy), (cx + int(r * 0.50), cy)], fill=c, width=lw)

    # Circular arrow (refresh arc) outside the clock
    ar = r + int(s * 0.08)
    draw.arc([cx - ar, cy - ar, cx + ar, cy + ar], start=220, end=320, fill=c, width=lw)
    # Arrow tip
    tip_angle = math.radians(320)
    tip_x = cx + int(ar * math.cos(tip_angle))
    tip_y = cy + int(ar * math.sin(tip_angle))
    ah = int(s * 0.06)
    draw.line([(tip_x, tip_y), (tip_x + ah, tip_y - ah)], fill=c, width=lw)
    draw.line([(tip_x, tip_y), (tip_x - ah, tip_y - ah)], fill=c, width=lw)

    return _finish(img, size)


def _draw_anomaly_score(size: int, color: str) -> Image.Image:
    """Zigzag heartbeat / pulse line — anomaly score icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))

    # Shield outline
    shield_points = [
        (int(s * 0.50), int(s * 0.10)),  # top center
        (int(s * 0.85), int(s * 0.28)),  # right
        (int(s * 0.80), int(s * 0.60)),  # right lower
        (int(s * 0.50), int(s * 0.88)),  # bottom
        (int(s * 0.20), int(s * 0.60)),  # left lower
        (int(s * 0.15), int(s * 0.28)),  # left
    ]
    draw.polygon(shield_points, outline=c, width=lw)

    # ECG/pulse line across the middle
    pulse_y = int(s * 0.48)
    pulse_points = [
        (int(s * 0.22), pulse_y),
        (int(s * 0.35), pulse_y),
        (int(s * 0.40), int(s * 0.28)),
        (int(s * 0.45), int(s * 0.65)),
        (int(s * 0.50), int(s * 0.35)),
        (int(s * 0.55), pulse_y),
        (int(s * 0.62), pulse_y),
        (int(s * 0.65), int(s * 0.38)),
        (int(s * 0.68), pulse_y),
        (int(s * 0.78), pulse_y),
    ]
    draw.line(pulse_points, fill=c, width=lw, joint="curve")

    return _finish(img, size)


def _draw_active_alerts(size: int, color: str) -> Image.Image:
    """Triangle with exclamation mark — warning/active alerts icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    cx = s // 2

    # Triangle
    tri_top = int(s * 0.12)
    tri_bot = int(s * 0.85)
    tri_left = int(s * 0.10)
    tri_right = int(s * 0.90)
    draw.polygon([
        (cx, tri_top),
        (tri_right, tri_bot),
        (tri_left, tri_bot),
    ], outline=c, width=lw)

    # Exclamation mark stem
    ex_top = int(s * 0.32)
    ex_bot = int(s * 0.58)
    draw.line([(cx, ex_top), (cx, ex_bot)], fill=c, width=lw + 1)

    # Exclamation dot
    dot_r = int(s * 0.04)
    dot_y = int(s * 0.70)
    draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=c)

    return _finish(img, size)


def _draw_thresholds(size: int, color: str) -> Image.Image:
    """Horizontal slider bars — alert thresholds icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    pad_l = int(s * 0.15)
    pad_r = int(s * 0.85)
    for i, (frac, knob_frac) in enumerate([(0.30, 0.55), (0.50, 0.35), (0.70, 0.70)]):
        y = int(s * frac)
        draw.line([(pad_l, y), (pad_r, y)], fill=_hex_to_rgba(color, 80), width=max(2, lw))
        kx = int(s * knob_frac)
        draw.line([(pad_l, y), (kx, y)], fill=c, width=max(2, lw))
        kr = int(s * 0.06)
        draw.ellipse([kx - kr, y - kr, kx + kr, y + kr], fill=c)
    return _finish(img, size)


def _draw_ml_brain(size: int, color: str) -> Image.Image:
    """Brain/circuit — ML prediction icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    cx, cy = s // 2, s // 2
    r = int(s * 0.32)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=lw)
    draw.line([(cx - int(r * 0.5), cy), (cx + int(r * 0.5), cy)], fill=c, width=lw)
    draw.line([(cx, cy - int(r * 0.5)), (cx, cy + int(r * 0.5))], fill=c, width=lw)
    nr = int(s * 0.04)
    for dx, dy in [(-0.5, 0), (0.5, 0), (0, -0.5), (0, 0.5)]:
        nx = cx + int(r * dx)
        ny = cy + int(r * dy)
        draw.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=c)
    draw.line([(cx - int(r * 0.35), cy - int(r * 0.35)), (cx, cy)], fill=c, width=max(1, lw // 2))
    draw.line([(cx + int(r * 0.35), cy + int(r * 0.35)), (cx, cy)], fill=c, width=max(1, lw // 2))
    return _finish(img, size)


def _draw_notification_bell(size: int, color: str) -> Image.Image:
    """Bell with notification dot — notification settings icon."""
    img = _draw_alerts(size, color)
    # Add a notification dot on top-right
    draw = ImageDraw.Draw(img, "RGBA")
    c = _hex_to_rgba(color)
    dot_r = max(2, int(size * 0.08))
    dot_x = int(size * 0.72)
    dot_y = int(size * 0.18)
    draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=c)
    return img


def _draw_user_group(size: int, color: str) -> Image.Image:
    """Two people silhouettes — user management icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    # Front person
    cx1, head_r = int(s * 0.40), int(s * 0.10)
    head_y = int(s * 0.28)
    draw.ellipse([cx1 - head_r, head_y - head_r, cx1 + head_r, head_y + head_r], outline=c, width=lw)
    body_top = head_y + head_r + int(s * 0.04)
    body_half = int(s * 0.15)
    draw.arc([cx1 - body_half, body_top, cx1 + body_half, body_top + int(s * 0.30)],
             start=0, end=180, fill=c, width=lw)
    # Back person
    cx2 = int(s * 0.62)
    draw.ellipse([cx2 - head_r, head_y - int(s * 0.03) - head_r, cx2 + head_r, head_y - int(s * 0.03) + head_r], outline=c, width=lw)
    draw.arc([cx2 - body_half, body_top - int(s * 0.03), cx2 + body_half, body_top + int(s * 0.27)],
             start=0, end=180, fill=c, width=lw)
    return _finish(img, size)


def _draw_shield_lock(size: int, color: str) -> Image.Image:
    """Shield with lock — account security icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    pts = [
        (int(s * 0.50), int(s * 0.10)),
        (int(s * 0.85), int(s * 0.28)),
        (int(s * 0.78), int(s * 0.62)),
        (int(s * 0.50), int(s * 0.88)),
        (int(s * 0.22), int(s * 0.62)),
        (int(s * 0.15), int(s * 0.28)),
    ]
    draw.polygon(pts, outline=c, width=lw)
    cx = s // 2
    lock_w, lock_h = int(s * 0.14), int(s * 0.12)
    lock_y = int(s * 0.48)
    draw.rounded_rectangle([cx - lock_w, lock_y, cx + lock_w, lock_y + lock_h],
                           radius=int(s * 0.03), outline=c, width=lw)
    shackle_r = int(s * 0.08)
    draw.arc([cx - shackle_r, lock_y - shackle_r * 2, cx + shackle_r, lock_y],
             start=180, end=0, fill=c, width=lw)
    return _finish(img, size)


def _draw_crash_incident(size: int, color: str) -> Image.Image:
    """Lightning bolt — crash incident icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    bolt_pts = [
        (int(s * 0.55), int(s * 0.10)),
        (int(s * 0.30), int(s * 0.48)),
        (int(s * 0.48), int(s * 0.48)),
        (int(s * 0.42), int(s * 0.90)),
        (int(s * 0.72), int(s * 0.45)),
        (int(s * 0.52), int(s * 0.45)),
    ]
    draw.polygon(bolt_pts, fill=c)
    return _finish(img, size)


def _draw_info_circle(size: int, color: str) -> Image.Image:
    """Circle with 'i' — info / summary icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.06))
    cx, cy = s // 2, s // 2
    r = int(s * 0.36)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=lw)
    dot_r = int(s * 0.045)
    dot_y = int(s * 0.32)
    draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=c)
    draw.line([(cx, int(s * 0.42)), (cx, int(s * 0.68))], fill=c, width=lw + 1)
    return _finish(img, size)


def _draw_dropdown_arrow(size: int, color: str) -> Image.Image:
    """Chevron down — dropdown arrow icon."""
    img, draw, s, sc = _new_canvas(size)
    c = _hex_to_rgba(color)
    lw = max(2, int(s * 0.07))
    cx = s // 2
    draw.line([(int(s * 0.25), int(s * 0.38)), (cx, int(s * 0.62))], fill=c, width=lw)
    draw.line([(cx, int(s * 0.62)), (int(s * 0.75), int(s * 0.38))], fill=c, width=lw)
    return _finish(img, size)


# ═══════════════════════════════════════════════════════════════
#  ICON REGISTRY & PUBLIC API
# ═══════════════════════════════════════════════════════════════

_ICON_MAP = {
    "dashboard":         _draw_dashboard,
    "alerts":            _draw_alerts,
    "crash-details":     _draw_crash_details,
    "logs":              _draw_logs,
    "prediction":        _draw_prediction,
    "settings":          _draw_settings,
    "logout":            _draw_logout,
    "bell":              _draw_bell,
    "power":             _draw_power,
    "back_arrow":        _draw_back_arrow,
    "crash_count":       _draw_crash_count,
    "recovery_time":     _draw_recovery_time,
    "anomaly_score":     _draw_anomaly_score,
    "active_alerts":     _draw_active_alerts,
    "thresholds":        _draw_thresholds,
    "ml_brain":          _draw_ml_brain,
    "notification_bell": _draw_notification_bell,
    "user_group":        _draw_user_group,
    "shield_lock":       _draw_shield_lock,
    "crash_incident":    _draw_crash_incident,
    "info_circle":       _draw_info_circle,
    "dropdown_arrow":    _draw_dropdown_arrow,
}

# Cache to avoid regenerating the same icon multiple times
_cache: dict[tuple, ctk.CTkImage] = {}


def get_icon(name: str, size: int = 20, color: str = "#9ca3af") -> ctk.CTkImage:
    """
    Retrieve (or generate and cache) a ``CTkImage`` icon.

    Args:
        name:  One of the keys in ``_ICON_MAP``.
        size:  Target pixel size (width = height).
        color: Hex colour for the icon strokes.

    Returns:
        A ``CTkImage`` suitable for CTkButton / CTkLabel ``image`` parameter.
    """
    key = (name, size, color)
    if key not in _cache:
        draw_fn = _ICON_MAP.get(name)
        if draw_fn is None:
            raise ValueError(f"Unknown icon: {name!r}. Available: {list(_ICON_MAP)}")
        pil_img = draw_fn(size, color)
        _cache[key] = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
    return _cache[key]

