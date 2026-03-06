"""
CrashSense — Minimum Viable Email Notifier
==========================================

Sends an email notification when a critical process alert is generated.
"""
import threading
from firebase_service import send_email_notification

class EmailNotifier:
    def __init__(self):
        pass
        
    def send_critical_alert_async(self, alert: dict, target_email: str):
        """Send an email asynchronously to avoid blocking the monitor loop."""
        def _send():
            try:
                subject = f"CrashSense Critical Alert: {alert.get('name')}"
                body = (
                    f"CRITICAL ALERT DETECTED\n\n"
                    f"Type: {alert.get('type')}\n"
                    f"Process: {alert.get('name')} (PID {alert.get('pid')})\n"
                    f"Details: {alert.get('detail')}\n"
                    f"Metric: {alert.get('metric')}\n"
                )
                
                send_email_notification(target_email, subject, body)
                print(f"[EmailNotifier] Firebase email queued to {target_email} for critical alert on {alert.get('name')}")
            except Exception as e:
                print(f"[EmailNotifier] Failed to queue email: {e}")
                
        threading.Thread(target=_send, daemon=True).start()

email_notifier = EmailNotifier()
