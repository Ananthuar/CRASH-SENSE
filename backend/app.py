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
from core.crash_signatures import crash_sig_db
from core.resolution import system_resolver, get_post_action_validator
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
        """Return user profiles from Firestore, isolated by the requester's email domain."""
        try:
            from flask import request
            requester_email = request.args.get('email', '')
            if not requester_email or '@' not in requester_email:
                return jsonify({"error": "Missing or invalid email parameter. Tenant isolation requires requester email."}), 400
                
            domain = requester_email.split('@')[1].lower()
            all_users = firebase_service.list_all_users()
            
            filtered_users = [
                u for u in all_users 
                if u.get('email') and '@' in u['email'] and u['email'].split('@')[1].lower() == domain
            ]
            return jsonify(filtered_users)
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
            'version': 'v1.1.3'
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
        """Retrieve recent logs from Firestore."""
        uid = request.args.get('uid')
        if not uid:
            return jsonify({"error": "Missing uid parameter"}), 400

        limit_str = request.args.get('limit', '50')
        limit = int(limit_str) if limit_str.isdigit() else 50
        
        try:
            from firebase_service import get_logs as fs_get_logs
            entries = fs_get_logs(uid=uid, limit=limit)
            
            error_count = sum(1 for e in entries if e.get("level") == "ERROR")
            warn_count  = sum(1 for e in entries if e.get("level") == "WARN")
            from collections import Counter
            mod_counts = Counter(e.get("module") for e in entries if e.get("level") == "ERROR")
            top_module = mod_counts.most_common(1)[0] if mod_counts else ("None", 0)
            
            return jsonify({
                "entries":          entries,
                "total":            len(entries),
                "error_count":      error_count,
                "warn_count":       warn_count,
                "top_module":       top_module[0],
                "top_module_count": top_module[1]
            })
        except Exception as e:
            return jsonify({
                "entries": [],
                "total": 0,
                "error_count": 0,
                "warn_count": 0,
                "top_module": "None",
                "top_module_count": 0
            })

    @app.route('/api/session', methods=['POST'])
    def sync_session():
        """Syncs the current desktop session's active UID with the backend process monitor."""
        data = request.get_json(silent=True) or {}
        uid = data.get('uid')
        if uid:
            process_monitor.active_uid = uid
            return jsonify({"status": "ok"}), 200
        return jsonify({"error": "missing uid"}), 400

    @app.route('/api/ml-status', methods=['GET'])
    def get_ml_status():
        """Return ML model metadata and enabled state."""
        import os, joblib
        model_path = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "models", "crash_rf_model.joblib"
        ))
        model_version  = "1.1.0"
        accuracy       = None
        trained_at     = "March 2, 2026"
        model_loaded   = crash_predictor._rf_loaded

        if os.path.exists(model_path):
            try:
                bundle = joblib.load(model_path)
                model_version = bundle.get("version", "1.1.0")
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

    # ── Route: Crash Signatures DB (FR-05) ──────────────────────
    @app.route('/api/signatures', methods=['GET'])
    def get_signatures():
        """
        FR-05: Query the crash signatures database.

        Query params:
            q (str): Search text (e.g. 'OOM Error'). If omitted, returns all.

        Returns:
            JSON list of {signature, actions, category}.
        """
        q = request.args.get('q', '').strip()
        if q:
            results = crash_sig_db.query(q)
        else:
            results = crash_sig_db.get_all()
        return jsonify({"signatures": results, "query": q, "count": len(results)})

    @app.route('/api/signatures', methods=['POST'])
    def add_signature():
        """Add or update a crash signature mapping."""
        data = request.get_json(silent=True) or {}
        pattern  = data.get('pattern', '').strip()
        actions  = data.get('actions', [])
        category = data.get('category', 'general')
        if not pattern or not actions:
            return jsonify({"error": "'pattern' and 'actions' are required"}), 400
        ok = crash_sig_db.add_signature(pattern, actions, category)
        return jsonify({"success": ok}), 201 if ok else 500

    # ── Route: Log Injection (FR-02 / TC-02) ────────────────────
    @app.route('/api/logs/inject', methods=['POST'])
    def inject_log_line():
        """
        FR-02: Write a log line to the monitored log file for testing.

        Body JSON:
            line (str): The raw log line to append.
            log_file (str, optional): Path to log file (default: data/app.log)
        """
        import os as _os
        data = request.get_json(silent=True) or {}
        line = data.get('line', '').strip()
        if not line:
            return jsonify({"error": "'line' is required"}), 400

        log_path = data.get('log_file', 'data/app.log')
        abs_log_path = _os.path.abspath(
            _os.path.join(_os.path.dirname(__file__), log_path)
        )
        _os.makedirs(_os.path.dirname(abs_log_path), exist_ok=True)

        import time as _time
        from datetime import datetime as _dt
        timestamp = _dt.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        full_line = f"{timestamp} {line}\n"

        with open(abs_log_path, 'a') as f:
            f.write(full_line)

        return jsonify({"injected": full_line.strip(), "file": abs_log_path})

    # ── Route: SHAP Values (FR-04) ───────────────────────────────
    @app.route('/api/prediction/shap', methods=['GET'])
    def get_shap_values():
        """
        FR-04: Return SHAP feature attribution values from the last prediction.

        Returns:
            JSON with shap_values dict and shap_top_feature.
        """
        shap_values   = getattr(crash_predictor, '_last_shap_values', {})
        top_feature   = max(shap_values, key=lambda k: abs(shap_values[k]), default=None) \
                        if shap_values else None
        return jsonify({
            "shap_values":    shap_values,
            "shap_top_feature": top_feature,
            "feature_count":  len(shap_values),
        })

    # ── Route: Ahead Prediction (FR-03) ─────────────────────────
    @app.route('/api/prediction/ahead', methods=['GET'])
    def get_prediction_ahead():
        """
        FR-03: Return 30-second-ahead crash probability extrapolation.

        Query params:
            seconds (float, default=30): Look-ahead horizon in seconds.
        """
        try:
            seconds = float(request.args.get('seconds', 30.0))
        except (TypeError, ValueError):
            seconds = 30.0
        result = crash_predictor.predict_ahead(seconds=seconds)
        return jsonify(result)

    # ── Route: Execute Remediation (FR-07) ──────────────────────
    @app.route('/api/resolution/execute', methods=['POST'])
    def execute_remediation():
        """
        FR-07: Execute a remediation action only if permission_granted=True.

        Body JSON:
            action (str): Action name (clear_cache, kill_process, etc.)
            permission_granted (bool): User approval flag.
            pid (int, optional): Process ID for process-level actions.
            process_name (str, optional): Process name for logging.
        """
        data = request.get_json(silent=True) or {}
        action     = data.get('action', 'noop')
        permitted  = bool(data.get('permission_granted', False))
        pid        = data.get('pid')  # may be None
        proc_name  = data.get('process_name')
        result = system_resolver.execute_remediation(
            action_name=action,
            permission_granted=permitted,
            pid=int(pid) if pid is not None else None,
            process_name=proc_name,
        )
        status_code = 200 if result["permission_granted"] else 403
        return jsonify(result), status_code

    # ── Route: Resolution Status (FR-08) ────────────────────────
    @app.route('/api/resolution/status', methods=['GET'])
    def get_resolution_status():
        """
        FR-08: Return post-action health validation status.

        Returns:
            JSON with stabilization result, CPU samples, and denied actions.
        """
        validator = get_post_action_validator()
        return jsonify(validator.get_status())

    return app


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT — Development Server
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # Suppress the "WARNING: This is a development server" banner
    from flask import cli
    import logging
    cli.show_server_banner = lambda *args: None
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    
    app = create_app(os.environ.get('FLASK_CONFIG', 'default'))
    try:
        # Bind to all interfaces on port 5000 for local development
        app.run(host='0.0.0.0', port=5000)
    finally:
        # Ensure the metrics polling thread is cleanly stopped on shutdown
        system_monitor.stop()
        process_monitor.stop()
