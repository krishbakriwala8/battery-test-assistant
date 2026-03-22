import pandas as pd
import json
import os
from .data_loader import load_mpt

class BatteryTestAnalyzer:
    """
    Analyzes battery test logs against threshold config.
    """
    
    REQUIRED_COLUMNS = ['timestamp', 'voltage', 'current', 'temperature']
    
    def __init__(self, csv_path: str, config_path: str):
        self.csv_path = csv_path
        self.config_path = config_path
        self.df = None
        self.config = None
        self.violations = []
        self.summary_stats = {}
        self.pass_status = True
        
    def load_data(self) -> bool:
        """Load data from CSV or MPT file based on extension."""
        try:
            ext = os.path.splitext(self.csv_path)[1].lower()
            if ext == '.csv':
                self.df = pd.read_csv(self.csv_path)
            elif ext == '.mpt':
                self.df = load_mpt(self.csv_path)
            else:
                raise ValueError(f"Unsupported file format: {ext}")
            
            # Check required columns
            missing = [col for col in self.REQUIRED_COLUMNS if col not in self.df.columns]
            if missing:
                raise ValueError(f"Missing columns: {missing}")
            
            # Ensure numeric
            for col in self.REQUIRED_COLUMNS[1:]:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            if self.df[self.REQUIRED_COLUMNS[1:]].isnull().any().any():
                raise ValueError("Non-numeric values found in signal columns")
                
            # Load threshold config
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            # Validate config has expected signals
            for signal in self.REQUIRED_COLUMNS[1:]:
                if signal not in self.config:
                    raise ValueError(f"Missing threshold for {signal}")
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def compute_statistics(self):
        """Compute min, max, mean for each signal."""
        for signal in self.REQUIRED_COLUMNS[1:]:
            self.summary_stats[signal] = {
                'min': self.df[signal].min(),
                'max': self.df[signal].max(),
                'mean': self.df[signal].mean()
            }
    
    def check_violations(self):
        """Compare each signal value against thresholds, record violations."""
        self.violations = []
        for idx, row in self.df.iterrows():
            timestamp = row['timestamp']
            for signal in self.REQUIRED_COLUMNS[1:]:
                value = row[signal]
                thresholds = self.config[signal]
                if value < thresholds['min']:
                    self.violations.append({
                        'signal': signal,
                        'timestamp': timestamp,
                        'value': value,
                        'rule': f'below min {thresholds["min"]}'
                    })
                if value > thresholds['max']:
                    self.violations.append({
                        'signal': signal,
                        'timestamp': timestamp,
                        'value': value,
                        'rule': f'above max {thresholds["max"]}'
                    })
        self.pass_status = len(self.violations) == 0
    
    def generate_summary(self) -> str:
        """Create a human-readable summary."""
        if self.pass_status:
            return "Test PASSED: All signals within specified thresholds."
        else:
            lines = ["Test FAILED due to the following violations:"]
            for v in self.violations:
                lines.append(f"  - {v['signal']} at t={v['timestamp']:.2f}: {v['value']:.3f} ({v['rule']})")
            return "\n".join(lines)
    
    def run(self) -> dict:
        """Execute the full analysis and return results."""
        if not self.load_data():
            return {"error": "Data loading failed"}
        self.compute_statistics()
        self.check_violations()
        return {
            "pass": self.pass_status,
            "statistics": self.summary_stats,
            "violations": self.violations,
            "summary": self.generate_summary()
        }