"""
CrashSense — Automated System Resolution
==========================================

Proactively mitigating system crashes before they occur.
Provides non-blocking, safe privilege-escalation mechanisms to intervene
in runaway processes or OOM situations.

Features:
    1. Dynamic Throttling (renice)
    2. Graceful Termination (SIGTERM)
    3. OOM Prevention (drop_caches)

Execution happens async so the main ML loop never blocks
waiting for OS permission prompts.
"""

import os
import time
import signal
import threading
import subprocess
import psutil

# ─────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────

# Cooldowns prevent spamming the same PID or system command
THROTTLE_COOLDOWN = 60    # seconds per PID
TERM_COOLDOWN = 120       # seconds per PID
CACHE_DROP_COOLDOWN = 300 # seconds for system-wide cache drop


class SystemResolver:
    """Daemon responsible for system interventions."""

    def __init__(self):
        self._last_throttled = {}  # PID -> timestamp
        self._last_terminated = {} # PID -> timestamp
        self._last_cache_drop = 0
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────
    #  Actions
    # ─────────────────────────────────────────────────────────────

    def throttle_process(self, pid: int, name: str):
        """
        Dynamically throttles a CPU-hogging process by setting its 'nice'
        value to 19 (lowest priority).
        """
        now = time.time()
        with self._lock:
            if now - self._last_throttled.get(pid, 0) < THROTTLE_COOLDOWN:
                return  # In cooldown
            self._last_throttled[pid] = now

        threading.Thread(
            target=self._exec_throttle,
            args=(pid, name),
            daemon=True
        ).start()

    def terminate_process(self, pid: int, name: str):
        """
        Gracefully terminates a process (e.g. runaway memory leak)
        by sending SIGTERM.
        """
        now = time.time()
        with self._lock:
            if now - self._last_terminated.get(pid, 0) < TERM_COOLDOWN:
                return  # In cooldown
            self._last_terminated[pid] = now

        threading.Thread(
            target=self._exec_terminate,
            args=(pid, name),
            daemon=True
        ).start()

    def clear_sys_cache(self):
        """
        Drops pagecache, dentries, and inodes to free up RAM.
        Requires root privileges.
        """
        now = time.time()
        with self._lock:
            if now - self._last_cache_drop < CACHE_DROP_COOLDOWN:
                return
            self._last_cache_drop = now

        threading.Thread(
            target=self._exec_cache_drop,
            daemon=True
        ).start()

    # ─────────────────────────────────────────────────────────────
    #  Executors (Run in Background Threads)
    # ─────────────────────────────────────────────────────────────

    def _exec_throttle(self, pid: int, name: str):
        try:
            proc = psutil.Process(pid)
            # Try normal user privilege first
            proc.nice(19)
            print(f"[Resolver] [+] Successfully throttled '{name}' (PID {pid}) to nice 19.")
            return
        except psutil.AccessDenied:
            # Fallback to passwordless sudo if needed
            print(f"[Resolver] Access denied throttling '{name}' (PID {pid}). Attempting sudo...")
            try:
                subprocess.run(
                    ["sudo", "-n", "renice", "19", "-p", str(pid)],
                    check=True, capture_output=True
                )
                print(f"[Resolver] [+] Sudo throttled '{name}' (PID {pid}).")
            except subprocess.CalledProcessError:
                print(f"[Resolver] [-] Failed to throttle '{name}' (PID {pid}) - Insufficient privileges.")
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            print(f"[Resolver] [-] Throttle error for '{name}': {e}")

    def _exec_terminate(self, pid: int, name: str):
        try:
            # Normal OS signal
            os.kill(pid, signal.SIGTERM)
            print(f"[Resolver] [+] Sent SIGTERM to '{name}' (PID {pid}).")
            return
        except PermissionError:
            print(f"[Resolver] Permission denied sending SIGTERM to '{name}' (PID {pid}). Attempting sudo...")
            try:
                subprocess.run(
                    ["sudo", "-n", "kill", "-15", str(pid)],
                    check=True, capture_output=True
                )
                print(f"[Resolver] [+] Sudo SIGTERM'd '{name}' (PID {pid}).")
            except subprocess.CalledProcessError:
                print(f"[Resolver] [-] Failed to kill '{name}' (PID {pid}) - Insufficient privileges.")
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"[Resolver] [-] Terminate error for '{name}': {e}")

    def _exec_cache_drop(self):
        try:
            # We must use sudo here. -n ensures it fails immediately without blocking for a password prompt
            print("[Resolver] Critical memory exhaustion detected. Attempting to drop sys caches...")
            result = subprocess.run(
                ["sudo", "-n", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
                check=True, capture_output=True, text=True
            )
            print("[Resolver] [+] Successfully cleared pagecache, dentries, and inodes.")
        except subprocess.CalledProcessError as e:
             if 'sudo: a password is required' in e.stderr:
                 print("[Resolver] [-] Cache drop failed: requires passwordless sudo configuration.")
             else:
                 print(f"[Resolver] [-] Cache drop failed: {e.stderr.strip()}")
        except Exception as e:
            print(f"[Resolver] [-] Cache drop error: {e}")

# Module-level singleton
system_resolver = SystemResolver()
