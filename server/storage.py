"""
In-Memory Storage for Arxis SOC POC

Simple, elegant in-memory storage with JSON persistence.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from models import SecurityLog, DetectionSignal, Alert, Severity
from threading import Lock


class ArxisStorage:
    """Thread-safe in-memory storage with optional JSON persistence."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # In-memory stores
        self.logs: List[Dict[str, Any]] = []
        self.signals: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        
        # Thread safety
        self._lock = Lock()
        
        # Load persisted data
        self._load_from_disk()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Logs
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def add_log(self, log: SecurityLog) -> None:
        """Add a security log."""
        with self._lock:
            self.logs.append(log.model_dump())
            # Keep only last 1000 logs to prevent memory overflow
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get most recent logs."""
        with self._lock:
            return self.logs[-limit:]
    
    def get_logs_for_user(self, user: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get logs for a specific user."""
        with self._lock:
            user_logs = [log for log in self.logs if log["user"] == user]
            return user_logs[-limit:]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Detection Signals
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def add_signal(self, signal: DetectionSignal) -> None:
        """Add a detection signal."""
        with self._lock:
            self.signals.append(signal.model_dump())
    
    def get_pending_signals(self) -> List[Dict[str, Any]]:
        """Get signals not yet processed by agents."""
        with self._lock:
            return [s for s in self.signals if not s.get("processed", False)]
    
    def mark_signal_processed(self, signal_id: str) -> None:
        """Mark a signal as processed."""
        with self._lock:
            for signal in self.signals:
                if signal["signal_id"] == signal_id:
                    signal["processed"] = True
                    break
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Alerts
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def add_alert(self, alert: Alert) -> None:
        """Add a finalized alert."""
        with self._lock:
            self.alerts.append(alert.model_dump())
            self._persist_to_disk()
    
    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts."""
        with self._lock:
            return self.alerts.copy()
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert by ID."""
        with self._lock:
            for alert in self.alerts:
                if alert["alert_id"] == alert_id:
                    return alert.copy()
            return None
    
    def get_alerts_by_severity(self, severity: Severity) -> List[Dict[str, Any]]:
        """Get alerts filtered by severity."""
        with self._lock:
            return [a for a in self.alerts if a["severity"] == severity.value]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Metrics
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate system metrics."""
        with self._lock:
            # Count alerts by severity
            severity_counts = {
                "LOW": 0,
                "MEDIUM": 0,
                "HIGH": 0,
                "CRITICAL": 0
            }
            
            for alert in self.alerts:
                severity = alert["severity"]
                if severity in severity_counts:
                    severity_counts[severity] += 1
            
            # Recent activity (last 10 alerts)
            recent = self.alerts[-10:] if len(self.alerts) >= 10 else self.alerts
            
            return {
                "total_logs": len(self.logs),
                "total_alerts": len(self.alerts),
                "alerts_by_severity": severity_counts,
                "recent_activity": recent
            }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Persistence
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _persist_to_disk(self) -> None:
        """Persist alerts to disk."""
        alerts_file = self.data_dir / "alerts.json"
        try:
            with open(alerts_file, "w") as f:
                json.dump(self.alerts, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to persist alerts: {e}")
    
    def _load_from_disk(self) -> None:
        """Load alerts from disk on startup."""
        alerts_file = self.data_dir / "alerts.json"
        if alerts_file.exists():
            try:
                with open(alerts_file, "r") as f:
                    self.alerts = json.load(f)
                print(f"✅ Loaded {len(self.alerts)} alerts from disk")
            except Exception as e:
                print(f"⚠️  Failed to load alerts: {e}")
    
    def clear_all(self) -> None:
        """Clear all data (for testing)."""
        with self._lock:
            self.logs.clear()
            self.signals.clear()
            self.alerts.clear()
            self._persist_to_disk()


# Global storage instance
storage = ArxisStorage()
