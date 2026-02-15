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
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import config
from core.collector import system_monitor
from core.preprocessor import data_scaler


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
            'version': '0.1.0'
        })

    # ── Route: Welcome Page ─────────────────────────────────────
    @app.route('/')
    def index():
        """Renders a minimal HTML welcome page confirming the API is running."""
        return "<h1>CRASH SENSE API</h1><p>The backend is running. Use /api/health to check status.</p>"

    # ── Route: Current Metrics ──────────────────────────────────
    @app.route('/api/metrics/current', methods=['GET'])
    def get_current_metrics():
        """
        Return the most recent system metrics snapshot.

        Query Parameters:
            normalized (str): If 'true', applies min-max / log normalisation
                              via the DataScaler before returning the metrics.

        Returns:
            JSON dict of metric key-value pairs, or empty dict if no
            metrics have been collected yet.
        """
        metrics = system_monitor.get_latest_metrics()
        if not metrics:
            return jsonify({})

        # Check if the caller wants normalised (0-1) values
        normalized = request.args.get('normalized', 'false').lower() == 'true'
        if normalized:
            return jsonify(data_scaler.normalize_metrics(metrics))

        return jsonify(metrics)

    # ── Future: Blueprint Registration ──────────────────────────
    # from .api import api_bp
    # app.register_blueprint(api_bp, url_prefix='/api')

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
