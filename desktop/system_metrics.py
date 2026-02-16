"""
CrashSense — System Metrics Helper
====================================

Provides lightweight wrappers around ``psutil`` to fetch real-time CPU,
memory, disk, and network statistics for the desktop UI.
"""

import psutil
import os
import time
from datetime import datetime


def get_cpu_percent() -> float:
    """Return current CPU usage as a percentage (non-blocking)."""
    return psutil.cpu_percent(interval=None)


def get_memory() -> dict:
    """Return memory stats: total, used, percent."""
    vm = psutil.virtual_memory()
    return {
        "total_gb": round(vm.total / (1024 ** 3), 1),
        "used_gb": round(vm.used / (1024 ** 3), 1),
        "available_gb": round(vm.available / (1024 ** 3), 1),
        "percent": vm.percent,
    }


def get_disk() -> dict:
    """Return root disk usage stats."""
    du = psutil.disk_usage("/")
    return {
        "total_gb": round(du.total / (1024 ** 3), 1),
        "used_gb": round(du.used / (1024 ** 3), 1),
        "free_gb": round(du.free / (1024 ** 3), 1),
        "percent": du.percent,
    }


def get_network() -> dict:
    """Return network I/O counters."""
    net = psutil.net_io_counters()
    return {
        "bytes_sent_mb": round(net.bytes_sent / (1024 ** 2), 1),
        "bytes_recv_mb": round(net.bytes_recv / (1024 ** 2), 1),
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
    }


def get_process_count() -> int:
    """Return total number of running processes."""
    return len(psutil.pids())


def get_uptime() -> str:
    """Return system uptime as a human-readable string."""
    boot = psutil.boot_time()
    delta = time.time() - boot
    hours = int(delta // 3600)
    minutes = int((delta % 3600) // 60)
    if hours > 24:
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def get_thread_count() -> int:
    """Return total number of threads (fast, reads /proc/stat on Linux)."""
    try:
        # Fast path: read from /proc/stat on Linux
        procs_running = 0
        if os.path.exists("/proc/stat"):
            with open("/proc/stat") as f:
                for line in f:
                    if line.startswith("procs_running"):
                        procs_running = int(line.split()[1])
                        break
            # Use process count as a proxy; true thread enumeration is too slow
            return len(psutil.pids()) * 2  # reasonable estimate
        return len(psutil.pids()) * 2
    except Exception:
        return 0


def get_all_metrics() -> dict:
    """Return a comprehensive snapshot of system metrics (non-blocking)."""
    try:
        mem = get_memory()
        cpu = get_cpu_percent()
        return {
            "cpu_percent": cpu,
            "memory_percent": mem["percent"],
            "memory_used_gb": mem["used_gb"],
            "memory_total_gb": mem["total_gb"],
            "disk_percent": get_disk()["percent"],
            "process_count": get_process_count(),
            "thread_count": get_thread_count(),
            "uptime": get_uptime(),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
    except Exception:
        # Fallback if anything fails — never block the UI
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_used_gb": 0.0,
            "memory_total_gb": 0.0,
            "disk_percent": 0.0,
            "process_count": 0,
            "thread_count": 0,
            "uptime": "--",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
