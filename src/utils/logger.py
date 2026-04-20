import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "project" / "logs"

class DispatchLogger:
    def __init__(self):
        if not LOG_DIR.exists():
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"dispatch_log_{self.timestamp}.json"
        self._entries = []

    def log_attempt(self, input_items: Any, selection_result: Any = None, loading_result: Any = None, error: str = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": input_items,
            "selection": selection_result,
            "loading": loading_result,
            "error": error,
            "status": "SUCCESS" if not error else "FAILED"
        }
        self._entries.append(entry)
        self._save()

    def _save(self):
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, indent=2, ensure_ascii=False)

# Singleton instance
dispatch_logger = DispatchLogger()
