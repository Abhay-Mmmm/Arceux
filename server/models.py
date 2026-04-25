"""
Data Models for Arxis SOC

Pydantic models defining the shape of data flowing through the system.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    """Security event types."""
    SUCCESSFUL_LOGIN = "successful_login"
    FAILED_LOGIN = "failed_login"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_DOWNLOAD = "data_download"
    NEW_COUNTRY_LOGIN = "new_country_login"


class SecurityLog(BaseModel):
    """Incoming security log from log generator."""
    timestamp: str
    user: str
    event_type: EventType
    ip: str
    location: str
    asset: str


class Severity(str, Enum):
    """Alert severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalType(str, Enum):
    """Detection signal types."""
    BRUTE_FORCE = "BRUTE_FORCE"
    SUSPICIOUS_LOGIN = "SUSPICIOUS_LOGIN"
    INSIDER_THREAT = "INSIDER_THREAT"
    ANOMALOUS_ACCESS = "ANOMALOUS_ACCESS"


class DetectionSignal(BaseModel):
    """Output from detection engine."""
    signal_id: str
    signal_type: SignalType
    user: str
    severity: Severity
    events: List[SecurityLog]
    detected_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ThreatAnalysis(BaseModel):
    """Output from Threat Analyst Agent."""
    threat_type: str
    confidence: str
    indicators: List[str]
    severity_justification: str


class ContextEnrichment(BaseModel):
    """Output from Context Enrichment Agent."""
    user_baseline: str
    deviation_summary: str
    risk_factors: List[str]
    historical_notes: str


class Alert(BaseModel):
    """Final alert structure stored and served to frontend."""
    alert_id: str
    timestamp: str
    user: str
    threat_type: str
    severity: Severity
    explanation: str
    recommendation: str
    agent_trace: List[str]
    raw_events: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricsSummary(BaseModel):
    """System metrics for dashboard."""
    total_logs: int
    total_alerts: int
    alerts_by_severity: Dict[str, int]
    recent_activity: List[Dict[str, Any]]
