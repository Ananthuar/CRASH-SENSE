"""
CrashSense — Synthetic Training Data Generator & Model Trainer
================================================================

Generates a synthetic dataset of system metric snapshots labelled as
crash-likely (1) or healthy (0), then trains a Random Forest classifier.
It also looks for REAL crash logs and adaptively merges them into the
training dataset.

The dataset uses PERCENTAGE / NORMALIZED features so the model is
system-agnostic — works on any hardware regardless of specs.

Usage:
    python train_model.py
    # → Saves model to backend/models/crash_rf_model.joblib
"""

import os
import glob
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
import joblib

np.random.seed(42)

# ─────────────────────────────────────────────────────────────────
#  Feature names — must match crash_predictor.py's feature order
# ─────────────────────────────────────────────────────────────────
FEATURE_NAMES = [
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


def _clip(arr, lo=0.0, hi=100.0):
    return np.clip(arr, lo, hi)


# ─────────────────────────────────────────────────────────────────
#  Synthetic Data Generation
# ─────────────────────────────────────────────────────────────────

def _add_new_features(data, mode="healthy"):
    """Helper to add the 7 new engineered features based on the base metrics."""
    n = len(data["cpu_percent"])
    data["cpu_memory_product"] = data["cpu_percent"] * data["memory_percent"] / 10000.0
    data["resource_ratio"] = data["cpu_percent"] / (data["memory_percent"] + 1e-8)
    
    if mode == "healthy" or mode == "moderate":
        data["cpu_acceleration"] = np.random.normal(0, 1, n)
        data["memory_acceleration"] = np.random.normal(0, 0.5, n)
        data["window_divergence_cpu"] = np.random.normal(0, 2, n)
        data["window_divergence_memory"] = np.random.normal(0, 2, n)
        data["cpu_trend"] = np.random.normal(0, 0.5, n)
        data["memory_trend"] = np.random.normal(0, 0.2, n)
    elif mode == "cpu_exhaustion":
        data["cpu_acceleration"] = np.random.normal(2, 2, n)
        data["memory_acceleration"] = np.random.normal(0, 1, n)
        data["window_divergence_cpu"] = np.random.normal(15, 5, n)
        data["window_divergence_memory"] = np.random.normal(2, 3, n)
        data["cpu_trend"] = np.random.normal(1, 1, n)
        data["memory_trend"] = np.random.normal(0, 0.5, n)
    elif mode == "memory_exhaustion":
        data["cpu_acceleration"] = np.random.normal(0, 2, n)
        data["memory_acceleration"] = np.random.normal(1.5, 1, n)
        data["window_divergence_cpu"] = np.random.normal(2, 5, n)
        data["window_divergence_memory"] = np.random.normal(12, 4, n)
        data["cpu_trend"] = np.random.normal(0, 1, n)
        data["memory_trend"] = np.random.normal(1, 0.5, n)
    elif mode == "combined":
        data["cpu_acceleration"] = np.random.normal(1.5, 2, n)
        data["memory_acceleration"] = np.random.normal(1.5, 2, n)
        data["window_divergence_cpu"] = np.random.normal(10, 5, n)
        data["window_divergence_memory"] = np.random.normal(10, 5, n)
        data["cpu_trend"] = np.random.normal(1, 1, n)
        data["memory_trend"] = np.random.normal(1, 1, n)
    elif mode == "spikes":
        data["cpu_acceleration"] = np.random.normal(8, 4, n)
        data["memory_acceleration"] = np.random.normal(5, 3, n)
        data["window_divergence_cpu"] = np.random.normal(25, 10, n)
        data["window_divergence_memory"] = np.random.normal(20, 8, n)
        data["cpu_trend"] = np.random.normal(3, 2, n)
        data["memory_trend"] = np.random.normal(2, 2, n)
    elif mode == "degradation" or mode == "io_storm":
        data["cpu_acceleration"] = np.random.normal(0.5, 1, n)
        data["memory_acceleration"] = np.random.normal(0.5, 1, n)
        data["window_divergence_cpu"] = np.random.normal(5, 3, n)
        data["window_divergence_memory"] = np.random.normal(5, 3, n)
        data["cpu_trend"] = np.random.normal(2, 1, n)
        data["memory_trend"] = np.random.normal(3, 1, n)
    
    return data

def generate_healthy_samples(n: int) -> pd.DataFrame:
    data = {
        "cpu_percent":           _clip(np.random.normal(30, 15, n)),
        "memory_percent":        _clip(np.random.normal(45, 12, n)),
        "disk_usage_percent":    _clip(np.random.normal(50, 15, n)),
        "cpu_std":               _clip(np.random.exponential(3, n), 0, 30),
        "memory_std":            _clip(np.random.exponential(2, n), 0, 20),
        "cpu_rate_of_change":    np.random.normal(0, 3, n),
        "memory_rate_of_change": np.random.normal(0, 1.5, n),
        "io_read_intensity":     _clip(np.random.exponential(0.1, n), 0, 1),
        "io_write_intensity":    _clip(np.random.exponential(0.08, n), 0, 1),
        "net_send_intensity":    _clip(np.random.exponential(0.1, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.exponential(0.12, n), 0, 1),
    }
    data = _add_new_features(data, mode="healthy")
    df = pd.DataFrame(data)
    df["crash"] = 0
    return df

def generate_cpu_exhaustion(n: int) -> pd.DataFrame:
    data = {
        "cpu_percent":           _clip(np.random.normal(93, 4, n), 80, 100),
        "memory_percent":        _clip(np.random.normal(55, 15, n)),
        "disk_usage_percent":    _clip(np.random.normal(55, 15, n)),
        "cpu_std":               _clip(np.random.exponential(2, n), 0, 15),
        "memory_std":            _clip(np.random.exponential(3, n), 0, 20),
        "cpu_rate_of_change":    np.random.normal(5, 3, n),
        "memory_rate_of_change": np.random.normal(2, 2, n),
        "io_read_intensity":     _clip(np.random.exponential(0.2, n), 0, 1),
        "io_write_intensity":    _clip(np.random.exponential(0.15, n), 0, 1),
        "net_send_intensity":    _clip(np.random.exponential(0.1, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.exponential(0.1, n), 0, 1),
    }
    data = _add_new_features(data, mode="cpu_exhaustion")
    df = pd.DataFrame(data)
    df["crash"] = 1
    return df

def generate_memory_exhaustion(n: int) -> pd.DataFrame:
    data = {
        "cpu_percent":           _clip(np.random.normal(50, 20, n)),
        "memory_percent":        _clip(np.random.normal(90, 5, n), 78, 100),
        "disk_usage_percent":    _clip(np.random.normal(60, 15, n)),
        "cpu_std":               _clip(np.random.exponential(4, n), 0, 25),
        "memory_std":            _clip(np.random.exponential(1.5, n), 0, 15),
        "cpu_rate_of_change":    np.random.normal(2, 3, n),
        "memory_rate_of_change": np.random.normal(3, 2, n),
        "io_read_intensity":     _clip(np.random.exponential(0.15, n), 0, 1),
        "io_write_intensity":    _clip(np.random.exponential(0.3, n), 0, 1),
        "net_send_intensity":    _clip(np.random.exponential(0.1, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.exponential(0.1, n), 0, 1),
    }
    data = _add_new_features(data, mode="memory_exhaustion")
    df = pd.DataFrame(data)
    df["crash"] = 1
    return df

def generate_combined_stress(n: int) -> pd.DataFrame:
    data = {
        "cpu_percent":           _clip(np.random.normal(88, 6, n), 75, 100),
        "memory_percent":        _clip(np.random.normal(85, 6, n), 72, 100),
        "disk_usage_percent":    _clip(np.random.normal(70, 12, n)),
        "cpu_std":               _clip(np.random.exponential(5, n), 0, 25),
        "memory_std":            _clip(np.random.exponential(4, n), 0, 20),
        "cpu_rate_of_change":    np.random.normal(4, 4, n),
        "memory_rate_of_change": np.random.normal(3, 3, n),
        "io_read_intensity":     _clip(np.random.exponential(0.3, n), 0, 1),
        "io_write_intensity":    _clip(np.random.exponential(0.25, n), 0, 1),
        "net_send_intensity":    _clip(np.random.exponential(0.2, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.exponential(0.2, n), 0, 1),
    }
    data = _add_new_features(data, mode="combined")
    df = pd.DataFrame(data)
    df["crash"] = 1
    return df

def generate_io_storm(n: int) -> pd.DataFrame:
    data = {
        "cpu_percent":           _clip(np.random.normal(60, 15, n)),
        "memory_percent":        _clip(np.random.normal(65, 12, n)),
        "disk_usage_percent":    _clip(np.random.normal(80, 10, n), 60, 100),
        "cpu_std":               _clip(np.random.exponential(6, n), 0, 25),
        "memory_std":            _clip(np.random.exponential(3, n), 0, 20),
        "cpu_rate_of_change":    np.random.normal(3, 4, n),
        "memory_rate_of_change": np.random.normal(2, 2, n),
        "io_read_intensity":     _clip(np.random.normal(0.7, 0.15, n), 0.3, 1),
        "io_write_intensity":    _clip(np.random.normal(0.65, 0.15, n), 0.3, 1),
        "net_send_intensity":    _clip(np.random.normal(0.5, 0.2, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.normal(0.55, 0.2, n), 0, 1),
    }
    data = _add_new_features(data, mode="io_storm")
    df = pd.DataFrame(data)
    df["crash"] = 1
    return df

def generate_rapid_spikes(n: int) -> pd.DataFrame:
    data = {
        "cpu_percent":           _clip(np.random.normal(70, 20, n)),
        "memory_percent":        _clip(np.random.normal(65, 15, n)),
        "disk_usage_percent":    _clip(np.random.normal(55, 15, n)),
        "cpu_std":               _clip(np.random.normal(18, 5, n), 8, 40),
        "memory_std":            _clip(np.random.normal(12, 4, n), 5, 30),
        "cpu_rate_of_change":    np.random.normal(15, 8, n),
        "memory_rate_of_change": np.random.normal(10, 5, n),
        "io_read_intensity":     _clip(np.random.exponential(0.2, n), 0, 1),
        "io_write_intensity":    _clip(np.random.exponential(0.2, n), 0, 1),
        "net_send_intensity":    _clip(np.random.exponential(0.15, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.exponential(0.15, n), 0, 1),
    }
    data = _add_new_features(data, mode="spikes")
    df = pd.DataFrame(data)
    df["crash"] = 1
    return df

def generate_gradual_degradation(n: int) -> pd.DataFrame:
    t = np.linspace(0, 1, n)
    data = {
        "cpu_percent":           _clip(np.random.normal(45, 10, n) + t * 20),
        "memory_percent":        _clip(55 + t * 35 + np.random.normal(0, 3, n), 50, 100),
        "disk_usage_percent":    _clip(np.random.normal(55, 10, n) + t * 10),
        "cpu_std":               _clip(np.random.exponential(3, n) + t * 5, 0, 25),
        "memory_std":            _clip(np.random.exponential(1, n) + t * 3, 0, 15),
        "cpu_rate_of_change":    np.random.normal(1, 2, n) + t * 5,
        "memory_rate_of_change": np.random.normal(0.5, 1, n) + t * 8,
        "io_read_intensity":     _clip(np.random.exponential(0.1, n) + t * 0.2, 0, 1),
        "io_write_intensity":    _clip(np.random.exponential(0.1, n) + t * 0.3, 0, 1),
        "net_send_intensity":    _clip(np.random.exponential(0.08, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.exponential(0.1, n), 0, 1),
    }
    data = _add_new_features(data, mode="degradation")
    df = pd.DataFrame(data)
    df["crash"] = (t > 0.5).astype(int)
    return df

def generate_moderate_load(n: int) -> pd.DataFrame:
    data = {
        "cpu_percent":           _clip(np.random.normal(60, 10, n)),
        "memory_percent":        _clip(np.random.normal(55, 10, n)),
        "disk_usage_percent":    _clip(np.random.normal(60, 10, n)),
        "cpu_std":               _clip(np.random.exponential(5, n), 0, 20),
        "memory_std":            _clip(np.random.exponential(3, n), 0, 15),
        "cpu_rate_of_change":    np.random.normal(1, 3, n),
        "memory_rate_of_change": np.random.normal(0.5, 2, n),
        "io_read_intensity":     _clip(np.random.exponential(0.15, n), 0, 1),
        "io_write_intensity":    _clip(np.random.exponential(0.12, n), 0, 1),
        "net_send_intensity":    _clip(np.random.exponential(0.15, n), 0, 1),
        "net_recv_intensity":    _clip(np.random.exponential(0.15, n), 0, 1),
    }
    data = _add_new_features(data, mode="moderate")
    df = pd.DataFrame(data)
    df["crash"] = 0
    return df

def generate_synthetic_dataset() -> pd.DataFrame:
    parts = [
        generate_healthy_samples(2000),
        generate_moderate_load(1000),
        generate_cpu_exhaustion(500),
        generate_memory_exhaustion(500),
        generate_combined_stress(400),
        generate_io_storm(400),
        generate_rapid_spikes(400),
        generate_gradual_degradation(400),
    ]
    df = pd.concat(parts, ignore_index=True)
    return df

# ─────────────────────────────────────────────────────────────────
#  Adaptive Real Logs Ingestion
# ─────────────────────────────────────────────────────────────────

def load_real_logs(log_dir="data/real_logs") -> pd.DataFrame:
    """Read genuine crash logs from disk and adapt."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_path = os.path.join(base_dir, log_dir, "*.json")
    files = glob.glob(logs_path)
    
    records = []
    for fpath in files:
        try:
            with open(fpath, "r") as f:
                payload = json.load(f)
                features_dict = payload.get("engineered_features", {})
                
                # Check if it has all the current features
                if all(feat in features_dict for feat in FEATURE_NAMES):
                    row = {feat: features_dict[feat] for feat in FEATURE_NAMES}
                    row["crash"] = payload.get("label", 1)
                    records.append(row)
        except Exception as e:
            print(f"Warning: Failed to load {fpath}: {e}")
            
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    
    # Class Imbalance Strategy: Oversample real logs heavily
    # Since real logs are very valuable and rare
    dup_factor = 20
    df = pd.concat([df] * dup_factor, ignore_index=True)
    return df

# ─────────────────────────────────────────────────────────────────
#  Pipeline Execution
# ─────────────────────────────────────────────────────────────────

def train_and_save():
    print("=" * 60)
    print("  CrashSense — Model Training Pipeline (Adaptive)")
    print("=" * 60)

    # ── Generate & Load data ─────────────────────────────────────
    print("\n[1/4] Preparing data (Synthetic + Real)...")
    df_synth = generate_synthetic_dataset()
    df_real = load_real_logs()
    
    df = pd.concat([df_synth, df_real], ignore_index=True) if not df_real.empty else df_synth
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"      Synthetic samples: {len(df_synth)}")
    print(f"      Real-world samples (oversampled): {len(df_real)}")
    print(f"      Total Training Pool: {len(df)}")
    print(f"      Healthy: {(df['crash'] == 0).sum()}")
    print(f"      Crash:   {(df['crash'] == 1).sum()}")
    print(f"      Active Features: {len(FEATURE_NAMES)}")

    X = df[FEATURE_NAMES].values
    y = df["crash"].values

    # ── Train/test split ─────────────────────────────────────────
    print("\n[2/4] Splitting data (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )
    print(f"      Train: {len(X_train)}  |  Test: {len(X_test)}")

    # ── Train Random Forest ──────────────────────────────────────
    print("\n[3/4] Training Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced", # Handles any remaining class imbalance
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n      Accuracy: {accuracy:.4f}")
    print("\n      Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Healthy", "Crash"]))

    # Feature importances
    print("\n      Top Feature Importances:")
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for i in sorted_idx[:10]:
        bar = "\u2588" * int(importances[i] * 40)
        print(f"        {FEATURE_NAMES[i]:28s} {importances[i]:.4f}  {bar}")

    # ── Save model ───────────────────────────────────────────────
    print("\n[4/4] Saving model...")
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "crash_rf_model.joblib")
    
    # Safely overwrite
    joblib.dump({
        "model":         model,
        "feature_names": FEATURE_NAMES,
        "version":       "2.0.0",
        "n_estimators":  200,
        "accuracy":      accuracy,
    }, model_path)
    
    print(f"      Saved to: {model_path}")
    print(f"      File size: {os.path.getsize(model_path) / 1024:.1f} KB")
    print("\n" + "=" * 60)
    print("  Training complete!")
    print("=" * 60)

if __name__ == "__main__":
    train_and_save()
