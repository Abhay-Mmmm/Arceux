"""
Detection Engine for Arceux SOC

Rules-based threat detection that analyzes incoming logs and generates signals.
Each detection rule has a clear, testable condition.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict, deque
from models import SecurityLog, DetectionSignal, SignalType, Severity


# Shared high-risk location set — used by both DetectionEngine and RiverAnomalyDetector
SUSPICIOUS_LOCATIONS = {
    "Russia", "North Korea", "Unknown",
    "Tor Exit Node", "Romania", "Iran",
}


class DetectionEngine:
    """
    Stateful detection engine using sliding windows and pattern matching.

    Rules:
    1. BRUTE_FORCE:       >5 failed logins from same user in 2 minutes
    2. SUSPICIOUS_LOGIN:  Login from high-risk location (successful or failed)
    3. IMPOSSIBLE_TRAVEL: Same user in two different locations within 10 minutes
    4. ACCOUNT_TAKEOVER:  Successful login after 3+ failures in 5 minutes
    5. INSIDER_THREAT:    Privilege escalation followed by data download
    6. DATA_EXFILTRATION: Downloads from 3+ different assets in 5 minutes
    """

    def __init__(self):
        self.failed_login_window: dict = defaultdict(lambda: deque(maxlen=20))
        self.recent_escalations: dict = defaultdict(lambda: deque(maxlen=10))
        self.data_download_window: dict = defaultdict(lambda: deque(maxlen=30))
        self.last_login_location: Dict[str, Dict[str, Any]] = {}

        self.suspicious_locations = SUSPICIOUS_LOCATIONS

        # River online ML anomaly detector (Rule 7)
        threshold = float(os.getenv("RIVER_ANOMALY_THRESHOLD", "0.75"))
        _river = RiverAnomalyDetector(threshold)
        self.river_detector = _river if _river._available else None
        if self.river_detector is not None:
            print(f"[RIVER] Anomaly detector initialized (threshold={threshold}, cohorts=3)")

    def analyze(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Analyze a single log and return a signal if a rule matches."""

        # River learns from every event regardless of which rule fires.
        # Rule signals take priority; river_signal is the fallback if all rules miss.
        river_signal = self.river_detector.detect(log) if self.river_detector is not None else None

        # ── Rule 1: Brute Force ──────────────────────────────────────────
        if log.event_type == "failed_login":
            signal = self._check_brute_force(log)
            if signal:
                return signal

            # Rule 2b: Failed login FROM suspicious location → MEDIUM probe alert
            if log.location in self.suspicious_locations:
                return DetectionSignal(
                    signal_id=str(uuid.uuid4()),
                    signal_type=SignalType.SUSPICIOUS_LOGIN,
                    user=log.user,
                    severity=Severity.MEDIUM,
                    events=[log],
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    metadata={
                        "location": log.location,
                        "ip": log.ip,
                        "risk_reason": "Failed login attempt from high-risk location",
                    }
                )

        # ── Login events: travel + location + account takeover ───────────
        if log.event_type in ["successful_login", "new_country_login"]:
            now = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
            prev = self.last_login_location.get(log.user)
            self.last_login_location[log.user] = {"location": log.location, "timestamp": now}

            # Rule 3: Impossible Travel → CRITICAL
            if prev:
                signal = self._check_impossible_travel(log, prev, now)
                if signal:
                    return signal

            # Rule 2: Suspicious location → HIGH
            signal = self._check_suspicious_login(log)
            if signal:
                return signal

        # Rule 4: Account Takeover → HIGH
        if log.event_type == "successful_login":
            signal = self._check_account_takeover(log)
            if signal:
                return signal

        # ── Rule 5: Insider Threat ───────────────────────────────────────
        if log.event_type == "privilege_escalation":
            self.recent_escalations[log.user].append(log)

        if log.event_type == "data_download":
            signal = self._check_insider_threat(log)
            if signal:
                return signal

            # Rule 6: Data Exfiltration → HIGH
            signal = self._check_data_exfiltration(log)
            if signal:
                return signal

        # Rule 7: River ML — fallback when no rule matched
        return river_signal

    # ── Detection Methods ────────────────────────────────────────────────

    def _check_brute_force(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Rule 1: >5 failed logins from same user in 2 minutes."""
        user = log.user
        now = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
        self.failed_login_window[user].append(log)

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
                    "ips": list(set(l.ip for l in recent_failures)),
                }
            )
        return None

    def _check_suspicious_login(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Rule 2: Successful or new-country login from a high-risk location."""
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
                    "risk_reason": "Geographic anomaly — login from high-risk country",
                }
            )
        return None

    def _check_impossible_travel(
        self, log: SecurityLog, prev: Dict[str, Any], now: datetime
    ) -> Optional[DetectionSignal]:
        """Rule 3: Same user in two different locations within 10 minutes."""
        if log.location == prev["location"]:
            return None

        minutes_apart = (now - prev["timestamp"]).total_seconds() / 60
        if minutes_apart <= 10:
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.SUSPICIOUS_LOGIN,
                user=log.user,
                severity=Severity.CRITICAL,
                events=[log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "impossible_travel",
                    "previous_location": prev["location"],
                    "current_location": log.location,
                    "minutes_between_logins": round(minutes_apart, 1),
                    "risk_reason": (
                        f"Login from {log.location} only "
                        f"{round(minutes_apart, 1)} min after login from {prev['location']}"
                    ),
                }
            )
        return None

    def _check_account_takeover(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Rule 4: Successful login after 3+ failures in 5 minutes — credential stuffing."""
        user = log.user
        now = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
        five_min_ago = now - timedelta(minutes=5)

        recent_failures = [
            l for l in self.failed_login_window[user]
            if datetime.fromisoformat(l.timestamp.replace('Z', '+00:00')) > five_min_ago
        ]

        if len(recent_failures) >= 3:
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.SUSPICIOUS_LOGIN,
                user=user,
                severity=Severity.HIGH,
                events=recent_failures + [log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "account_takeover",
                    "failed_attempts_before_success": len(recent_failures),
                    "time_window": "5 minutes",
                    "risk_reason": "Successful login immediately after multiple failures — possible account takeover",
                }
            )
        return None

    def _check_insider_threat(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Rule 5: Privilege escalation followed by data download."""
        user = log.user
        if self.recent_escalations[user]:
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
                    "escalation_count": len(recent_escalations),
                }
            )
        return None

    def _check_data_exfiltration(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Rule 6: Downloads from 3+ different assets in 5 minutes."""
        user = log.user
        now = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
        self.data_download_window[user].append(log)

        five_min_ago = now - timedelta(minutes=5)
        recent_downloads = [
            l for l in self.data_download_window[user]
            if datetime.fromisoformat(l.timestamp.replace('Z', '+00:00')) > five_min_ago
        ]

        unique_assets = set(l.asset for l in recent_downloads)
        if len(unique_assets) >= 3:
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.ANOMALOUS_ACCESS,
                user=user,
                severity=Severity.HIGH,
                events=recent_downloads,
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "data_exfiltration",
                    "assets_accessed": list(unique_assets),
                    "download_count": len(recent_downloads),
                    "time_window": "5 minutes",
                    "risk_reason": f"Downloaded from {len(unique_assets)} different assets in 5 minutes",
                }
            )
        return None


class RiverAnomalyDetector:
    """
    Online ML anomaly detector using River's HalfSpaceTrees.

    Maintains 3 independent HST models (one per user cohort) and learns
    continuously from every incoming event. Generates ANOMALOUS_ACCESS
    signals when the anomaly score exceeds the configured threshold.

    Warmup: the first ~50 events per cohort produce near-zero scores while
    the model builds its baseline — this is expected, not a bug.
    """

    def __init__(self, threshold: float = 0.75) -> None:
        self._threshold = threshold
        self._event_rate_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

        try:
            from river.anomaly import HalfSpaceTrees
            self._models: Dict[str, Any] = {
                "admin_cohort":    HalfSpaceTrees(n_trees=10, height=8, window_size=50, seed=42),
                "service_cohort":  HalfSpaceTrees(n_trees=10, height=8, window_size=50, seed=42),
                "standard_cohort": HalfSpaceTrees(n_trees=10, height=8, window_size=50, seed=42),
            }
            self._available = True
        except ImportError:
            self._available = False
            self._models = {}
            print("[RIVER] WARNING: river not installed. ML anomaly detection disabled.")

    def _get_cohort(self, username: str) -> str:
        u = username.lower()
        if "admin" in u or "root" in u:
            return "admin_cohort"
        if "service" in u or "svc" in u:
            return "service_cohort"
        return "standard_cohort"

    def _update_event_rate(self, user: str, now: datetime) -> int:
        """Append timestamp to per-user window; return count within last 60 s."""
        window = self._event_rate_windows[user]
        window.append(now)
        cutoff = now - timedelta(seconds=60)
        return sum(1 for t in window if t > cutoff)

    def _extract_features(self, log: SecurityLog, now: datetime) -> Dict[str, float]:
        return {
            "hour_of_day":            float(now.hour),
            "is_suspicious_location": 1.0 if log.location in SUSPICIOUS_LOCATIONS else 0.0,
            "is_failed_login":        1.0 if log.event_type == "failed_login" else 0.0,
            "is_privilege_escalation": 1.0 if log.event_type == "privilege_escalation" else 0.0,
            "is_data_download":       1.0 if log.event_type == "data_download" else 0.0,
            "user_event_rate":        float(self._update_event_rate(log.user, now)),
        }

    def detect(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Learn from the event, then return a signal if score >= threshold."""
        if not self._available:
            return None

        now = datetime.fromisoformat(log.timestamp.replace("Z", "+00:00"))
        cohort = self._get_cohort(log.user)
        features = self._extract_features(log, now)
        model = self._models[cohort]

        model.learn_one(features)
        score: float = model.score_one(features)

        if score >= self._threshold:
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.ANOMALOUS_ACCESS,
                user=log.user,
                severity=Severity.HIGH,
                events=[log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "river_ml": True,
                    "cohort": cohort,
                    "anomaly_score": round(score, 3),
                    "risk_reason": (
                        f"River ML anomaly detected for user {log.user} "
                        f"(cohort: {cohort}, score: {score:.3f})"
                    ),
                },
            )
        return None


# Global detection engine instance
detection_engine = DetectionEngine()
