"""
CrashSense — Application Configuration
========================================

Defines environment-specific configuration classes using the
Flask configuration pattern. The `config` dictionary at the bottom
maps environment names to their corresponding config classes.

Configuration Hierarchy:
    Config (base)
    ├── DevelopmentConfig  (DEBUG=True)   ← default
    └── ProductionConfig   (DEBUG=False)

Usage:
    app.config.from_object(config['development'])
    app.config.from_object(config[os.environ.get('FLASK_CONFIG', 'default')])

Environment Variables:
    SECRET_KEY      — Flask session signing key (falls back to a dev default)
    FLASK_CONFIG    — Config profile name ('development' or 'production')
"""

import os


class Config:
    """
    Base configuration shared across all environments.

    Attributes:
        SECRET_KEY: Cryptographic key for session signing and CSRF protection.
                    In production, this MUST be set via the SECRET_KEY env var.
        DEBUG:      Disabled by default; overridden in subclasses.
        TESTING:    Disabled by default; enable for test suites.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string-for-dev'
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration — enables Flask debug mode and auto-reload."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration — debug mode disabled for security."""
    DEBUG = False


# ── Environment name → Config class mapping ────────────────────
# 'default' aliases to DevelopmentConfig for quick local development.
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
