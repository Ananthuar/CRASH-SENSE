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
    #  FR-07: Permission-Gated Remediation Executor
    # ─────────────────────────────────────────────────────────────

    def execute_remediation(self, action_name: str,
                             permission_granted: bool,
                             pid: int = None,
                             process_name: str = None) -> dict:
        """
        FR-07: Execute a named remediation action only when permission_granted=True.

        If permission_granted is False, logs "User Denied" and returns immediately
        without executing any OS-level action.

        Args:
            action_name:        One of: 'clear_cache', 'restart_service',
                                'kill_process', 'throttle_process',
                                'rotate_logs', 'noop'
            permission_granted: Boolean user response from the UI prompt.
            pid:                Optional process ID for process-level actions.
            process_name:       Optional process name for logging.

        Returns:
            dict with keys: action, permission_granted, executed (bool), message
        """
        if not permission_granted:
            msg = f"[Resolver] User Denied remediation action '{action_name}'"
            print(msg)
            _post_action_validator.record_denial(action_name)
            return {
                "action": action_name,
                "permission_granted": False,
                "executed": False,
                "message": "User Denied",
            }

        # Permission granted — execute the action
        print(f"[Resolver] User Approved: executing '{action_name}' "
              f"(pid={pid}, name={process_name})")

        result_msg = "Action dispatched."
        try:
            if action_name == "clear_cache":
                self.clear_sys_cache()
                result_msg = "Cache drop initiated."
            elif action_name == "kill_process" and pid is not None:
                self.terminate_process(pid, process_name or str(pid))
                result_msg = f"SIGTERM sent to PID {pid}."
            elif action_name == "throttle_process" and pid is not None:
                self.throttle_process(pid, process_name or str(pid))
                result_msg = f"Throttled PID {pid} to nice 19."
            elif action_name == "restart_service":
                # Placeholder — real impl would call systemctl or supervisord
                print(f"[Resolver] Restart service action triggered.")
                result_msg = "Service restart requested."
            elif action_name == "rotate_logs":
                print("[Resolver] Log rotation action triggered.")
                result_msg = "Log rotation requested."
            else:
                result_msg = f"Action '{action_name}' acknowledged (no-op or unknown)."
        except Exception as e:
            result_msg = f"Action '{action_name}' failed: {e}"
            print(f"[Resolver] Error: {result_msg}")

        # Start post-action validation (FR-08)
        _post_action_validator.start_validation(action_name, pid)

        return {
            "action": action_name,
            "permission_granted": True,
            "executed": True,
            "message": result_msg,
        }

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


# ─────────────────────────────────────────────────────────────────
#  FR-08: Post-Action Health Validator
# ─────────────────────────────────────────────────────────────────

class PostActionValidator:
    """
    FR-08: Monitors system health after a remediation action and determines
    whether the application stabilized.

    Polls CPU usage every POLL_INTERVAL seconds for up to VALIDATION_WINDOW
    seconds. Reports stabilization if CPU stays below CPU_STABLE_THRESHOLD
    for the majority of the window.

    Constants:
        VALIDATION_WINDOW: 120 seconds (2 minutes)
        CPU_STABLE_THRESHOLD: 50%
        POLL_INTERVAL: 10 seconds
    """

    VALIDATION_WINDOW    = 120   # seconds
    CPU_STABLE_THRESHOLD = 50.0  # percent
    POLL_INTERVAL        = 10    # seconds

    def __init__(self):
        self._lock   = threading.Lock()
        self._status = {
            "active":       False,
            "action":       None,
            "pid":          None,
            "started_at":   None,
            "stabilized":   None,   # True / False / None (in-progress)
            "cpu_samples":  [],
            "result_msg":   "No validation run yet.",
            "denied_actions": [],
        }

    def record_denial(self, action_name: str):
        """Record a user-denied action for audit purposes."""
        with self._lock:
            self._status["denied_actions"].append({
                "action":    action_name,
                "timestamp": time.time(),
            })

    def start_validation(self, action_name: str, pid: int = None):
        """
        Begin a background validation poll after a remediation action.

        Args:
            action_name: The remediation action that was executed.
            pid:         Optional PID of the affected process.
        """
        with self._lock:
            self._status.update({
                "active":      True,
                "action":      action_name,
                "pid":         pid,
                "started_at":  time.time(),
                "stabilized":  None,
                "cpu_samples": [],
                "result_msg":  "Validation in progress...",
            })

        threading.Thread(
            target=self._poll_health,
            daemon=True
        ).start()

    def _poll_health(self):
        """Background thread: poll CPU until window expires or stabilization confirmed."""
        start = time.time()
        samples = []

        while time.time() - start < self.VALIDATION_WINDOW:
            try:
                cpu = psutil.cpu_percent(interval=1)
                samples.append(cpu)

                with self._lock:
                    self._status["cpu_samples"] = list(samples)

                    # Early exit if system is clearly stabilized (5+ samples all < threshold)
                    if len(samples) >= 5 and all(s < self.CPU_STABLE_THRESHOLD for s in samples[-5:]):
                        self._status["stabilized"] = True
                        self._status["active"]     = False
                        elapsed = round(time.time() - start, 1)
                        self._status["result_msg"] = (
                            f"✅ System stabilized after {elapsed}s. "
                            f"CPU stayed below {self.CPU_STABLE_THRESHOLD}%."
                        )
                        print(f"[PostValidator] {self._status['result_msg']}")
                        return

            except Exception:
                pass

            time.sleep(self.POLL_INTERVAL - 1)  # subtract interval=1 used above

        # Window expired — evaluate final samples
        with self._lock:
            if not samples:
                self._status["stabilized"] = None
                self._status["result_msg"] = "Validation complete (no CPU samples collected)."
            else:
                below = sum(1 for s in samples if s < self.CPU_STABLE_THRESHOLD)
                ratio = below / len(samples)
                self._status["stabilized"] = ratio >= 0.7
                avg_cpu = sum(samples) / len(samples)
                if self._status["stabilized"]:
                    self._status["result_msg"] = (
                        f"✅ System stabilized. Avg CPU={avg_cpu:.1f}% over "
                        f"{self.VALIDATION_WINDOW}s window."
                    )
                else:
                    self._status["result_msg"] = (
                        f"⚠️ System NOT fully stabilized. Avg CPU={avg_cpu:.1f}% "
                        f"({below}/{len(samples)} samples below {self.CPU_STABLE_THRESHOLD}%)."
                    )
            self._status["active"] = False
            print(f"[PostValidator] {self._status['result_msg']}")

    def get_status(self) -> dict:
        """
        Return current validation state.

        Returns:
            dict with keys: active, action, started_at, stabilized,
                            result_msg, cpu_samples, denied_actions
        """
        with self._lock:
            return dict(self._status)


# Module-level singletons
system_resolver       = SystemResolver()
_post_action_validator = PostActionValidator()


def get_post_action_validator() -> PostActionValidator:
    """Return the module-level PostActionValidator instance."""
    return _post_action_validator
