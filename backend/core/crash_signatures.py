"""
CrashSense — Crash Signatures Database
========================================

FR-05: Maintains a SQLite database mapping crash signature patterns to
        "Recommended Actions" for operator guidance.

Architecture:
    CrashSignatureDB
        ├── SQLite table: signatures (id, pattern, actions_json, category)
        └── query(text) → fuzzy keyword match → [{signature, actions, category}]

Pre-populated signatures cover common crash patterns:
    OOM Error            → Clear Temp Cache, Restart App
    DB Connection Timeout → Restart Service
    CPU Spike            → Kill Runaway Process, Renice Process
    ...

Module-Level Singleton:
    crash_sig_db — pre-created CrashSignatureDB instance.

Usage:
    from core.crash_signatures import crash_sig_db
    results = crash_sig_db.query("OOM Error")
    # → [{'signature': 'OOM Error', 'actions': ['Clear Temp Cache', ...]}]
"""

import os
import re
import json
import sqlite3
import threading


# ─────────────────────────────────────────────────────────────────
#  Default Signature Library
# ─────────────────────────────────────────────────────────────────

_DEFAULT_SIGNATURES = [
    # (pattern_string, [recommended actions], category)
    ("OOM Error",              ["Clear Temp Cache", "Restart App"],                      "memory"),
    ("Out of Memory",          ["Clear Temp Cache", "Restart App", "Kill Heaviest Process"], "memory"),
    ("Memory Leak",            ["Restart Service", "Clear Temp Cache"],                  "memory"),
    ("OOM Kill",               ["Clear Temp Cache", "Kill Heaviest Process"],             "memory"),
    ("DB Connection Timeout",  ["Restart Service", "Check DB Health"],                   "database"),
    ("Connection Refused",     ["Restart Service", "Check Network"],                     "network"),
    ("Deadlock",               ["Restart Service", "Kill Blocked Transactions"],          "database"),
    ("CPU Spike",              ["Kill Runaway Process", "Renice Process"],               "cpu"),
    ("CPU Runaway",            ["Renice Process", "Kill Runaway Process"],               "cpu"),
    ("High CPU",               ["Kill Runaway Process", "Renice Process"],               "cpu"),
    ("Thread Explosion",       ["Restart Service", "Reduce Thread Pool"],                "threads"),
    ("Thread Leak",            ["Restart Service"],                                      "threads"),
    ("File Descriptor Exhaustion", ["Restart Service", "Close Stale Connections"],       "fd"),
    ("FD Limit",               ["Restart Service", "Increase FD Limit"],                 "fd"),
    ("Disk Full",              ["Delete Temp Files", "Rotate Logs"],                     "disk"),
    ("I/O Bottleneck",         ["Throttle I/O", "Check Disk Health"],                   "disk"),
    ("Zombie Process",         ["Kill Parent Process", "Restart Service"],               "process"),
    ("Crash Loop",             ["Restart Service", "Check Logs"],                        "general"),
    ("Service Unavailable",    ["Restart Service", "Check Dependencies"],                "general"),
    ("Timeout",                ["Restart Service", "Increase Timeout Limit"],            "general"),
    ("Threshold Breach",       ["Restart Service", "Scale Resources"],                   "general"),
    ("High Memory",            ["Clear Temp Cache", "Restart App"],                      "memory"),
    ("Stack Overflow",         ["Restart App", "Increase Stack Size"],                   "general"),
    ("Segmentation Fault",     ["Restart App", "Collect Core Dump"],                     "general"),
    ("Permission Denied",      ["Fix File Permissions", "Check User Context"],           "security"),
]


class CrashSignatureDB:
    """
    SQLite-backed mapping of crash signature patterns to recommended actions.

    Patterns are stored as case-insensitive keywords. Querying searches for
    any signature whose pattern appears as a substring of the query text
    (or vice versa), returning all matching signatures ranked by relevance.

    Thread-safe via a per-instance lock.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            import sys
            if getattr(sys, 'frozen', False):
                # Running as a PyInstaller bundle: __file__ is inside read-only temp dir.
                # Use a persistent, writable system path instead.
                data_dir = "/var/lib/crashsense"
                os.makedirs(data_dir, exist_ok=True)
                db_path = os.path.join(data_dir, "crash_signatures.db")
            else:
                # Development: place DB alongside this source file
                db_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "crash_signatures.db",
                )
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    # ─────────────────────────────────────────────────────────────
    #  DB Initialisation
    # ─────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Open a new SQLite connection (thread-local use)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create schema and load default signatures if not already present."""
        with self._lock:
            conn = self._conn()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS signatures (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern      TEXT    NOT NULL UNIQUE,
                        actions_json TEXT    NOT NULL,
                        category     TEXT    DEFAULT 'general'
                    )
                """)
                conn.commit()

                # Seed defaults only if table is empty
                count = conn.execute("SELECT COUNT(*) FROM signatures").fetchone()[0]
                if count == 0:
                    conn.executemany(
                        "INSERT OR IGNORE INTO signatures (pattern, actions_json, category) VALUES (?, ?, ?)",
                        [
                            (pattern, json.dumps(actions), category)
                            for pattern, actions, category in _DEFAULT_SIGNATURES
                        ],
                    )
                    conn.commit()
            finally:
                conn.close()

    # ─────────────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────────────

    def query(self, text: str, max_results: int = 5) -> list[dict]:
        """
        Find signatures matching the given text (case-insensitive keyword search).

        The query text is checked against each stored pattern:
          - if the pattern keyword appears in the query text, OR
          - if the query text appears in the pattern

        Args:
            text:        Free-form query string (e.g. "OOM Error in process X").
            max_results: Maximum number of results to return.

        Returns:
            list[dict]: Matching signatures, each with:
                - signature (str): the matched pattern
                - actions   (list[str]): recommended remediation actions
                - category  (str): crash category
        """
        text_lower = text.lower()
        results = []

        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    "SELECT pattern, actions_json, category FROM signatures"
                ).fetchall()
            finally:
                conn.close()

        # Score each pattern against the query text
        scored = []
        for row in rows:
            pattern_lower = row["pattern"].lower()
            pattern_words = set(pattern_lower.split())
            text_words    = set(text_lower.split())

            word_overlap  = len(pattern_words & text_words)
            substr_match  = pattern_lower in text_lower or text_lower in pattern_lower

            score = word_overlap * 2 + (3 if substr_match else 0)
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)

        for _, row in scored[:max_results]:
            results.append({
                "signature": row["pattern"],
                "actions":   json.loads(row["actions_json"]),
                "category":  row["category"],
            })

        return results

    def get_all(self) -> list[dict]:
        """Return all stored signatures."""
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    "SELECT pattern, actions_json, category FROM signatures ORDER BY category, pattern"
                ).fetchall()
            finally:
                conn.close()

        return [
            {
                "signature": r["pattern"],
                "actions":   json.loads(r["actions_json"]),
                "category":  r["category"],
            }
            for r in rows
        ]

    def add_signature(self, pattern: str, actions: list[str], category: str = "general") -> bool:
        """
        Add or update a signature mapping.

        Args:
            pattern:  The crash signature keyword.
            actions:  List of recommended action strings.
            category: Crash category (memory, cpu, disk, etc.).

        Returns:
            bool: True if inserted/updated successfully.
        """
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """INSERT INTO signatures (pattern, actions_json, category)
                       VALUES (?, ?, ?)
                       ON CONFLICT(pattern) DO UPDATE SET actions_json=excluded.actions_json,
                                                          category=excluded.category""",
                    (pattern, json.dumps(actions), category),
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"[CrashSignatureDB] Error adding signature: {e}")
                return False
            finally:
                conn.close()


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════
crash_sig_db = CrashSignatureDB()
