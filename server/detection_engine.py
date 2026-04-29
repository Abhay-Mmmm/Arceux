"""
Detection Engine for Arceux SOC

Rules-based threat detection that analyzes incoming logs and generates signals.
Each detection rule has a clear, testable condition.
"""

import os
import re
import threading
import time
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
        self.river_detector = RiverAnomalyDetector.try_create(threshold)
        if self.river_detector is not None:
            print(f"[RIVER] Anomaly detector initialized (threshold={threshold}, cohorts=3)")

        # Graph-based threat detector (Rule 8)
        graph_window = int(os.getenv("GRAPH_WINDOW_SECONDS", "300"))
        try:
            self.graph_detector = GraphThreatDetector(graph_window)
            if self.graph_detector._available:
                print(f"[GRAPH] Graph threat detector initialized (window={graph_window}s)")
        except Exception:
            self.graph_detector = None

    def analyze(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Analyze a single log and return a signal if a rule matches."""

        # Graph and River learn from every event so their models stay current.
        # Rule signals take priority; River is the first fallback; Graph is the last.
        graph_signal = self.graph_detector.update(log) if self.graph_detector is not None else None
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
                        "confidence": 65,
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
        if river_signal:
            score = river_signal.metadata.get("anomaly_score", 0)
            local = river_signal.user.split("@")[0]
            cohort = river_signal.metadata.get("cohort", "?")
            print(f"[RIVER] Score {score:.3f} → ANOMALOUS_ACCESS for {local[:4]}*** ({cohort})")
            return river_signal
        # Rule 8: Graph ML — fallback when River also missed
        return graph_signal

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
                    "confidence": min(95, 60 + len(recent_failures) * 5),
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
                    "confidence": 82,
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
                    "confidence": min(99, round(90 + (10 - minutes_apart) * 0.9)),
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
                    "confidence": min(95, 70 + len(recent_failures) * 5),
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
                    "confidence": min(98, 88 + len(recent_escalations) * 5),
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
                    "confidence": min(95, 65 + len(unique_assets) * 5),
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
        # maxlen=200 caps memory per user; at >200 events/60 s the oldest timestamps
        # are evicted, causing an undercount of user_event_rate — acceptable at this scale.
        self._event_rate_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._locks: Dict[str, threading.Lock] = {
            "admin_cohort":    threading.Lock(),
            "service_cohort":  threading.Lock(),
            "standard_cohort": threading.Lock(),
        }

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

    @classmethod
    def try_create(cls, threshold: float = 0.75) -> Optional["RiverAnomalyDetector"]:
        """Return a configured detector if River is installed, else None."""
        instance = cls(threshold)
        return instance if instance._available else None

    def _get_cohort(self, username: str) -> str:
        u = username.lower()
        if re.search(r"\b(admin|root)\b", u):
            return "admin_cohort"
        if re.search(r"\b(service|svc)\b", u):
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

        with self._locks[cohort]:
            self._models[cohort].learn_one(features)
            score: float = self._models[cohort].score_one(features)

        if score >= self._threshold:
            # Redact PII: show only the first 4 chars of the local part
            local = log.user.split("@")[0]
            user_display = local[:4] + "***"
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
                    "confidence": round(score * 100),
                    "risk_reason": (
                        f"River ML anomaly detected for user {user_display} "
                        f"(cohort: {cohort}, score: {score:.3f})"
                    ),
                },
            )
        return None


class GraphThreatDetector:
    """
    Graph-based threat detector using NetworkX MultiDiGraph.

    Builds a rolling temporal graph of ip→user and user→asset relationships,
    pruning edges older than window_seconds. Detects 4 structural attack patterns:

    1. LATERAL_MOVEMENT:   Same IP → 3+ distinct users in window → CRITICAL
    2. COORDINATED_PROBE:  3+ distinct IPs → same user in window → HIGH
    3. HUB_ASSET_PRESSURE: 3+ distinct users → same asset in window → HIGH
    4. IP_REUSE:           Same IP shared by 2+ distinct users in window → HIGH

    A 60-second per-pattern cooldown prevents alert floods.
    Degrades gracefully if networkx is not installed.
    """

    SIGNAL_COOLDOWN = 60  # seconds

    def __init__(self, window_seconds: int = 300) -> None:
        self._window = window_seconds
        self._lock = threading.Lock()
        self._edge_timestamps: list = []  # (ts, u, v, key)
        self._last_signal_time: Dict[str, float] = {}

        try:
            import networkx as nx
            self._graph = nx.MultiDiGraph()
            self._available = True
        except ImportError:
            self._graph = None
            self._available = False
            print("[GRAPH] WARNING: networkx not installed. Graph threat detection disabled.")

    def _cooldown_ok(self, pattern: str) -> bool:
        return (time.time() - self._last_signal_time.get(pattern, 0.0)) >= self.SIGNAL_COOLDOWN

    def _prune_old_edges(self) -> None:
        cutoff = time.time() - self._window
        fresh = []
        for ts, u, v, key in self._edge_timestamps:
            if ts < cutoff:
                try:
                    self._graph.remove_edge(u, v, key=key)
                except Exception:
                    pass
            else:
                fresh.append((ts, u, v, key))
        self._edge_timestamps = fresh

    def _add_edge(self, u: str, v: str) -> None:
        key = self._graph.add_edge(u, v)
        self._edge_timestamps.append((time.time(), u, v, key))

    def _check_lateral_movement(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Same IP connecting to 3+ distinct users."""
        if not self._cooldown_ok("lateral_movement"):
            return None
        ip_node = f"ip:{log.ip}"
        if ip_node not in self._graph:
            return None
        targets = {v for _, v in self._graph.out_edges(ip_node) if v.startswith("user:")}
        if len(targets) >= 3:
            self._last_signal_time["lateral_movement"] = time.time()
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.SUSPICIOUS_LOGIN,
                user=log.user,
                severity=Severity.CRITICAL,
                events=[log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "lateral_movement",
                    "ip": log.ip,
                    "targets": list(targets),
                    "confidence": 90,
                    "risk_reason": (
                        f"IP {log.ip} connected to {len(targets)} distinct users "
                        f"in {self._window // 60} minutes"
                    ),
                },
            )
        return None

    def _check_coordinated_probe(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """3+ distinct IPs targeting the same user."""
        if not self._cooldown_ok("coordinated_probe"):
            return None
        user_node = f"user:{log.user}"
        if user_node not in self._graph:
            return None
        sources = {u for u, _ in self._graph.in_edges(user_node) if u.startswith("ip:")}
        if len(sources) >= 3:
            self._last_signal_time["coordinated_probe"] = time.time()
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.BRUTE_FORCE,
                user=log.user,
                severity=Severity.HIGH,
                events=[log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "coordinated_probe",
                    "source_ips": list(sources),
                    "confidence": 82,
                    "risk_reason": (
                        f"{len(sources)} distinct IPs targeting user {log.user} "
                        f"in {self._window // 60} minutes"
                    ),
                },
            )
        return None

    def _check_hub_asset_pressure(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """3+ distinct users accessing the same asset."""
        if not log.asset:
            return None
        if not self._cooldown_ok("hub_asset_pressure"):
            return None
        asset_node = f"asset:{log.asset}"
        if asset_node not in self._graph:
            return None
        accessors = {u for u, _ in self._graph.in_edges(asset_node) if u.startswith("user:")}
        if len(accessors) >= 3:
            self._last_signal_time["hub_asset_pressure"] = time.time()
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.ANOMALOUS_ACCESS,
                user=log.user,
                severity=Severity.HIGH,
                events=[log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "hub_asset_pressure",
                    "asset": log.asset,
                    "accessing_users": list(accessors),
                    "confidence": 78,
                    "risk_reason": (
                        f"{len(accessors)} distinct users accessed asset {log.asset} "
                        f"in {self._window // 60} minutes"
                    ),
                },
            )
        return None

    def _check_ip_reuse(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Same IP shared by 2+ distinct users."""
        if not self._cooldown_ok("ip_reuse"):
            return None
        ip_node = f"ip:{log.ip}"
        if ip_node not in self._graph:
            return None
        sharing = {v for _, v in self._graph.out_edges(ip_node) if v.startswith("user:")}
        if len(sharing) >= 2:
            self._last_signal_time["ip_reuse"] = time.time()
            return DetectionSignal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.SUSPICIOUS_LOGIN,
                user=log.user,
                severity=Severity.HIGH,
                events=[log],
                detected_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "pattern": "ip_reuse",
                    "ip": log.ip,
                    "users": list(sharing),
                    "confidence": 72,
                    "risk_reason": (
                        f"IP {log.ip} shared by {len(sharing)} distinct users "
                        f"in {self._window // 60} minutes"
                    ),
                },
            )
        return None

    def update(self, log: SecurityLog) -> Optional[DetectionSignal]:
        """Update the graph from this event. Return highest-severity signal if a pattern fires."""
        if not self._available:
            return None

        with self._lock:
            self._prune_old_edges()

            ip_node = f"ip:{log.ip}"
            user_node = f"user:{log.user}"

            if log.event_type in ("failed_login", "successful_login", "new_country_login"):
                self._add_edge(ip_node, user_node)

            if log.event_type in ("data_download", "privilege_escalation") and log.asset:
                self._add_edge(user_node, f"asset:{log.asset}")

            candidates = []
            for check_fn in (
                self._check_lateral_movement,
                self._check_coordinated_probe,
                self._check_hub_asset_pressure,
                self._check_ip_reuse,
            ):
                sig = check_fn(log)
                if sig:
                    candidates.append(sig)

        if not candidates:
            return None
        _rank = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
        return min(candidates, key=lambda s: _rank.get(s.severity, 99))


# Global detection engine instance
detection_engine = DetectionEngine()
