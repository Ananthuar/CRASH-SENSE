"""
CrashSense — Hybrid AI Crash Predictor
========================================

Combines TWO models for robust crash prediction:

1. **Pre-Trained Random Forest** (supervised)
   Trained on synthetic crash patterns (CPU exhaustion, memory exhaustion,
   I/O storms, rapid spikes, gradual degradation, etc.). Uses normalized
   features (percentages) so it works on any hardware. Provides a strong
   baseline prediction even at startup.

2. **Isolation Forest** (unsupervised)
   Learns what "normal" looks like for THIS specific system from the live
   metrics buffer. Catches system-specific anomalies the pre-trained
   model might miss.

The final crash probability is a weighted ensemble of both models:
    P(crash) = WEIGHT_RF × RF_probability + WEIGHT_ANOMALY × IF_anomaly_score

Architecture:
    SystemMonitor (collector.py)
        ↓  raw metrics history (120 × 7 features)
    _compute_rf_features()    _compute_if_features()
        ↓                          ↓
    RandomForest.predict_proba()  IsolationForest.decision_function()
        ↓                          ↓
    rf_probability              if_anomaly_score
        ↓─────────────────────────↓
              weighted_ensemble
                    ↓
    predict() → { crash_probability, risk_level, factors, actions }

Module-Level Singleton:
    crash_predictor — Pre-created HybridCrashPredictor instance.

Usage:
    from core.crash_predictor import crash_predictor
    result = crash_predictor.predict()
"""

import os
import time
import json
import threading
import numpy as np
import psutil
from collections import deque
from sklearn.ensemble import IsolationForest
import joblib

try:
    import shap as _shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False
    print("[CrashPredictor] shap not installed — FR-04 SHAP attribution disabled.")

from core.collector import system_monitor
from core.preprocessor import data_scaler
from core.resolution import system_resolver


# ─────────────────────────────────────────────────────────────────
#  Configuration & Constants
# ─────────────────────────────────────────────────────────────────

# Ensemble weights (Configurable)
WEIGHT_RF = 0.7        # Pre-trained model weight
WEIGHT_ANOMALY = 0.3   # Anomaly detector weight

# Alert configuration
ALERT_COOLDOWN_SEC = 30  # Minimum seconds before escalating or re-alerting heavily

# Features for the pre-trained Random Forest (must match train_model.py)
_RF_FEATURE_NAMES = [
    "cpu_percent",
    "memory_percent",
    "disk_usage_percent",
    "cpu_std",
    "memory_std",
    "cpu_rate_of_change",
    "memory_rate_of_change",
    "cpu_memory_product",
    "io_read_intensity",
    "io_write_intensity",
    "net_send_intensity",
    "net_recv_intensity",
    "cpu_acceleration",
    "memory_acceleration",
    "window_divergence_cpu",
    "window_divergence_memory",
    "resource_ratio",
    "cpu_trend",
    "memory_trend"
]

# Raw metric keys from SystemMonitor
_METRIC_KEYS = [
    "cpu_percent", "memory_percent",
    "disk_read_bytes", "disk_write_bytes",
    "net_bytes_sent", "net_bytes_recv",
]


# ─────────────────────────────────────────────────────────────────
#  Real Crash Logger
# ─────────────────────────────────────────────────────────────────

class RealCrashLogger:
    """
    Handles asynchronous saving of real crash events to disk.
    Non-blocking to ensure the live prediction loop is never stalled.
    """
    def __init__(self, log_dir="backend/data/real_logs"):
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        # Prevent spamming: only allow one log write every 60 seconds
        self._last_log_time = 0 
        self._cooldown = 60

    def log_event_async(self, history, features, probability, label=1):
        """Spawns a background thread to format and save the log."""
        now = time.time()
        if now - self._last_log_time < self._cooldown:
            return  # Still in cooldown

        self._last_log_time = now
        
        # Snapshot the data before passing to thread
        history_snapshot = list(history)
        if hasattr(features, "tolist"):
            features_snapshot = features.tolist()[0]
        else:
            features_snapshot = features
        
        thread = threading.Thread(
            target=self._write_log,
            args=(history_snapshot, features_snapshot, probability, label, now),
            daemon=True
        )
        thread.start()

    def _write_log(self, history, features, probability, label, timestamp):
        try:
            filename = f"crash_log_{int(timestamp)}.json"
            filepath = os.path.join(self.log_dir, filename)
            
            payload = {
                "timestamp": timestamp,
                "label": label,
                "probability": probability,
                "engineered_features": dict(zip(_RF_FEATURE_NAMES, features)),
                "raw_metrics_buffer": history  # The 60-120s rolling buffer
            }
            
            with open(filepath, "w") as f:
                json.dump(payload, f, indent=2)
            print(f"[CrashLogger] Flushed real crash log to {filename}")
        except Exception as e:
            print(f"[CrashLogger] Error writing log: {e}")

_crash_logger = RealCrashLogger()


# ─────────────────────────────────────────────────────────────────
#  Risk factor descriptions
# ─────────────────────────────────────────────────────────────────

_FACTOR_LABELS = {
    "cpu_percent":      "High CPU usage",
    "memory_percent":   "Elevated memory consumption",
    "disk_read_bytes":  "Heavy disk read activity",
    "disk_write_bytes": "Heavy disk write activity",
    "net_bytes_sent":   "High outbound network traffic",
    "net_bytes_recv":   "High inbound network traffic",
    "cpu_memory":       "CPU × Memory pressure",
    "io_pressure":      "Combined I/O pressure",
    "cpu_roc":          "Rapid CPU usage changes",
    "memory_roc":       "Rapid memory usage changes",
}

_SUGGESTED_ACTIONS = {
    "cpu_percent": {
        "title":    "Reduce CPU Load",
        "desc":     "Identify and terminate CPU-intensive processes, or scale up CPU resources.",
        "priority": "High",
    },
    "memory_percent": {
        "title":    "Free Memory",
        "desc":     "Close memory-heavy applications or restart services with memory leaks.",
        "priority": "High",
    },
    "disk_read_bytes": {
        "title":    "Reduce Disk Reads",
        "desc":     "Check for excessive logging, large file scans, or runaway database queries.",
        "priority": "Medium",
    },
    "disk_write_bytes": {
        "title":    "Reduce Disk Writes",
        "desc":     "Check for log rotation storms, temp file creation, or database write bursts.",
        "priority": "Medium",
    },
    "net_bytes_sent": {
        "title":    "Check Network Output",
        "desc":     "Investigate high outbound traffic — possible data sync storm or exfiltration.",
        "priority": "Medium",
    },
    "net_bytes_recv": {
        "title":    "Check Network Input",
        "desc":     "Investigate high inbound traffic — possible attack or overloaded API.",
        "priority": "Medium",
    },
    "cpu_memory": {
        "title":    "System Under Pressure",
        "desc":     "Both CPU and memory are stressed. Consider restarting non-critical services.",
        "priority": "Critical",
    },
    "io_pressure": {
        "title":    "I/O Bottleneck Detected",
        "desc":     "Disk and network I/O are both elevated. Check for cascading failures.",
        "priority": "High",
    },
    "cpu_roc": {
        "title":    "CPU Spike Detected",
        "desc":     "CPU usage is changing rapidly — possible runaway process or fork bomb.",
        "priority": "High",
    },
    "memory_roc": {
        "title":    "Memory Spike Detected",
        "desc":     "Memory usage is changing rapidly — possible memory leak escalation.",
        "priority": "High",
    },
}


class HybridCrashPredictor:
    """
    Ensemble crash predictor combining a pre-trained Random Forest
    (general crash knowledge) with an Isolation Forest (system-specific
    anomaly detection).

    Args:
        window_size:    Number of raw metric points per IF feature window.
        refit_interval: Minimum seconds between IF model refits.
        contamination:  IF expected anomaly proportion.
    """

    def __init__(self, window_size=20, refit_interval=10,
                 contamination=0.1):
        self.window_size = window_size
        self.refit_interval = refit_interval

        # ── Pre-trained Random Forest ────────────────────────────
        self._rf_model = None
        self._rf_loaded = False
        self._load_pretrained_model()

        # ── Isolation Forest (live anomaly detector) ─────────────
        self._if_model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
            n_jobs=1,
        )
        self._if_fitted = False
        self._if_last_fit = 0

        # ── Prediction history & Alerting ────────────────────────
        self._prediction_history = deque(maxlen=60)
        self._last_probability = 0.0
        self._last_alert_time = 0
        self._last_risk_level = "Low"

        # ── SHAP explainer (FR-04) ───────────────────────────────
        self._shap_explainer = None
        self._last_shap_values: dict = {}  # feature → shap_value

    def _load_pretrained_model(self):
        """Load the pre-trained Random Forest from disk."""
        import sys
        import warnings
        
        try:
            # When frozen via PyInstaller, assets are shipped to a temp directory
            base_path = sys._MEIPASS
            model_path = os.path.join(base_path, "backend", "models", "crash_rf_model.joblib")
        except AttributeError:
            # Standard execution from source code
            base_path = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_path, "..", "models", "crash_rf_model.joblib")
            
        model_path = os.path.normpath(model_path)

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
                bundle = joblib.load(model_path)
            self._rf_model = bundle["model"]
            
            # Check if model has exactly the right number of features
            if hasattr(self._rf_model, "n_features_in_") and self._rf_model.n_features_in_ != len(_RF_FEATURE_NAMES):
                 print(f"[CrashPredictor] Warning: Model expects {self._rf_model.n_features_in_} features, but we provide {len(_RF_FEATURE_NAMES)}.")
                 print("                 You must run 'python backend/train_model.py' first.")
            else:
                 self._rf_loaded = True
                 print(f"[CrashPredictor] Loaded pre-trained model "
                       f"(accuracy={bundle.get('accuracy', '?'):.4f}, "
                       f"v{bundle.get('version', '?')})")
        except FileNotFoundError:
            print(f"[CrashPredictor] Warning: No pre-trained model at {model_path}")
            print("                 Run 'python train_model.py' to train one.")
        except Exception as e:
            print(f"[CrashPredictor] Error loading model: {e}")

    # ─────────────────────────────────────────────────────────────
    #  Feature Engineering — Pre-trained RF
    # ─────────────────────────────────────────────────────────────

    def _compute_rf_features(self, history: list[dict]) -> np.ndarray:
        """
        Compute the features expected by the pre-trained Random Forest.
        Includes base features and newly added advanced features.
        """
        if len(history) < 10:
            return None

        recent = history[-min(self.window_size, len(history)):]
        long_term = history[-min(self.window_size * 3, len(history)):]

        # Current values (last snapshot)
        latest = recent[-1]
        cpu_pct = latest.get("cpu_percent", 0)
        mem_pct = latest.get("memory_percent", 0)

        # Disk usage as percentage
        try:
            disk = psutil.disk_usage("/")
            disk_pct = disk.percent
        except Exception:
            disk_pct = 0

        # Extract arrays
        cpu_vals_recent = [m.get("cpu_percent", 0) for m in recent]
        mem_vals_recent = [m.get("memory_percent", 0) for m in recent]
        cpu_vals_long = [m.get("cpu_percent", 0) for m in long_term]
        mem_vals_long = [m.get("memory_percent", 0) for m in long_term]

        # 1. Volatility (std of recent window)
        cpu_std = float(np.std(cpu_vals_recent))
        mem_std = float(np.std(mem_vals_recent))

        # 2. Rate of change (second half mean - first half mean)
        n = len(recent)
        half = n // 2
        q1 = recent[:half//2]
        q2 = recent[half//2:half]
        q3 = recent[half:half + half//2]
        q4 = recent[half + half//2:]
        
        # Means of halves for RoC
        cpu_h1 = np.mean(cpu_vals_recent[:half])
        cpu_h2 = np.mean(cpu_vals_recent[half:])
        mem_h1 = np.mean(mem_vals_recent[:half])
        mem_h2 = np.mean(mem_vals_recent[half:])
        
        cpu_roc = cpu_h2 - cpu_h1
        mem_roc = mem_h2 - mem_h1

        # 3. CPU × Memory interaction
        cpu_mem_prod = (cpu_pct * mem_pct) / 10000.0

        # 4. I/O intensity (normalized using log scale then capped at 1)
        disk_read = latest.get("disk_read_bytes", 0)
        disk_write = latest.get("disk_write_bytes", 0)
        net_sent = latest.get("net_bytes_sent", 0)
        net_recv = latest.get("net_bytes_recv", 0)

        io_read_int = min(np.log1p(disk_read) / 30.0, 1.0)
        io_write_int = min(np.log1p(disk_write) / 30.0, 1.0)
        net_send_int = min(np.log1p(net_sent) / 28.0, 1.0)
        net_recv_int = min(np.log1p(net_recv) / 28.0, 1.0)

        # ─────────────────────────────────────────────────────────────
        # NEW ENHANCED FEATURES
        # ─────────────────────────────────────────────────────────────
        
        # 5. Second Derivative (Acceleration)
        # roc_recent - roc_older
        if len(q1) > 0 and len(q4) > 0:
            cpu_roc_older = np.mean([m.get("cpu_percent", 0) for m in q2]) - np.mean([m.get("cpu_percent", 0) for m in q1])
            cpu_roc_newer = np.mean([m.get("cpu_percent", 0) for m in q4]) - np.mean([m.get("cpu_percent", 0) for m in q3])
            cpu_accel = cpu_roc_newer - cpu_roc_older
            
            mem_roc_older = np.mean([m.get("memory_percent", 0) for m in q2]) - np.mean([m.get("memory_percent", 0) for m in q1])
            mem_roc_newer = np.mean([m.get("memory_percent", 0) for m in q4]) - np.mean([m.get("memory_percent", 0) for m in q3])
            mem_accel = mem_roc_newer - mem_roc_older
        else:
            cpu_accel, mem_accel = 0.0, 0.0

        # 6. Window Divergence (Sudden Spike vs long term baseline)
        win_div_cpu = np.mean(cpu_vals_recent[-5:]) - np.mean(cpu_vals_long) if len(cpu_vals_recent) >= 5 else 0
        win_div_mem = np.mean(mem_vals_recent[-5:]) - np.mean(mem_vals_long) if len(mem_vals_recent) >= 5 else 0

        # 7. Resource Ratio
        res_ratio = cpu_pct / (mem_pct + 1e-8)

        # 8. Trend Analysis (Linear Regression Slope on Recent Window)
        # Slope = (y[-1] - y[0]) / n for lightweight linear trend proxy
        cpu_trend = (cpu_vals_recent[-1] - cpu_vals_recent[0]) / n
        mem_trend = (mem_vals_recent[-1] - mem_vals_recent[0]) / n

        features = np.array([[
            cpu_pct,
            mem_pct,
            disk_pct,
            cpu_std,
            mem_std,
            cpu_roc,
            mem_roc,
            cpu_mem_prod,
            io_read_int,
            io_write_int,
            net_send_int,
            net_recv_int,
            cpu_accel,
            mem_accel,
            win_div_cpu,
            win_div_mem,
            res_ratio,
            cpu_trend,
            mem_trend
        ]])

        return features

    # ─────────────────────────────────────────────────────────────
    #  Feature Engineering — Isolation Forest
    # ─────────────────────────────────────────────────────────────

    def _compute_if_features(self, history: list[dict]) -> np.ndarray:
        """
        Compute feature matrix for Isolation Forest from normalized metrics.
        Each window of `window_size` points → one feature row with stats.
        """
        if len(history) < self.window_size:
            return np.array([])

        normalized = [data_scaler.normalize_metrics(m) for m in history]
        arrays = {}
        for key in _METRIC_KEYS:
            arrays[key] = np.array([m.get(key, 0.0) for m in normalized])

        n_windows = len(history) - self.window_size + 1
        features_list = []

        for i in range(n_windows):
            row = []
            for key in _METRIC_KEYS:
                window = arrays[key][i:i + self.window_size]
                row.extend([np.mean(window), np.std(window),
                            np.max(window), np.min(window)])
            features_list.append(row)

        return np.array(features_list)

    # ─────────────────────────────────────────────────────────────
    #  Scoring Helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _if_score_to_prob(score: float) -> float:
        """Convert IF anomaly score to crash probability (0-1)."""
        raw = -score
        scale = 5.0
        prob = 1.0 / (1.0 + np.exp(-scale * raw))
        return float(np.clip(prob, 0.0, 1.0))

    def _get_risk_level(self, probability: float, now: float) -> str:
        """
        Get risk level with cooldown logic to prevent alert spamming.
        """
        # Raw tier calculation
        if probability < 0.40:
            target_level = "Low"
            target_severity = 0
        elif probability < 0.75:
            target_level = "Elevated"
            target_severity = 1
        else:
            target_level = "Critical"
            target_severity = 2

        # Severity mappings
        severities = {"Low": 0, "Elevated": 1, "Critical": 2}
        current_severity = severities.get(self._last_risk_level, 0)
        
        # If it's escalating or critical, don't delay it.
        # But if it's fluctuating back down, apply a cooldown.
        if target_severity >= current_severity or target_severity == 2:
            self._last_risk_level = target_level
            self._last_alert_time = now
            return target_level
            
        # At this point, target severity is strictly lower than current.
        if now - self._last_alert_time < ALERT_COOLDOWN_SEC:
             # Maintain the higher active alert level
             return self._last_risk_level
             
        # Cooldown expired, drop down to the target level
        self._last_risk_level = target_level
        self._last_alert_time = now
        return target_level

    # ─────────────────────────────────────────────────────────────
    #  Risk Factor Analysis
    # ─────────────────────────────────────────────────────────────

    def _analyze_risk_factors(self, history: list[dict]) -> list[dict]:
        """
        Identify which metrics contribute most to crash risk by comparing
        recent values to the full-history baseline using z-scores.
        """
        if len(history) < 4:
            return []

        normalized = [data_scaler.normalize_metrics(m) for m in history]
        recent = normalized[-min(self.window_size, len(normalized)):]
        factors = []

        for key in _METRIC_KEYS:
            baseline_vals = [m.get(key, 0) for m in normalized]
            recent_vals = [m.get(key, 0) for m in recent]
            baseline_mean = np.mean(baseline_vals)
            baseline_std = np.std(baseline_vals) + 1e-8
            recent_mean = np.mean(recent_vals)
            z = (recent_mean - baseline_mean) / baseline_std

            if z > 1.0:
                factors.append({
                    "key":      key,
                    "label":    _FACTOR_LABELS.get(key, key),
                    "severity": round(min(z / 3.0, 1.0), 2),
                    "z_score":  round(z, 2),
                })

        # Cross-metric checks
        cpu_recent = np.mean([m.get("cpu_percent", 0) for m in recent])
        mem_recent = np.mean([m.get("memory_percent", 0) for m in recent])

        if cpu_recent > 0.6 and mem_recent > 0.6:
            factors.append({
                "key":      "cpu_memory",
                "label":    _FACTOR_LABELS["cpu_memory"],
                "severity": round(min((cpu_recent + mem_recent) / 2, 1.0), 2),
                "z_score":  0,
            })

        # Rate of change
        if len(recent) >= 4:
            half = len(recent) // 2
            cpu_v = [m.get("cpu_percent", 0) for m in recent]
            mem_v = [m.get("memory_percent", 0) for m in recent]
            cpu_roc = abs(np.mean(cpu_v[half:]) - np.mean(cpu_v[:half]))
            mem_roc = abs(np.mean(mem_v[half:]) - np.mean(mem_v[:half]))

            if cpu_roc > 0.15:
                factors.append({
                    "key": "cpu_roc", "label": _FACTOR_LABELS["cpu_roc"],
                    "severity": round(min(cpu_roc, 1.0), 2), "z_score": 0,
                })
            if mem_roc > 0.15:
                factors.append({
                    "key": "memory_roc", "label": _FACTOR_LABELS["memory_roc"],
                    "severity": round(min(mem_roc, 1.0), 2), "z_score": 0,
                })

        factors.sort(key=lambda f: f["severity"], reverse=True)
        return factors[:5]

    def _get_suggested_actions(self, risk_factors: list[dict]) -> list[dict]:
        """Generate action recommendations from risk factors."""
        actions = []
        seen = set()
        for f in risk_factors:
            key = f["key"]
            if key in _SUGGESTED_ACTIONS and key not in seen:
                action = _SUGGESTED_ACTIONS[key].copy()
                action["severity"] = f["severity"]
                actions.append(action)
                seen.add(key)

        if not actions:
            actions.append({
                "title":    "System Healthy",
                "desc":     "All metrics within normal parameters. No action needed.",
                "priority": "Info",
                "severity": 0.0,
            })
        return actions[:4]

    # ─────────────────────────────────────────────────────────────
    #  Main Prediction API
    # ─────────────────────────────────────────────────────────────

    def predict(self) -> dict:
        """
        Run hybrid crash prediction.

        Returns dict with: crash_probability, crash_percent, risk_level,
        top_risk_factors, suggested_actions, model_info, timestamp.
        """
        now = time.time()

        # ── ML globally disabled by user in Settings ─────────────
        if not getattr(self, "_ml_enabled", True):
            return {
                "crash_probability": 0.0,
                "crash_percent":     0,
                "risk_level":        "Disabled",
                "top_risk_factors":  [],
                "suggested_actions": [{
                    "title":    "ML Prediction Disabled",
                    "desc":     "Re-enable ML Prediction in Settings to activate crash forecasting.",
                    "priority": "Info",
                    "severity": 0.0,
                }],
                "model_info": {"rf_loaded": self._rf_loaded, "if_fitted": self._if_fitted,
                               "ml_enabled": False},
                "timestamp":   now,
                "data_points": 0,
            }

        history = system_monitor.get_history()

        if len(history) < 10:
            return {
                "crash_probability": 0.0,
                "crash_percent":     0,
                "risk_level":        "Low",
                "top_risk_factors":  [],
                "suggested_actions": [{
                    "title": "Collecting Data",
                    "desc":  f"Need {10 - len(history)} more data points...",
                    "priority": "Info", "severity": 0.0,
                }],
                "model_info": {"rf_loaded": self._rf_loaded, "if_fitted": self._if_fitted},
                "timestamp":   now,
                "data_points": len(history),
            }

        # ── Random Forest prediction ─────────────────────────────
        rf_prob = 0.0
        rf_features = None
        if self._rf_loaded:
            rf_features = self._compute_rf_features(history)
            if rf_features is not None:
                try:
                    # predict_proba returns [[P(healthy), P(crash)]]
                    proba = self._rf_model.predict_proba(rf_features)
                    rf_prob = float(proba[0][1])  # P(crash)
                except Exception:
                    rf_prob = 0.0

                # ── FR-04: SHAP feature attribution ─────────────────
                try:
                    self._compute_shap_values(rf_features)
                except Exception:
                    pass

        # ── Isolation Forest anomaly score ────────────────────────
        if_prob = 0.0
        if len(history) >= self.window_size + 5:
            if_features = self._compute_if_features(history)
            if if_features.size > 0 and len(if_features) >= 3:
                # Re-fit periodically
                if not self._if_fitted or (now - self._if_last_fit) > self.refit_interval:
                    try:
                        self._if_model.fit(if_features)
                        self._if_fitted = True
                        self._if_last_fit = now
                    except Exception:
                        pass

                if self._if_fitted:
                    try:
                        score = self._if_model.decision_function(if_features[-1:])[0]
                        if_prob = self._if_score_to_prob(score)
                    except Exception:
                        pass

        # ── Ensemble ─────────────────────────────────────────────
        if self._rf_loaded and self._if_fitted:
            probability = WEIGHT_RF * rf_prob + WEIGHT_ANOMALY * if_prob
        elif self._rf_loaded:
            probability = rf_prob  # Only RF available
        elif self._if_fitted:
            probability = if_prob  # Only IF available
        else:
            probability = 0.0

        probability = float(np.clip(probability, 0.0, 1.0))
        self._last_probability = probability
        
        # ── Real Crash Logging Trigger ───────────────────────────
        if probability >= 0.85 and rf_features is not None:
             _crash_logger.log_event_async(history, rf_features, probability, label=1)

        # Store in history (include timestamp for FR-03 extrapolation)
        self._prediction_history.append({
            "probability": probability,
            "rf_prob":     rf_prob,
            "if_prob":     if_prob,
            "timestamp":   now,
        })

        # Analyze risk factors & actions & risk level (with cooldown)
        risk_level = self._get_risk_level(probability, now)
        risk_factors = self._analyze_risk_factors(history)
        actions = self._get_suggested_actions(risk_factors)

        # Proactive Resolution Execution
        if risk_level == "Critical":
            # Identify if it's an OOM-level System emergency (vs just CPU which renice handles)
            needs_cache_drop = any(
                f["key"] in ("memory_percent", "cpu_memory", "memory_roc") 
                for f in risk_factors
            )
            if needs_cache_drop:
                system_resolver.clear_sys_cache()

        # FR-04: top SHAP feature name
        shap_top = max(self._last_shap_values, key=lambda k: abs(self._last_shap_values[k]), default=None) \
                   if self._last_shap_values else None

        return {
            "crash_probability": round(probability, 4),
            "crash_percent":     int(probability * 100),
            "risk_level":        risk_level,
            "top_risk_factors":  risk_factors,
            "suggested_actions": actions,
            "shap_top_feature":  shap_top,
            "shap_values":       self._last_shap_values,
            "model_info": {
                "rf_loaded":     self._rf_loaded,
                "rf_probability": round(rf_prob, 4),
                "if_fitted":     self._if_fitted,
                "if_probability": round(if_prob, 4),
                "ensemble":      f"{WEIGHT_RF:.0%} RF + {WEIGHT_ANOMALY:.0%} IF",
                "shap_available": _SHAP_AVAILABLE,
            },
            "timestamp":   now,
            "data_points": len(history),
        }

    def get_trend(self) -> list[dict]:
        """Return recent prediction history for trend charts."""
        return list(self._prediction_history)

    # ─────────────────────────────────────────────────────────────
    #  FR-03: 30-second ahead crash prediction
    # ─────────────────────────────────────────────────────────────

    def predict_ahead(self, seconds: float = 30.0) -> dict:
        """
        FR-03: Predict whether a crash will occur within the next `seconds`.

        Uses linear regression over the recent probability history to extrapolate
        the trend. If the projected probability crosses 0.85 within `seconds`,
        a pre-crash alert is generated.

        Args:
            seconds: Look-ahead window in seconds (default 30).

        Returns:
            dict with keys:
                - alert (bool): True if crash predicted within the horizon
                - projected_probability (float): extrapolated probability
                - seconds_until_critical (float | None): est. time-to-critical
                - confidence (str): 'high' / 'medium' / 'low'
                - message (str): human-readable summary
        """
        history = list(self._prediction_history)
        CRASH_THRESHOLD = 0.85
        MIN_SAMPLES = 5

        if len(history) < MIN_SAMPLES:
            return {
                "alert": False,
                "projected_probability": self._last_probability,
                "seconds_until_critical": None,
                "confidence": "low",
                "message": "Insufficient history for ahead prediction.",
            }

        # Extract time series
        t0 = history[0]["timestamp"]
        ts = np.array([(h["timestamp"] - t0) for h in history])
        ys = np.array([h["probability"] for h in history])

        # Linear regression: y = slope * t + intercept
        n = len(ts)
        t_mean = np.mean(ts)
        y_mean = np.mean(ys)
        denom = np.sum((ts - t_mean) ** 2)
        slope = float(np.sum((ts - t_mean) * (ys - y_mean)) / denom) if denom > 1e-10 else 0.0
        intercept = y_mean - slope * t_mean

        # Project probability at now + seconds
        t_now = history[-1]["timestamp"] - t0
        t_future = t_now + seconds
        projected_prob = float(np.clip(slope * t_future + intercept, 0.0, 1.0))

        # Estimate time until probability crosses threshold
        seconds_until_critical = None
        alert = False
        if slope > 0 and projected_prob >= CRASH_THRESHOLD:
            alert = True
            current_prob = float(np.clip(slope * t_now + intercept, 0.0, 1.0))
            if current_prob < CRASH_THRESHOLD:
                seconds_until_critical = max(0.0, (CRASH_THRESHOLD - current_prob) / slope)
            else:
                seconds_until_critical = 0.0  # Already critical

        # Confidence based on how monotonic the trend is
        diffs = np.diff(ys)
        positive_ratio = float(np.sum(diffs > 0) / len(diffs)) if len(diffs) > 0 else 0.5
        if positive_ratio > 0.7 and abs(slope) > 0.005:
            confidence = "high"
        elif positive_ratio > 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        if alert:
            secs_str = f"{seconds_until_critical:.0f}s" if seconds_until_critical else "now"
            message = (f"⚠️ Crash predicted in ~{secs_str} — "
                       f"probability trending to {projected_prob:.0%}")
        elif projected_prob > 0.5:
            message = f"System showing elevated risk trend ({projected_prob:.0%} in {seconds:.0f}s)"
        else:
            message = f"Stable. Projected probability in {seconds:.0f}s: {projected_prob:.0%}"

        return {
            "alert": alert,
            "projected_probability": round(projected_prob, 4),
            "seconds_until_critical": round(seconds_until_critical, 1) if seconds_until_critical is not None else None,
            "confidence": confidence,
            "slope": round(slope, 6),
            "message": message,
        }

    # ─────────────────────────────────────────────────────────────
    #  FR-04: SHAP Feature Attribution
    # ─────────────────────────────────────────────────────────────

    def _compute_shap_values(self, rf_features: np.ndarray):
        """
        FR-04: Compute SHAP values for the current RF prediction.

        Uses SHAP TreeExplainer (fast, exact for tree models) to produce
        per-feature attribution scores. Results are stored in
        `self._last_shap_values` as {feature_name: shap_value}.

        Args:
            rf_features: (1, n_features) numpy array for the current window.
        """
        if not _SHAP_AVAILABLE or not self._rf_loaded or self._rf_model is None:
            return

        try:
            if self._shap_explainer is None:
                self._shap_explainer = _shap.TreeExplainer(self._rf_model)

            # SHAP for class 1 (crash)
            shap_vals = self._shap_explainer.shap_values(rf_features)

            # shap_values shape: [2] for binary → pick class 1
            if isinstance(shap_vals, list) and len(shap_vals) == 2:
                vals = shap_vals[1][0]   # shape (n_features,)
            elif isinstance(shap_vals, np.ndarray):
                if shap_vals.ndim == 3:
                    vals = shap_vals[0, :, 1]  # newer shap: (1, n_features, 2)
                else:
                    vals = shap_vals[0]
            else:
                return

            self._last_shap_values = {
                name: round(float(val), 6)
                for name, val in zip(_RF_FEATURE_NAMES, vals)
            }
        except Exception as e:
            print(f"[CrashPredictor] SHAP computation error: {e}")


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════
crash_predictor = HybridCrashPredictor()
