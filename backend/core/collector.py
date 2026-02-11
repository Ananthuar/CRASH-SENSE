import time
import threading
import psutil
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SystemMonitor:
    def __init__(self, history_size=120, poll_interval=0.5):
        """
        initializes the SystemMonitor.
        :param history_size: Number of data points to keep (120 * 0.5s = 60 seconds history)
        :param poll_interval: Time in seconds between polls
        """
        self.history_size = history_size
        self.poll_interval = poll_interval
        self.metrics_history = deque(maxlen=history_size)
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _poll_loop(self):
        while self.running:
            metrics = self._collect_metrics()
            with self.lock:
                self.metrics_history.append(metrics)
            time.sleep(self.poll_interval)

    def _collect_metrics(self):
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
        with self.lock:
            if self.metrics_history:
                return list(self.metrics_history)[-1]
            return None
    
    def get_history(self):
        with self.lock:
            return list(self.metrics_history)


class LogFileEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

class LogMonitor:
    def __init__(self, log_paths):
        self.log_paths = log_paths
        self.observer = Observer()
        self.handlers = []

    def start(self):
        # In a real scenario, we might want to watch specific directory and filter by filename
        # For simplicity, we assume log_paths are files, so we watch their parent directories
        
        # Note: watchdog watches directories.
        paths_to_watch = set()
        for log_file in self.log_paths:
            # ensure file exists or directory exists
            import os
            if os.path.exists(log_file):
                directory = os.path.dirname(os.path.abspath(log_file))
                paths_to_watch.add(directory)
        
        event_handler = LogFileEventHandler(self._on_log_change)
        
        for directory in paths_to_watch:
            self.observer.schedule(event_handler, directory, recursive=False)
            
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def _on_log_change(self, file_path):
        # Filter if the changed file is one of our targets
        if any(file_path.endswith(target) for target in self.log_paths):
             # For now, just print or store that a change happened.
             # In Commit 3, we will tokenize this.
             print(f"[LogMonitor] Change detected in {file_path}")

# Interface for global access
system_monitor = SystemMonitor()
