"""
CrashSense — Flask Application Factory
========================================

Defines the Flask application using the **factory pattern** (create_app).
This module serves as the backend REST API for the CrashSense platform.

Architecture:
    create_app(config_name)
        │
        ├── Loads configuration from config.py
        ├── Enables CORS for cross-origin frontend access
        ├── Starts the SystemMonitor background polling thread
        └── Registers API routes:
              GET  /                      → HTML welcome page
              GET  /api/health            → Service health check
              GET  /api/status            → Monitoring status
              GET  /api/metrics/current   → Latest system metrics
                   ?normalized=true       → Returns 0-1 normalised values
              GET  /auth/google           → Firebase Google Sign-In page
              GET  /auth/phone            → Firebase Phone Sign-In page
              GET  /auth/email            → Firebase Email Link Sign-In page

Dependencies:
    - SystemMonitor (core/collector.py)  — provides live metrics
    - DataScaler (core/preprocessor.py)  — normalises metric values

Usage:
    # Development
    python app.py

    # Production
    gunicorn 'app:create_app("production")'
"""

import os
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv
from config import config
from core.collector import system_monitor
from core.preprocessor import data_scaler
from core.crash_predictor import crash_predictor
from core.process_monitor import process_monitor
import firebase_service
from auth_html import GOOGLE_AUTH_HTML, PHONE_AUTH_HTML, EMAIL_LINK_AUTH_HTML

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
load_dotenv()  # also pick up backend/.env if present
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN", "")
FIREBASE_PROJECT_ID  = os.getenv("FIREBASE_PROJECT_ID", "")

# Private aliases for render_template_string
_GOOGLE_AUTH_HTML = GOOGLE_AUTH_HTML
_PHONE_AUTH_HTML  = PHONE_AUTH_HTML
_EMAIL_LINK_HTML  = EMAIL_LINK_AUTH_HTML


def create_app(config_name=None):
    """
    Application factory — creates and configures a Flask instance.

    Args:
        config_name: Configuration profile to use. One of 'development',
                     'production', or 'default'. Falls back to the
                     FLASK_CONFIG environment variable if not provided.

    Returns:
        Flask: Configured Flask application instance with all routes
               registered and the system monitor running.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Enable CORS so the frontend (or desktop app) can call the API
    CORS(app)

    # Start the background metrics collection thread.
    # Polls CPU, memory, disk I/O, and network I/O every 0.5 seconds.
    system_monitor.start()

    # Start the per-process crash detection monitor.
    process_monitor.start()

    # Initialise Firebase Admin SDK (Firestore)
    firebase_service.init_firebase()

    # ── Route: Google Auth Page ──────────────────────────────────
    @app.route('/auth/google')
    def google_auth_page():
        """Browser page that handles Google Sign-In via Firebase JS SDK."""
        callback_url = request.args.get('callback', 'http://localhost:5557')
        return render_template_string(_GOOGLE_AUTH_HTML,
                                      api_key=FIREBASE_WEB_API_KEY,
                                      auth_domain=FIREBASE_AUTH_DOMAIN,
                                      project_id=FIREBASE_PROJECT_ID,
                                      callback_url=callback_url)

    # ── Route: Phone Auth Page ───────────────────────────────────
    @app.route('/auth/phone')
    def phone_auth_page():
        """Browser page that handles Phone Sign-In via Firebase JS SDK."""
        callback_url = request.args.get('callback', 'http://localhost:5557')
        return render_template_string(_PHONE_AUTH_HTML,
                                      api_key=FIREBASE_WEB_API_KEY,
                                      auth_domain=FIREBASE_AUTH_DOMAIN,
                                      project_id=FIREBASE_PROJECT_ID,
                                      callback_url=callback_url)

    # ── Route: Email Link Auth Page ──────────────────────────────
    @app.route('/auth/email')
    def email_auth_page():
        """Browser page for passwordless email link sign-in via Firebase."""
        callback_url = request.args.get('callback', 'http://localhost:5557')
        return render_template_string(_EMAIL_LINK_HTML,
                                      api_key=FIREBASE_WEB_API_KEY,
                                      auth_domain=FIREBASE_AUTH_DOMAIN,
                                      project_id=FIREBASE_PROJECT_ID,
                                      callback_url=callback_url)

    # ── Route: User Profile (Create) ────────────────────────────
    @app.route('/api/users/<uid>/profile', methods=['POST'])
    def create_user_profile(uid):
        """Create a Firestore profile document for a new user."""
        data = request.get_json(force=True, silent=True) or {}
        try:
            profile = firebase_service.create_user_profile(uid, data)
            return jsonify(profile), 201
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Route: User Profile (Get) ────────────────────────────────
    @app.route('/api/users/<uid>/profile', methods=['GET'])
    def get_user_profile(uid):
        """Fetch a user's Firestore profile."""
        try:
            profile = firebase_service.get_user_profile(uid)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            return jsonify(profile)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Route: User Profile (Update) ────────────────────────────
    @app.route('/api/users/<uid>/profile', methods=['PUT'])
    def update_user_profile(uid):
        """Update fields in a user's Firestore profile."""
        data = request.get_json(force=True, silent=True) or {}
        try:
            updated = firebase_service.update_user_profile(uid, data)
            return jsonify(updated)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Route: User Settings (Get) ──────────────────────────────
    @app.route('/api/users/<uid>/settings', methods=['GET'])
    def get_user_settings(uid):
        """Fetch a user's Firestore config and apply to monitor."""
        try:
            settings = firebase_service.get_user_settings(uid)
            if settings is None:
                return jsonify({}), 200 # Return empty dict if no settings exist yet
            
            # Apply to backend immediately upon fetch
            _apply_monitor_settings(settings)
            return jsonify(settings)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Route: User Settings (Update) ───────────────────────────
    @app.route('/api/users/<uid>/settings', methods=['PUT'])
    def update_user_settings(uid):
        """Update fields in a user's Firestore config and apply to metrics."""
        data = request.get_json(force=True, silent=True) or {}
        try:
            updated = firebase_service.update_user_settings(uid, data)
            _apply_monitor_settings(updated)
            return jsonify(updated)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    def _apply_monitor_settings(settings: dict):
        """Helper to mutate the absolute module-level threshold variables in the detector."""
        import core.process_monitor as pm
        
        if "cpu_alert" in settings:
            pm.CPU_RUNAWAY_PERCENT = float(settings["cpu_alert"])
        if "memory_alert" in settings:
            pm.OOM_RAM_PERCENT = float(settings["memory_alert"])
        if "thread_alert" in settings:
            pm.THREAD_MAX_COUNT = int(settings["thread_alert"])
        if "response_alert" in settings:
            pm.SCAN_INTERVAL = max(1, int(settings["response_alert"]))

    # ── Route: List All Users ────────────────────────────────────
    @app.route('/api/users', methods=['GET'])
    def list_users():
        """Return all user profiles from Firestore."""
        try:
            users = firebase_service.list_all_users()
            return jsonify(users)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Route: Monitoring Status ────────────────────────────────
    @app.route('/api/status')
    def status():
        """Returns a simple JSON status indicating monitoring is active."""
        return jsonify({"status": "monitoring"})

    # ── Route: Health Check ─────────────────────────────────────
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """
        Standard health check endpoint for load balancers and uptime monitors.

        Returns:
            JSON with service name, version, and health status.
        """
        return jsonify({
            'status': 'healthy',
            'service': 'CRASH SENSE Agent',
            'version': 'v1.1.1'
        })

    # ── Route: Welcome Page ─────────────────────────────────────
    @app.route('/')
    def index():
        """Renders a minimal HTML welcome page confirming the API is running."""
        return "<h1>CRASH SENSE API</h1><p>The backend is running. Use /api/health to check status.</p>"

    # ── Route: Current Metrics ──────────────────────────────────
    @app.route('/api/metrics/current', methods=['GET'])
    def get_current_metrics():
        metrics = system_monitor.get_latest_metrics()
        if not metrics:
            return jsonify({})
        normalized = request.args.get('normalized', 'false').lower() == 'true'
        if normalized:
            return jsonify(data_scaler.normalize_metrics(metrics))
        return jsonify(metrics)

    # ── Route: Crash Prediction ─────────────────────────────────
    @app.route('/api/prediction', methods=['GET'])
    def get_prediction():
        """Return AI crash probability, risk factors, and actions."""
        result = crash_predictor.predict()
        return jsonify(result)

    @app.route('/api/prediction/trend', methods=['GET'])
    def get_prediction_trend():
        """Return recent crash probability history for charts."""
        return jsonify(crash_predictor.get_trend())

    # ── Route: Process Alerts ──────────────────────────────────
    @app.route('/api/process-alerts', methods=['GET'])
    def get_process_alerts():
        """Return per-process crash detection alerts."""
        return jsonify({
            "alerts":  process_monitor.get_alerts(),
            "summary": process_monitor.get_summary(),
        })

    @app.route('/api/process-stats', methods=['GET'])
    def get_process_stats():
        """Return top processes by resource usage."""
        return jsonify(process_monitor.get_top_processes())

    @app.route('/api/process-alerts/trend', methods=['GET'])
    def get_process_alerts_trend():
        """Return recent health score history for charts."""
        return jsonify(process_monitor.get_health_trend())

    @app.route('/api/process-alerts/new', methods=['GET'])
    def get_new_process_alerts():
        """Return alerts detected after the given 'since' Unix timestamp.
        
        Query param:
            since (float): Unix timestamp. Only alerts newer than this are returned.
        
        This endpoint enables efficient proactive polling so the desktop can
        fire a warning notification as soon as a crash precursor is first detected,
        without re-processing alerts it has already seen.
        """
        try:
            since = float(request.args.get('since', 0))
        except (TypeError, ValueError):
            since = 0.0

        all_alerts = process_monitor.get_alerts()
        new_alerts = [a for a in all_alerts if a.get("detected_at", 0) > since]
        return jsonify({
            "alerts": new_alerts,
            "server_time": __import__('time').time(),
        })

    @app.route('/api/process-history/<int:pid>', methods=['GET'])
    def get_process_history(pid):
        """Return the snapshot history (CPU, memory, threads, FDs) for a single PID.
        Used by the Crash Details screen to render per-process resource charts.
        """
        history = process_monitor.get_process_history(pid)
        alerts  = process_monitor.get_alerts_for_pid(pid)
        return jsonify({
            "pid":     pid,
            "history": history,
            "alerts":  alerts,
        })

    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        """Return structured log entries derived from live process-monitor data.

        Each entry matches the schema:
            { time, level, module, type, msg }

        Sources:
          1. Active alerts  → ERROR / WARN entries per alert
          2. Health trend   → INFO entries showing score transitions
        """
        import time as _time
        from datetime import datetime as _dt

        entries = []

        # ── Source 1: active alerts ─────────────────────────────────
        _sev_level = {"critical": "ERROR", "high": "ERROR",
                      "medium": "WARN",  "low": "INFO"}
        for alert in process_monitor.get_alerts():
            ts  = alert.get("timestamp", _time.time())
            entries.append({
                "time":   _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                "level":  _sev_level.get(alert.get("severity", "low"), "INFO"),
                "module": alert.get("name", "Unknown")[:20],
                "type":   alert.get("type", "").replace("_", " ").title(),
                "msg":    alert.get("detail", alert.get("title", "")),
                "pid":    alert.get("pid"),
                "severity": alert.get("severity", "low"),
            })

        # ── Source 2: health trend snapshots (INFO / WARN) ──────────
        for snap in process_monitor.get_health_trend():
            score = snap.get("health_score", 100)
            ts    = snap.get("timestamp", _time.time())
            if score < 50:
                level = "WARN"
                msg   = f"System health degraded: score={score}"
            elif score < 80:
                level = "INFO"
                msg   = f"System health warning: score={score}"
            else:
                level = "INFO"
                msg   = f"System health nominal: score={score}"
            entries.append({
                "time":   _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                "level":  level,
                "module": "ProcessMonitor",
                "type":   "Health Check",
                "msg":    msg,
                "pid":    None,
                "severity": "low" if score >= 80 else "medium" if score >= 50 else "high",
            })

        # Sort newest first
        entries.sort(key=lambda e: e["time"], reverse=True)

        # Compute analytics
        error_count = sum(1 for e in entries if e["level"] == "ERROR")
        warn_count  = sum(1 for e in entries if e["level"] == "WARN")
        # Most affected module
        from collections import Counter
        mod_counts = Counter(e["module"] for e in entries if e["level"] == "ERROR")
        top_module = mod_counts.most_common(1)[0] if mod_counts else ("None", 0)

        return jsonify({
            "entries":          entries,
            "total":            len(entries),
            "error_count":      error_count,
            "warn_count":       warn_count,
            "top_module":       top_module[0],
            "top_module_count": top_module[1],
        })

    @app.route('/api/ml-status', methods=['GET'])
    def get_ml_status():
        """Return ML model metadata and enabled state."""
        import os, joblib
        model_path = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "models", "crash_rf_model.joblib"
        ))
        model_version  = "N/A"
        accuracy       = None
        trained_at     = "March 2, 2026"
        model_loaded   = crash_predictor._rf_loaded

        if os.path.exists(model_path):
            try:
                bundle = joblib.load(model_path)
                model_version = bundle.get("version", "unknown")
                accuracy      = bundle.get("accuracy", None)
            except Exception:
                pass

        return jsonify({
            "enabled":       getattr(crash_predictor, "_ml_enabled", True),
            "model_version": f"v{model_version}",
            "accuracy":      f"{accuracy:.4f}" if accuracy is not None else "N/A",
            "trained_at":    trained_at or "Unknown",
            "model_loaded":  model_loaded,
        })

    @app.route('/api/ml-status', methods=['PUT'])
    def set_ml_status():
        """Enable or disable ML prediction globally."""
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get("enabled", True))
        crash_predictor._ml_enabled = enabled
        return jsonify({"enabled": enabled})

    return app


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT — Development Server
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_CONFIG', 'default'))
    try:
        # Bind to all interfaces on port 5000 for local development
        app.run(host='0.0.0.0', port=5000)
    finally:
        # Ensure the metrics polling thread is cleanly stopped on shutdown
        system_monitor.stop()
        process_monitor.stop()
