"""
CrashSense — Demo / Mock Data Module
=====================================

Provides realistic, presentation-ready demo data for all dashboard screens.
This data is used exclusively for the front-end demonstration; in a production
deployment these would be replaced by live API calls to the Flask backend or a
database.

Sections:
    - Dashboard metrics  (4 KPI cards)
    - Crash trend data   (24-hour line chart)
    - CPU / Memory data  (resource usage area charts)
    - Alerts             (real-time alert cards)
    - Crash incident     (single detailed incident)
    - Log entries        (error-log viewer / crash-detail log)
    - Resource metrics   (resource chart at time of crash)
    - Full logs          (paginated log table)
    - Users              (settings → user management)
"""


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD SCREEN DATA
# ═══════════════════════════════════════════════════════════════

# KPI metric cards displayed at the top of the dashboard.
# Each metric includes:
#   value     – displayed prominently in large text
#   label     – metric name
#   sub       – contextual subtitle
#   trend     – percentage or count change indicator
#   trend_up  – True if the trend is negative (red), False if positive (green)
DASHBOARD_METRICS = {
    "process_count": {
        "value": "--", "label": "Processes",
        "sub": "Loading...", "trend": "Live", "trend_up": False,
    },
    "uptime": {
        "value": "--", "label": "System Uptime",
        "sub": "Loading...", "trend": "Live", "trend_up": False,
    },
    "cpu_usage": {
        "value": "--", "label": "CPU Usage",
        "sub": "Loading...", "trend": "Live", "trend_up": False,
    },
    "thread_count": {
        "value": "--", "label": "Active Threads",
        "sub": "Loading...", "trend": "Live", "trend_up": False,
    },
}

# Crash frequency data points for the 24-hour trend line chart.
CRASH_TREND_DATA = [
    {"time": "00:00", "crashes": 2},
    {"time": "04:00", "crashes": 1},
    {"time": "08:00", "crashes": 4},
    {"time": "12:00", "crashes": 3},
    {"time": "16:00", "crashes": 7},
    {"time": "20:00", "crashes": 5},
    {"time": "23:59", "crashes": 2},
]

# CPU utilisation data points for the resource area chart.
CPU_DATA = [
    {"time": "00:00", "usage": 45}, {"time": "04:00", "usage": 38},
    {"time": "08:00", "usage": 72}, {"time": "12:00", "usage": 65},
    {"time": "16:00", "usage": 88}, {"time": "20:00", "usage": 76},
    {"time": "23:59", "usage": 52},
]

# Memory utilisation data points for the resource area chart.
MEMORY_DATA = [
    {"time": "00:00", "usage": 62}, {"time": "04:00", "usage": 58},
    {"time": "08:00", "usage": 75}, {"time": "12:00", "usage": 71},
    {"time": "16:00", "usage": 85}, {"time": "20:00", "usage": 79},
    {"time": "23:59", "usage": 68},
]


# ═══════════════════════════════════════════════════════════════
#  ALERTS SCREEN DATA
# ═══════════════════════════════════════════════════════════════

# Real-time alert cards with severity levels.
# Severity hierarchy: Critical > High > Medium > Low
ALERTS = [
    {"time": "14:20:47", "module": "AuthService",     "severity": "Critical", "msg": "OutOfMemoryException in module AuthService.dll"},
    {"time": "14:18:32", "module": "DatabaseService",  "severity": "High",     "msg": "Connection timeout after 30s"},
    {"time": "14:15:21", "module": "APIGateway",       "severity": "Medium",   "msg": "High latency detected: 2.3s average"},
    {"time": "14:12:14", "module": "CacheService",     "severity": "Low",      "msg": "Cache miss rate: 23%"},
    {"time": "14:08:05", "module": "PaymentService",   "severity": "High",     "msg": "Transaction rollback due to timeout"},
    {"time": "14:02:33", "module": "UserService",      "severity": "Medium",   "msg": "Session expiry approaching for 45 users"},
]


# ═══════════════════════════════════════════════════════════════
#  CRASH DETAILS SCREEN DATA
# ═══════════════════════════════════════════════════════════════

# Single crash incident — used in the Crash Details screen.
# Contains metadata, a human-readable summary, and AI-generated root causes.
CRASH_INCIDENT = {
    "id": "CRS-2026-0147",
    "date": "January 14, 2026 - 14:20:47 UTC",
    "severity": "Critical",
    "module": "Authentication Service",
    "recovery": "3.2 seconds",
    "impact": "247 users affected",
    "summary": (
        "The authentication service experienced an out-of-memory exception at 14:20:47 UTC. "
        "The crash was triggered by excessive memory allocation during concurrent user authentication requests. "
        "Thread pool exhaustion (67 active threads) contributed to the system instability. "
        "The service automatically restarted and recovered after 3.2 seconds."
    ),
    # AI root-cause analysis results, ordered by confidence score (descending).
    "root_causes": [
        {"title": "Memory Leak in Session Management", "confidence": "94%"},
        {"title": "Insufficient Thread Pool Configuration", "confidence": "87%"},
        {"title": "Concurrent Request Spike", "confidence": "76%"},
    ],
}

# Error-log entries shown in the Crash Details log viewer.
# Level hierarchy: ERROR > WARN > INFO > DEBUG
LOG_ENTRIES = [
    {"level": "ERROR", "time": "14:20:47", "msg": "OutOfMemoryException in module AuthService.dll"},
    {"level": "WARN",  "time": "14:20:45", "msg": "Memory threshold exceeded: 95%"},
    {"level": "ERROR", "time": "14:20:43", "msg": "Failed to allocate memory for user session"},
    {"level": "INFO",  "time": "14:20:40", "msg": "Attempting garbage collection"},
    {"level": "WARN",  "time": "14:20:38", "msg": "High memory pressure detected"},
    {"level": "ERROR", "time": "14:20:35", "msg": "Thread pool exhausted: 67 active threads"},
]

# Resource utilisation at the time of the crash — plotted as a multi-line chart.
RESOURCE_METRICS = [
    {"time": "14:15", "cpu": 45, "memory": 62, "threads": 24},
    {"time": "14:16", "cpu": 58, "memory": 68, "threads": 28},
    {"time": "14:17", "cpu": 72, "memory": 75, "threads": 32},
    {"time": "14:18", "cpu": 88, "memory": 85, "threads": 45},
    {"time": "14:19", "cpu": 95, "memory": 92, "threads": 58},
    {"time": "14:20", "cpu": 98, "memory": 95, "threads": 67},  # ← crash point
    {"time": "14:21", "cpu": 12, "memory": 35, "threads": 18},  # ← post-recovery
]


# ═══════════════════════════════════════════════════════════════
#  LOGS SCREEN DATA
# ═══════════════════════════════════════════════════════════════

# Paginated system log table data.
# Each entry includes an optional error-type classification for filtering.
FULL_LOGS = [
    {"id": "1",  "time": "2026-01-14 14:20:47", "level": "ERROR", "module": "AuthService",         "type": "Memory",      "msg": "OutOfMemoryException: Unable to allocate memory"},
    {"id": "2",  "time": "2026-01-14 14:20:45", "level": "WARN",  "module": "AuthService",         "type": "Memory",      "msg": "Memory threshold exceeded: 95%"},
    {"id": "3",  "time": "2026-01-14 14:20:43", "level": "ERROR", "module": "AuthService",         "type": "Memory",      "msg": "Failed to allocate memory for user session"},
    {"id": "4",  "time": "2026-01-14 14:18:32", "level": "ERROR", "module": "DatabaseService",     "type": "Network",     "msg": "Connection timeout after 30s"},
    {"id": "5",  "time": "2026-01-14 14:15:21", "level": "WARN",  "module": "APIGateway",          "type": "Performance", "msg": "High latency detected: 2.3s average"},
    {"id": "6",  "time": "2026-01-14 14:12:14", "level": "INFO",  "module": "CacheService",        "type": "",            "msg": "Cache miss rate: 23%"},
    {"id": "7",  "time": "2026-01-14 14:08:05", "level": "ERROR", "module": "PaymentService",      "type": "Transaction", "msg": "Transaction rollback due to timeout"},
    {"id": "8",  "time": "2026-01-14 14:05:47", "level": "DEBUG", "module": "LogService",          "type": "",            "msg": "Log rotation completed successfully"},
    {"id": "9",  "time": "2026-01-14 14:02:33", "level": "WARN",  "module": "UserService",         "type": "Session",     "msg": "Session expiry approaching for 45 users"},
    {"id": "10", "time": "2026-01-14 13:58:12", "level": "ERROR", "module": "NotificationService", "type": "Integration", "msg": "Failed to send push notification"},
]


# ═══════════════════════════════════════════════════════════════
#  SETTINGS SCREEN DATA
# ═══════════════════════════════════════════════════════════════

# Team members listed in Settings → User Management.
# Roles: Admin (full access), Analyst (read + respond), Viewer (read-only).
USERS = [
    {"name": "Alex Davidson",  "email": "alex.davidson@company.com",  "role": "Admin"},
    {"name": "Sarah Chen",     "email": "sarah.chen@company.com",     "role": "Analyst"},
    {"name": "Mike Johnson",   "email": "mike.johnson@company.com",   "role": "Viewer"},
]
