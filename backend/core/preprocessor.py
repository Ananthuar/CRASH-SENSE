"""
CrashSense — Data Preprocessing Module
========================================

Provides two preprocessing utilities for the crash prediction pipeline:

1. **DataScaler**
   Normalises raw system metrics into a 0-1 range suitable for ML models.
   - Percentage metrics (CPU, memory) → simple linear scaling ÷ 100.
   - Byte counters (disk I/O, network I/O) → logarithmic scaling via
     `np.log1p()` to handle the wide dynamic range of byte values.

2. **LogTokenizer**
   Converts raw log lines into integer token sequences for NLP-based
   crash prediction models.
   - Builds a vocabulary on-the-fly up to `vocab_size` tokens.
   - Uses <PAD> (0) and <UNK> (1) as special tokens.
   - Words not in the vocabulary default to <UNK>.

Module-Level Singletons:
    `data_scaler`    — Pre-created DataScaler instance.
    `log_tokenizer`  — Pre-created LogTokenizer instance (vocab_size=1000).

Usage:
    from core.preprocessor import data_scaler, log_tokenizer

    normalised = data_scaler.normalize_metrics(raw_metrics)
    token_ids  = log_tokenizer.tokenize_log("ERROR: connection refused")
"""

import numpy as np


class DataScaler:
    """
    Normalises raw system metrics for ML model input.

    Strategy:
        - Percentage fields (0-100 range)  → divide by 100
        - Byte magnitude fields            → np.log1p() for logarithmic compression
        - Timestamp                        → passed through unchanged

    Attributes:
        ranges (dict): Reference ranges for linear normalisation.
                       Currently only used for documentation; the actual
                       scaling is hardcoded for performance.
    """

    def __init__(self):
        # Reference ranges for percentage-based metrics (informational).
        # Byte-based metrics use log scaling instead of min-max.
        self.ranges = {
            'cpu_percent': (0, 100),
            'memory_percent': (0, 100),
        }

    def normalize_metrics(self, metrics):
        """
        Normalise a metrics dictionary.

        Args:
            metrics: Raw metrics dict from SystemMonitor._collect_metrics().
                     Expected keys: cpu_percent, memory_percent,
                     disk_read_bytes, disk_write_bytes, net_bytes_recv,
                     net_bytes_sent, timestamp.

        Returns:
            dict: Normalised metrics with the same keys. Percentage fields
                  are scaled to [0, 1]; byte fields are log-transformed;
                  timestamp is passed through unchanged.
                  Returns empty dict if input is falsy.
        """
        if not metrics:
            return {}

        normalized = {}

        # ── Linear scaling for percentage metrics (0–100 → 0–1) ──
        normalized['cpu_percent'] = metrics.get('cpu_percent', 0) / 100.0
        normalized['memory_percent'] = metrics.get('memory_percent', 0) / 100.0

        # ── Logarithmic scaling for byte counters ────────────────
        # log1p(x) = ln(1 + x) — handles zero gracefully and compresses
        # large byte values into a manageable range for ML models.
        normalized['disk_read_bytes'] = np.log1p(metrics.get('disk_read_bytes', 0))
        normalized['disk_write_bytes'] = np.log1p(metrics.get('disk_write_bytes', 0))
        normalized['net_bytes_recv'] = np.log1p(metrics.get('net_bytes_recv', 0))
        normalized['net_bytes_sent'] = np.log1p(metrics.get('net_bytes_sent', 0))

        # ── Pass-through fields ──────────────────────────────────
        normalized['timestamp'] = metrics.get('timestamp')

        return normalized


class LogTokenizer:
    """
    Simple whitespace tokenizer with auto-expanding vocabulary.

    Splits log lines on whitespace and maps each token to a unique integer ID.
    The vocabulary grows dynamically until `vocab_size` is reached; any
    subsequent unseen tokens are mapped to <UNK>.

    Special Tokens:
        - <PAD> = 0  — used for sequence padding in batch processing
        - <UNK> = 1  — used for out-of-vocabulary tokens

    Args:
        vocab_size: Maximum number of unique tokens to track (default: 1000).

    Attributes:
        token_map (dict):    Token string → integer ID mapping.
        next_token_id (int): Next available integer ID for new tokens.
    """

    def __init__(self, vocab_size=1000):
        self.vocab_size = vocab_size
        self.token_map = {'<PAD>': 0, '<UNK>': 1}
        self.next_token_id = 2  # IDs 0 and 1 are reserved

    def tokenize_log(self, log_line):
        """
        Convert a raw log line into a list of integer token IDs.

        Args:
            log_line: A single log line string (e.g. "ERROR: OOM in AuthService").

        Returns:
            list[int]: Token IDs corresponding to each whitespace-delimited
                       word. Unknown tokens (after vocab is full) map to 1 (<UNK>).
        """
        tokens = log_line.strip().split()
        token_ids = []

        for token in tokens:
            # Auto-expand vocabulary if capacity remains
            if token not in self.token_map:
                if self.next_token_id < self.vocab_size:
                    self.token_map[token] = self.next_token_id
                    self.next_token_id += 1
                else:
                    # Vocabulary full — fall back to <UNK>
                    token = '<UNK>'

            token_ids.append(self.token_map.get(token, 1))  # 1 = <UNK>

        return token_ids


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL SINGLETONS
#  Pre-created instances for global access across the application.
# ═══════════════════════════════════════════════════════════════
data_scaler = DataScaler()
log_tokenizer = LogTokenizer()
