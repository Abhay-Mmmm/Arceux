"""
In-Memory Storage for Arceux SOC POC

Purely in-memory storage — no disk persistence. Alerts always start fresh on restart.
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from models import SecurityLog, DetectionSignal, Alert, Severity
from threading import Lock

_AGENT_NAMES = [
    "Orchestrator Agent",
    "Alert Handler Agent",
    "Threat Analyzer Agent",
    "Root Cause Agent",
    "Compliance Agent",
    "Response Automation Agent",
]


class ArceuxStorage:
    """Thread-safe in-memory storage. No disk I/O — always starts clean."""

    PIPELINE_COOLDOWN_SECONDS: int = 15

    def __init__(self):
        # In-memory stores
        self.logs: List[Dict[str, Any]] = []
        self.signals: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.executed_actions: List[Dict[str, Any]] = []

        # Action tracking sets
        self.blocked_ips: Set[str] = set()
        self.flagged_users: Set[str] = set()

        # Per-agent state tracking
        self.agent_states: Dict[str, Dict[str, Any]] = {
            name: {
                "name": name,
                "status": "idle",
                "last_run": None,
                "tasks_completed": 0,
                "execution_count": 0,
                "total_execution_time_ms": 0,
                "last_execution_trace": [],
            }
            for name in _AGENT_NAMES
        }

        # Pipeline rate limiting
        self.last_pipeline_run: float = 0.0
        self.pipeline_running: bool = False

        # Thread safety
        self._lock = Lock()

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

    def update_alert_status(self, alert_id: str, status: str) -> bool:
        """Update the status field of an alert."""
        with self._lock:
            for alert in self.alerts:
                if alert["alert_id"] == alert_id:
                    alert["status"] = status
                    return True
        return False

    def add_alert_note(self, alert_id: str, note: str) -> bool:
        """Append a note to an alert's metadata.notes list."""
        with self._lock:
            for alert in self.alerts:
                if alert["alert_id"] == alert_id:
                    if "notes" not in alert.setdefault("metadata", {}):
                        alert["metadata"]["notes"] = []
                    alert["metadata"]["notes"].append({
                        "text": note,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return True
        return False

    def add_executed_action(self, action: Dict[str, Any]) -> None:
        """Log an executed response action."""
        with self._lock:
            self.executed_actions.append(action)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Agent State
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def update_agent_state(self, agent_name: str, updates: Dict[str, Any]) -> None:
        """Update state fields for a specific agent."""
        with self._lock:
            if agent_name in self.agent_states:
                self.agent_states[agent_name].update(updates)

    def get_all_agent_states(self) -> List[Dict[str, Any]]:
        """Return a snapshot of all agent states."""
        with self._lock:
            return [dict(s) for s in self.agent_states.values()]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Metrics
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_metrics(self) -> Dict[str, Any]:
        """Calculate system metrics."""
        with self._lock:
            severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

            for alert in self.alerts:
                severity = alert["severity"]
                if severity in severity_counts:
                    severity_counts[severity] += 1

            recent = self.alerts[-10:] if len(self.alerts) >= 10 else self.alerts

            return {
                "total_logs": len(self.logs),
                "total_alerts": len(self.alerts),
                "alerts_by_severity": severity_counts,
                "recent_activity": recent
            }

    def clear_all(self) -> None:
        """Clear all in-memory data and reset pipeline rate-limit state."""
        with self._lock:
            self.logs.clear()
            self.signals.clear()
            self.alerts.clear()
            self.pipeline_running = False
            self.last_pipeline_run = 0.0


# Global storage instance
storage = ArceuxStorage()
