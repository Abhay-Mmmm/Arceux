"""
Detection Engine for Arxis SOC

Rules-based threat detection that analyzes incoming logs and generates signals.
Each detection rule has a clear, testable condition.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from collections import defaultdict, deque
from models import SecurityLog, DetectionSignal, SignalType, Severity


class DetectionEngine:
    """
    Stateful detection engine using sliding windows and pattern matching.
    
    Rules:
    1. BRUTE_FORCE: >5 failed logins in 2 minutes
    2. SUSPICIOUS_LOGIN: Login from unusual/risky location
    3. INSIDER_THREAT: Privilege escalation + data access
    """
    
    def __init__(self):
        # Sliding window: last 2 minutes of failed logins per user
        self.failed_login_window: dict = defaultdict(lambda: deque(maxlen=20))
        
        # Track privilege escalations for insider threat correlation
        self.recent_escalations: dict = defaultdict(lambda: deque(maxlen=10))
        
        # Suspicious locations
        self.suspicious_locations = {
            "Russia",
            "North Korea",
            "Unknown",
            "Tor Exit Node",
            "Romania",
            "Iran",
        }
    
    def analyze(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """
        Analyze a single log and return a detection signal if a rule matches.
        
        Args:
            log: The security log to analyze
            
        Returns:
            DetectionSignal if a threat is detected, None otherwise
        """
        # Rule 1: Brute Force Detection
        if log.event_type == "failed_login":
            signal = self._check_brute_force(log)
            if signal:
                return signal
        
        # Rule 2: Suspicious Login
        if log.event_type in ["successful_login", "new_country_login"]:
            signal = self._check_suspicious_login(log)
            if signal:
                return signal
        
        # Rule 3: Insider Threat
        if log.event_type == "privilege_escalation":
            # Track escalation
            self.recent_escalations[log.user].append(log)
        
        if log.event_type == "data_download":
            signal = self._check_insider_threat(log)
            if signal:
                return signal
        
        return None
    
    def _check_brute_force(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Detect brute force attacks: >5 failed logins in 2 minutes."""
        user = log.user
        now = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
        
        # Add current failed login to window
        self.failed_login_window[user].append(log)
        
        # Count failed logins in last 2 minutes
        two_minutes_ago = now - timedelta(minutes=2)
        recent_failures = [
            l for l in self.failed_login_window[user]
            if datetime.fromisoformat(l.timestamp.replace('Z', '+00:00')) > two_minutes_ago
        ]
        
        if len(recent_failures) > 5:
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.BRUTE_FORCE,
                user=user,
                severity=Severity.HIGH,
                events=recent_failures,
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "failed_attempts": len(recent_failures),
                    "time_window": "2 minutes",
                    "ips": list(set([l.ip for l in recent_failures]))
                }
            )
        
        return None
    
    def _check_suspicious_login(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Detect logins from suspicious locations."""
        if log.location in self.suspicious_locations:
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.SUSPICIOUS_LOGIN,
                user=log.user,
                severity=Severity.HIGH,
                events=[log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "location": log.location,
                    "ip": log.ip,
                    "risk_reason": "Geographic anomaly"
                }
            )
        
        return None
    
    def _check_insider_threat(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """
        Detect insider threats: privilege escalation followed by data download.
        """
        user = log.user
        
        # Check if user had recent privilege escalation
        if self.recent_escalations[user]:
            # Find most recent escalation
            recent_escalations = list(self.recent_escalations[user])
            
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.INSIDER_THREAT,
                user=user,
                severity=Severity.CRITICAL,
                events=recent_escalations + [log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "privilege_escalation → data_download",
                    "asset": log.asset,
                    "escalation_count": len(recent_escalations)
                }
            )
        
        return None


# Global detection engine instance
detection_engine = DetectionEngine()
