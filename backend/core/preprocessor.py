import numpy as np

class DataScaler:
    def __init__(self):
        # Define min-max ranges for normalization based on typical hardware limits
        self.ranges = {
            'cpu_percent': (0, 100),
            'memory_percent': (0, 100),
            # Disk and Net bytes are unbounded, but we can use a soft max or log scale
            # For simplicity, we'll use a log1p scale for bytes
        }

    def normalize_metrics(self, metrics):
        """
        Normalize metrics dictionary to 0-1 range where possible, or log scale.
        """
        if not metrics:
            return {}
        
        normalized = {}
        
        # Linear scaling for percentages
        normalized['cpu_percent'] = metrics.get('cpu_percent', 0) / 100.0
        normalized['memory_percent'] = metrics.get('memory_percent', 0) / 100.0
        
        # Log scaling for bytes
        normalized['disk_read_bytes'] = np.log1p(metrics.get('disk_read_bytes', 0))
        normalized['disk_write_bytes'] = np.log1p(metrics.get('disk_write_bytes', 0))
        normalized['net_bytes_recv'] = np.log1p(metrics.get('net_bytes_recv', 0))
        normalized['net_bytes_sent'] = np.log1p(metrics.get('net_bytes_sent', 0))
        
        # Pass through timestamp
        normalized['timestamp'] = metrics.get('timestamp')
        
        return normalized

class LogTokenizer:
    def __init__(self, vocab_size=1000):
        self.vocab_size = vocab_size
        self.token_map = {'<PAD>': 0, '<UNK>': 1}
        self.next_token_id = 2

    def tokenize_log(self, log_line):
        """
        Simple tokenizer that splits by spaces and maps to token IDs.
        Auto-expands vocabulary up to vocab_size.
        """
        tokens = log_line.strip().split()
        token_ids = []
        
        for token in tokens:
            if token not in self.token_map:
                if self.next_token_id < self.vocab_size:
                    self.token_map[token] = self.next_token_id
                    self.next_token_id += 1
                else:
                    token = '<UNK>'
            
            token_ids.append(self.token_map.get(token, 1)) # 1 is <UNK>
            
        return token_ids

# Global instances
data_scaler = DataScaler()
log_tokenizer = LogTokenizer()
