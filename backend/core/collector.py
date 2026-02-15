"""
CrashSense — System Metrics Collector
=======================================

Provides two monitoring components:

1. **SystemMonitor**
   A background thread that polls system metrics (CPU, memory, disk I/O,
   network I/O) at a configurable interval and stores them in a fixed-size
   circular buffer (deque). Thread-safe access is ensured via a threading lock.

   Default configuration:
       - poll_interval = 0.5 seconds
       - history_size = 120 entries  → 60 seconds of history

2. **LogMonitor** (stub)
   Uses the `watchdog` library to watch log files for changes. Currently
   prints a notification when a monitored file is modified; the tokenisation
   pipeline (LogTokenizer in preprocessor.py) will be wired in a future commit.

Module-Level Singleton:
    `system_monitor` — A pre-created SystemMonitor instance for global use.

Usage:
    from core.collector import system_monitor

    system_monitor.start()                     # Begin background polling
    current = system_monitor.get_latest_metrics()  # Most recent snapshot
    history = system_monitor.get_history()      # All buffered snapshots
    system_monitor.stop()                       # Cleanly terminate the thread
"""

import time
import threading
import psutil
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class SystemMonitor:
    """
    Background system metrics poller.

    Collects CPU percentage, memory usage, disk I/O counters, and network
    I/O counters at regular intervals. Stores the last `history_size`
    snapshots in a thread-safe circular buffer.

    Args:
        history_size:  Maximum number of metric snapshots to retain.
                       Older entries are automatically discarded (FIFO).
        poll_interval: Seconds between consecutive metric collections.

    Attributes:
        metrics_history (deque): Circular buffer of metric dicts.
        running (bool):          Whether the polling thread is active.
        thread (Thread | None):  Reference to the background polling thread.
        lock (Lock):             Threading lock protecting metrics_history.
    """

    def __init__(self, history_size=120, poll_interval=0.5):
        self.history_size = history_size
        self.poll_interval = poll_interval
        self.metrics_history = deque(maxlen=history_size)
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self):
        """
        Start the background polling thread.

        If already running, this method is a no-op (idempotent).
        The thread is marked as a daemon so it won't prevent process exit.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """
        Signal the polling thread to stop and wait for it to terminate.

        Safe to call even if the monitor was never started.
        """
        self.running = False
        if self.thread:
            self.thread.join()

    def _poll_loop(self):
        """
        Main polling loop — runs on the background thread.

        Continuously collects metrics and appends them to the history
        buffer until `self.running` is set to False.
        """
        while self.running:
            metrics = self._collect_metrics()
            with self.lock:
                self.metrics_history.append(metrics)
            time.sleep(self.poll_interval)

    def _collect_metrics(self):
        """
        Collect a single snapshot of system metrics via psutil.

        Returns:
            dict: A snapshot containing:
                - timestamp (float):         UNIX epoch seconds
                - cpu_percent (float):       CPU utilisation (0-100)
                - memory_percent (float):    RAM utilisation (0-100)
                - memory_used (int):         RAM used in bytes
                - disk_read_bytes (int):     Cumulative disk reads
                - disk_write_bytes (int):    Cumulative disk writes
                - net_bytes_sent (int):      Cumulative network bytes sent
                - net_bytes_recv (int):      Cumulative network bytes received
        """
        timestamp = time.time()
        cpu_percent = psutil.cpu_percent(interval=None)
        virtual_memory = psutil.virtual_memory()._asdict()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        return {
            'timestamp': timestamp,
            'cpu_percent': cpu_percent,
            'memory_percent': virtual_memory['percent'],
            'memory_used': virtual_memory['used'],
            'disk_read_bytes': disk_io.read_bytes if disk_io else 0,
            'disk_write_bytes': disk_io.write_bytes if disk_io else 0,
            'net_bytes_sent': net_io.bytes_sent if net_io else 0,
            'net_bytes_recv': net_io.bytes_recv if net_io else 0
        }

    def get_latest_metrics(self):
        """
        Return the most recently collected metric snapshot.

        Returns:
            dict | None: The latest metrics dict, or None if no data
                         has been collected yet.
        """
        with self.lock:
            if self.metrics_history:
                return list(self.metrics_history)[-1]
            return None

    def get_history(self):
        """
        Return a copy of the full metrics history buffer.

        Returns:
            list[dict]: List of metric snapshots, oldest first.
                        Length is at most `history_size`.
        """
        with self.lock:
            return list(self.metrics_history)


class LogFileEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler that triggers a callback on file modifications.

    Args:
        callback: Callable that receives the modified file path (str).
    """

    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        """Forward non-directory modification events to the callback."""
        if not event.is_directory:
            self.callback(event.src_path)


class LogMonitor:
    """
    File system watcher for log files.

    Uses the watchdog library to monitor directories containing the
    specified log files and trigger callbacks on modification.

    Args:
        log_paths: List of absolute paths to log files to watch.

    Note:
        Watchdog operates at the *directory* level, so we extract the
        parent directory of each log file and schedule one observer per
        unique directory.
    """

    def __init__(self, log_paths):
        self.log_paths = log_paths
        self.observer = Observer()
        self.handlers = []

    def start(self):
        """
        Begin watching the parent directories of all configured log paths.

        Only directories that actually exist on disk are watched.
        """
        # Deduplicate parent directories (watchdog watches directories, not files)
        paths_to_watch = set()
        for log_file in self.log_paths:
            import os
            if os.path.exists(log_file):
                directory = os.path.dirname(os.path.abspath(log_file))
                paths_to_watch.add(directory)

        event_handler = LogFileEventHandler(self._on_log_change)

        for directory in paths_to_watch:
            self.observer.schedule(event_handler, directory, recursive=False)

        self.observer.start()

    def stop(self):
        """Stop the watchdog observer and wait for its thread to terminate."""
        self.observer.stop()
        self.observer.join()

    def _on_log_change(self, file_path):
        """
        Internal callback triggered on any file modification in watched dirs.

        Filters events to only process files that match the configured log paths.

        Args:
            file_path: Absolute path to the modified file.
        """
        if any(file_path.endswith(target) for target in self.log_paths):
            # TODO: Wire into LogTokenizer for real-time log processing
            print(f"[LogMonitor] Change detected in {file_path}")


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL SINGLETON
#  Pre-created instance for global access across the application.
# ═══════════════════════════════════════════════════════════════
system_monitor = SystemMonitor()
