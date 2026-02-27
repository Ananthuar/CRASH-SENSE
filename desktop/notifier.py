"""
CrashSense — Proactive Crash Warning Notifier
===============================================

Runs as a background daemon thread in the desktop application.
Every POLL_INTERVAL seconds it calls /api/process-alerts/new to see if
any NEW crash precursors have been detected since the last check.

On a new alert it:
  1. Fires a native Linux desktop notification via `notify-send` (if available).
  2. Invokes an optional in-app callback so the UI can show a banner.

Usage::

    from desktop.notifier import CrashWarningNotifier
    notifier = CrashWarningNotifier(on_alert=my_callback)
    notifier.start()
    ...
    notifier.stop()
"""

import threading
import time
import requests
from plyer import notification

_API_BASE = "http://127.0.0.1:5000"
POLL_INTERVAL = 5   # Seconds between polling cycles

# How far back to look on the FIRST poll (catch alerts detected before app opened)
INITIAL_LOOKBACK_SEC = 300   # 5 minutes

# Severity → readable label
_SEV_LABEL = {
    "critical": "CRITICAL",
    "high":     "HIGH",
    "medium":   "WARNING",
    "low":      "INFO",
}

# Alert type → human readable category
_TYPE_LABEL = {
    "memory_leak":       "Memory Leak",
    "cpu_runaway":       "CPU Runaway",
    "thread_explosion":  "Thread Explosion",
    "high_thread_count": "High Thread Count",
    "fd_exhaustion":     "File Descriptor Exhaustion",
    "zombie":            "Zombie Process",
    "oom_risk":          "OOM Kill Risk",
}


class CrashWarningNotifier:
    """
    Background notifier that proactively warns users about crash precursors
    BEFORE a crash actually happens.

    Args:
        on_alert: Optional callback(alert_list) invoked on the main thread
                  when new alerts are received. Use this to show in-app banners.
    """

    def __init__(self, on_alert=None):
        self._on_alert = on_alert
        self._running  = False
        self._thread   = None
        # Start lookback so alerts detected before the app opened still notify
        self._last_poll_time: float = time.time() - INITIAL_LOOKBACK_SEC
        self._is_first_poll = True

        # Independently toggled by Settings screen
        self.desktop_enabled: bool = True   # OS notify-send notifications
        self.inapp_enabled:   bool = True   # In-app banner callback

    def start(self):
        """Start the background polling thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background polling thread."""
        self._running = False

    # ─────────────────────────────────────────────────────────────
    #  Internal
    # ─────────────────────────────────────────────────────────────

    def _poll_loop(self):
        # Give the backend a moment to come up before we start polling
        time.sleep(3)
        while self._running:
            try:
                self._check_for_new_alerts()
            except Exception:
                pass  # Never let the notifier die
            self._is_first_poll = False
            time.sleep(POLL_INTERVAL)

    def _check_for_new_alerts(self):
        since = self._last_poll_time
        resp = requests.get(
            f"{_API_BASE}/api/process-alerts/new",
            params={"since": since},
            timeout=3,
        )
        if resp.status_code != 200:
            return

        data = resp.json()
        self._last_poll_time = data.get("server_time", time.time())
        new_alerts = data.get("alerts", [])

        if not new_alerts:
            return

        # Fire native OS notifications if enabled
        if self.desktop_enabled:
            for alert in new_alerts:
                self._send_os_notification(alert)

        # Fire in-app callback if enabled
        if self.inapp_enabled and self._on_alert:
            try:
                self._on_alert(new_alerts)
            except Exception:
                pass

    def _send_os_notification(self, alert: dict):
        """Fire a native cross-platform desktop notification via plyer."""
        sev        = alert.get("severity", "low")
        alert_type = alert.get("type", "unknown")
        name       = alert.get("name", "?")
        pid        = alert.get("pid", "?")
        detail     = alert.get("detail", "")
        metric     = alert.get("metric", "")

        sev_label  = _SEV_LABEL.get(sev, "ALERT")
        type_label = _TYPE_LABEL.get(alert_type, alert_type.replace("_", " ").title())

        title = f"CrashSense [{sev_label}]: {type_label}"
        body  = f"{name} (PID {pid})\n{detail}\n{metric}".strip()

        try:
            notification.notify(
                title=title,
                message=body,
                app_name="CrashSense",
                timeout=8,
            )
        except Exception:
            pass


# Singleton instance
crash_warning_notifier = CrashWarningNotifier()
