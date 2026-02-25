"""
CrashSense — Per-Process Crash Detection Monitor
==================================================

Background daemon that monitors every running process for crash precursors.
Instead of vague system-level guesses, this detects concrete, evidence-based
signals that a specific process is headed for trouble.

Six Detectors:
    1. Memory Leak     — RSS growing monotonically (>1 MB/min for 2+ min)
    2. CPU Runaway      — Sustained >90% CPU for 30+ seconds
    3. Thread Explosion — Thread count growing >50% in 1 minute
    4. FD Exhaustion    — Open FDs approaching ulimit (>80%)
    5. Zombie Process   — Process in zombie/defunct state
    6. OOM Risk         — Single process using >40% of total RAM

Architecture:
    ProcessMonitor (daemon thread)
        → scans all processes every SCAN_INTERVAL seconds
        → stores per-PID snapshots in ring buffers
        → runs detectors on each PID's history
        → pushes alerts to a capped deque

Public API:
    process_monitor.start()
    process_monitor.stop()
    process_monitor.get_alerts()        → list of active alert dicts
    process_monitor.get_top_processes() → top N processes by resource usage

Usage:
    from core.process_monitor import process_monitor
    process_monitor.start()
    alerts = process_monitor.get_alerts()
"""

import os
import time
import resource
import threading
from collections import deque
from datetime import datetime

import psutil
import numpy as np


# ─────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────

SCAN_INTERVAL = 3          # Seconds between process scans
HISTORY_SIZE = 60          # Snapshots per PID (~3 min at 3s intervals)
MAX_ALERTS = 100           # Maximum alerts in queue
TOP_N = 15                 # Number of top processes to return
CLEANUP_INTERVAL = 30      # Seconds between dead-PID cleanup passes

# Detector thresholds
MEM_LEAK_SLOPE_MB_MIN = 1.0     # MB/min growth to flag as leak
MEM_LEAK_MIN_SAMPLES = 40       # ~2 minutes of history needed
CPU_RUNAWAY_PERCENT = 90.0      # CPU% threshold
CPU_RUNAWAY_MIN_SAMPLES = 10    # ~30 seconds sustained
THREAD_GROWTH_PERCENT = 50.0    # % increase to flag
THREAD_MIN_INITIAL = 5          # Don't flag if started with < 5 threads
FD_EXHAUSTION_PERCENT = 80.0    # % of ulimit
OOM_RAM_PERCENT = 40.0          # Single process using > this % of RAM

# Processes to skip (system-critical, not user-actionable)
_SKIP_NAMES = frozenset({
    "systemd", "kthreadd", "ksoftirqd", "kworker", "rcu_sched",
    "rcu_preempt", "rcu_bh", "migration", "watchdog", "cpuhp",
    "netns", "kdevtmpfs", "bioset", "crypto", "kblockd",
    "ata_sff", "md", "edac-poller", "devfreq_wq", "kswapd",
    "ecryptfs", "kthrotld", "irq/", "scsi_", "dm_", "jbd2",
    "ext4", "xfs", "writeback", "kcompactd", "khugepaged",
})


# ─────────────────────────────────────────────────────────────────
#  Alert Severity
# ─────────────────────────────────────────────────────────────────

class Severity:
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ─────────────────────────────────────────────────────────────────
#  Detectors
# ─────────────────────────────────────────────────────────────────

def detect_memory_leak(pid: int, name: str, history: list[dict]) -> dict | None:
    """
    Detect monotonically growing RSS over time.

    Fits a linear regression on the RSS time series. If the slope exceeds
    MEM_LEAK_SLOPE_MB_MIN for at least MEM_LEAK_MIN_SAMPLES, it's a leak.
    """
    if len(history) < MEM_LEAK_MIN_SAMPLES:
        return None

    rss_mb = np.array([s["rss_mb"] for s in history[-MEM_LEAK_MIN_SAMPLES:]])
    timestamps = np.array([s["timestamp"] for s in history[-MEM_LEAK_MIN_SAMPLES:]])

    # Time in minutes
    t_min = (timestamps - timestamps[0]) / 60.0
    if t_min[-1] < 1.0:
        return None  # Need at least 1 minute of data

    # Linear regression: RSS = slope * t + intercept
    n = len(t_min)
    t_mean = np.mean(t_min)
    rss_mean = np.mean(rss_mb)
    numerator = np.sum((t_min - t_mean) * (rss_mb - rss_mean))
    denominator = np.sum((t_min - t_mean) ** 2)

    if denominator < 1e-10:
        return None

    slope = numerator / denominator  # MB per minute

    if slope < MEM_LEAK_SLOPE_MB_MIN:
        return None

    # Check it's genuinely monotonic-ish (not just two noisy values)
    # At least 70% of consecutive diffs should be positive
    diffs = np.diff(rss_mb)
    positive_ratio = np.sum(diffs > 0) / len(diffs)
    if positive_ratio < 0.65:
        return None

    total_growth = rss_mb[-1] - rss_mb[0]

    return {
        "type":     "memory_leak",
        "severity": Severity.HIGH if slope > 5 else Severity.MEDIUM,
        "pid":      pid,
        "name":     name,
        "title":    "Memory Leak Detected",
        "detail":   f"RSS growing at {slope:.1f} MB/min "
                    f"(+{total_growth:.0f} MB over {t_min[-1]:.1f} min)",
        "metric":   f"{rss_mb[-1]:.0f} MB",
        "slope":    round(slope, 2),
    }


def detect_cpu_runaway(pid: int, name: str, history: list[dict]) -> dict | None:
    """
    Detect sustained high CPU usage.

    Flags if the last CPU_RUNAWAY_MIN_SAMPLES are all above the threshold.
    """
    if len(history) < CPU_RUNAWAY_MIN_SAMPLES:
        return None

    recent_cpu = [s["cpu_percent"] for s in history[-CPU_RUNAWAY_MIN_SAMPLES:]]
    avg_cpu = np.mean(recent_cpu)

    if avg_cpu < CPU_RUNAWAY_PERCENT:
        return None

    # How long has it been sustained?
    duration = (history[-1]["timestamp"] - history[-CPU_RUNAWAY_MIN_SAMPLES]["timestamp"])

    return {
        "type":     "cpu_runaway",
        "severity": Severity.CRITICAL if avg_cpu > 98 else Severity.HIGH,
        "pid":      pid,
        "name":     name,
        "title":    "CPU Runaway Process",
        "detail":   f"Sustained {avg_cpu:.0f}% CPU for {duration:.0f}s",
        "metric":   f"{avg_cpu:.0f}%",
    }


def detect_thread_explosion(pid: int, name: str, history: list[dict]) -> dict | None:
    """
    Detect rapid thread count growth.

    Compares current thread count to the value 20 samples ago (~1 min).
    """
    if len(history) < 20:
        return None

    current_threads = history[-1].get("num_threads", 0)
    past_threads = history[-20].get("num_threads", 0)

    if past_threads < THREAD_MIN_INITIAL:
        return None

    if past_threads == 0:
        return None

    growth = ((current_threads - past_threads) / past_threads) * 100

    if growth < THREAD_GROWTH_PERCENT:
        return None

    return {
        "type":     "thread_explosion",
        "severity": Severity.HIGH if growth > 100 else Severity.MEDIUM,
        "pid":      pid,
        "name":     name,
        "title":    "Thread Explosion",
        "detail":   f"Threads grew {growth:.0f}% in ~1 min "
                    f"({past_threads} → {current_threads})",
        "metric":   f"{current_threads} threads",
    }


def detect_fd_exhaustion(pid: int, name: str, history: list[dict]) -> dict | None:
    """
    Detect open file descriptor count approaching the system limit.
    """
    latest = history[-1]
    num_fds = latest.get("num_fds", 0)
    fd_limit = latest.get("fd_limit", 0)

    if fd_limit <= 0 or num_fds <= 0:
        return None

    usage_pct = (num_fds / fd_limit) * 100

    if usage_pct < FD_EXHAUSTION_PERCENT:
        return None

    return {
        "type":     "fd_exhaustion",
        "severity": Severity.CRITICAL if usage_pct > 95 else Severity.HIGH,
        "pid":      pid,
        "name":     name,
        "title":    "File Descriptor Exhaustion",
        "detail":   f"Using {num_fds}/{fd_limit} FDs ({usage_pct:.0f}%)",
        "metric":   f"{num_fds}/{fd_limit}",
    }


def detect_zombie(pid: int, name: str, history: list[dict]) -> dict | None:
    """
    Detect zombie (defunct) processes — immediate alert.
    """
    latest = history[-1]
    if latest.get("status") != psutil.STATUS_ZOMBIE:
        return None

    return {
        "type":     "zombie",
        "severity": Severity.MEDIUM,
        "pid":      pid,
        "name":     name,
        "title":    "Zombie Process",
        "detail":   f"Process is defunct (zombie) — not properly reaped by parent",
        "metric":   "defunct",
    }


def detect_oom_risk(pid: int, name: str, history: list[dict]) -> dict | None:
    """
    Detect processes consuming a dangerous amount of total system RAM.
    """
    latest = history[-1]
    mem_pct = latest.get("memory_percent", 0)

    if mem_pct < OOM_RAM_PERCENT:
        return None

    rss_mb = latest.get("rss_mb", 0)

    return {
        "type":     "oom_risk",
        "severity": Severity.CRITICAL if mem_pct > 60 else Severity.HIGH,
        "pid":      pid,
        "name":     name,
        "title":    "OOM Kill Risk",
        "detail":   f"Using {mem_pct:.1f}% of total RAM ({rss_mb:.0f} MB) — "
                    f"OOM killer may target this process",
        "metric":   f"{mem_pct:.1f}% RAM",
    }


# All detectors in execution order
_DETECTORS = [
    detect_zombie,
    detect_oom_risk,
    detect_cpu_runaway,
    detect_memory_leak,
    detect_thread_explosion,
    detect_fd_exhaustion,
]


# ─────────────────────────────────────────────────────────────────
#  Process Monitor
# ─────────────────────────────────────────────────────────────────

class ProcessMonitor:
    """
    Background daemon that scans all processes and runs crash detectors.

    Stores per-PID history in ring buffers and maintains an alert queue.
    Thread-safe.
    """

    def __init__(self):
        self._process_history: dict[int, deque] = {}
        self._alerts: deque = deque(maxlen=MAX_ALERTS)
        self._active_alert_keys: set = set()  # (pid, alert_type) to avoid duplicates
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._last_cleanup = 0
        self._health_trend: deque = deque(maxlen=60)  # Health score history

    def start(self):
        """Start the background monitoring thread."""
        if self._running:
            return
        self._running = True
        # Prime psutil's CPU percent tracking
        try:
            psutil.cpu_percent(interval=None)
            for proc in psutil.process_iter():
                try:
                    proc.cpu_percent(interval=None)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_alerts(self) -> list[dict]:
        """Return a copy of all active alerts (newest first)."""
        with self._lock:
            return list(reversed(self._alerts))

    def get_top_processes(self) -> list[dict]:
        """Return top N processes by combined resource usage."""
        with self._lock:
            entries = []
            for pid, history in self._process_history.items():
                if not history:
                    continue
                latest = history[-1]
                # Score: weighted combination of CPU + memory + thread risk
                score = (
                    latest.get("cpu_percent", 0) * 0.4 +
                    latest.get("memory_percent", 0) * 0.4 +
                    min(latest.get("num_threads", 0) / 100, 1) * 20
                )
                entries.append({
                    "pid":            pid,
                    "name":           latest.get("name", "?"),
                    "cpu_percent":    round(latest.get("cpu_percent", 0), 1),
                    "memory_percent": round(latest.get("memory_percent", 0), 1),
                    "rss_mb":         round(latest.get("rss_mb", 0), 1),
                    "num_threads":    latest.get("num_threads", 0),
                    "status":         latest.get("status_str", "?"),
                    "score":          round(score, 1),
                })

            entries.sort(key=lambda e: e["score"], reverse=True)
            return entries[:TOP_N]

    def get_summary(self) -> dict:
        """Return a summary of monitoring state with overall health score."""
        with self._lock:
            alert_count = len(self._alerts)
            critical = sum(1 for a in self._alerts if a["severity"] == Severity.CRITICAL)
            high = sum(1 for a in self._alerts if a["severity"] == Severity.HIGH)
            medium = sum(1 for a in self._alerts if a["severity"] == Severity.MEDIUM)
            tracked = len(self._process_history)

        # Health score: 100 = perfect, deduct for each alert by severity
        score = 100
        score -= critical * 25
        score -= high * 15
        score -= medium * 5
        score = max(0, min(100, score))

        # Record in trend
        self._health_trend.append({
            "score": score,
            "alerts": alert_count,
            "timestamp": time.time(),
        })

        if score >= 80:
            status = "healthy"
        elif score >= 50:
            status = "warning" if high > 0 else "healthy"
        else:
            status = "critical"

        return {
            "total_alerts":      alert_count,
            "critical_alerts":   critical,
            "high_alerts":       high,
            "medium_alerts":     medium,
            "tracked_processes": tracked,
            "health_score":      score,
            "status":            status,
        }

    def get_health_trend(self) -> list[dict]:
        """Return recent health score history for trend charts."""
        with self._lock:
            return list(self._health_trend)

    # ─────────────────────────────────────────────────────────────
    #  Internal: Scan Loop
    # ─────────────────────────────────────────────────────────────

    def _scan_loop(self):
        """Main background loop — scans all processes and runs detectors."""
        while self._running:
            try:
                self._scan_all_processes()
            except Exception as e:
                # Never let the monitor die
                print(f"[ProcessMonitor] Scan error: {e}")

            # Periodic cleanup of dead PIDs
            now = time.time()
            if now - self._last_cleanup > CLEANUP_INTERVAL:
                self._cleanup_dead_pids()
                self._last_cleanup = now

            time.sleep(SCAN_INTERVAL)

    def _scan_all_processes(self):
        """Take a snapshot of all processes and run detectors."""
        now = time.time()
        alive_pids = set()

        attrs = [
            "pid", "name", "status", "cpu_percent", "memory_percent",
            "memory_info", "num_threads",
        ]

        # Track which alerts were actively re-detected in this scan
        active_alerts_this_scan = set()

        for proc in psutil.process_iter(attrs, ad_value=None):
            try:
                info = proc.info
                pid = info["pid"]
                name = info["name"] or "?"

                # Skip kernel threads and system-critical processes
                if self._should_skip(name, pid):
                    continue

                alive_pids.add(pid)

                # Build snapshot
                mem_info = info.get("memory_info")
                rss_bytes = mem_info.rss if mem_info else 0
                status = info.get("status", "")

                # Get FD count (may fail on some processes)
                try:
                    num_fds = proc.num_fds()
                except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                    num_fds = 0

                # Get FD limit
                try:
                    fd_limit_soft, _ = proc.rlimit(psutil.RLIMIT_NOFILE)
                except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                    fd_limit_soft = 1024  # Default assumption

                snapshot = {
                    "timestamp":      now,
                    "name":           name,
                    "status":         status,
                    "status_str":     str(status),
                    "cpu_percent":    info.get("cpu_percent", 0) or 0,
                    "memory_percent": info.get("memory_percent", 0) or 0,
                    "rss_mb":         rss_bytes / (1024 * 1024),
                    "num_threads":    info.get("num_threads", 0) or 0,
                    "num_fds":        num_fds,
                    "fd_limit":       fd_limit_soft,
                }

                # Store in history
                with self._lock:
                    if pid not in self._process_history:
                        self._process_history[pid] = deque(maxlen=HISTORY_SIZE)
                    self._process_history[pid].append(snapshot)
                    history = list(self._process_history[pid])

                # Run detectors
                for detector in _DETECTORS:
                    try:
                        alert = detector(pid, name, history)
                        if alert:
                            self._add_alert(alert)
                            active_alerts_this_scan.add((pid, alert["type"]))
                    except Exception:
                        pass  # Individual detector failure shouldn't stop others

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Prune alerts that were not re-detected (i.e., issue resolved itself)
        self._prune_resolved_alerts(alive_pids, active_alerts_this_scan)

    def _prune_resolved_alerts(self, alive_pids: set, active_alerts_this_scan: set):
        with self._lock:
            new_alerts = deque(maxlen=MAX_ALERTS)
            new_keys = set()
            
            for alert in self._alerts:
                pid = alert["pid"]
                key = (pid, alert["type"])
                
                # Keep if process died (will be cleaned up in _cleanup_dead_pids later)
                # Keep if issue was actively re-detected this scan
                # Also add a short grace period logic here if desired, but dropping immediately is correct for current status
                if pid not in alive_pids or key in active_alerts_this_scan:
                    new_alerts.append(alert)
                    new_keys.add(key)
            
            self._alerts = new_alerts
            self._active_alert_keys = new_keys

    def _should_skip(self, name: str, pid: int) -> bool:
        """Check if a process should be skipped (kernel thread, init, etc.)."""
        if pid <= 2:
            return True
        name_lower = name.lower()
        for skip in _SKIP_NAMES:
            if name_lower.startswith(skip):
                return True
        return False

    def _add_alert(self, alert: dict):
        """Add an alert, avoiding duplicates for the same (pid, type)."""
        key = (alert["pid"], alert["type"])
        alert["timestamp"] = time.time()
        alert["time_str"] = datetime.now().strftime("%H:%M:%S")

        with self._lock:
            if key in self._active_alert_keys:
                # Update existing alert (refresh timestamp and detail)
                for i, existing in enumerate(self._alerts):
                    if (existing["pid"], existing["type"]) == key:
                        self._alerts[i] = alert
                        return
            else:
                self._active_alert_keys.add(key)
                self._alerts.append(alert)

    def _cleanup_dead_pids(self):
        """Remove history and alerts for processes that no longer exist."""
        with self._lock:
            dead_pids = set()
            for pid in list(self._process_history.keys()):
                if not psutil.pid_exists(pid):
                    dead_pids.add(pid)
                    del self._process_history[pid]

            if dead_pids:
                # Remove alerts for dead PIDs
                self._alerts = deque(
                    (a for a in self._alerts if a["pid"] not in dead_pids),
                    maxlen=MAX_ALERTS,
                )
                self._active_alert_keys = {
                    k for k in self._active_alert_keys if k[0] not in dead_pids
                }


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════
process_monitor = ProcessMonitor()
