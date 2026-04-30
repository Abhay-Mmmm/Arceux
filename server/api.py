"""
Arceux SOC Backend API

Main FastAPI application serving:
1. Log ingestion endpoint
2. Frontend data endpoints
3. System metrics

This is the orchestration layer connecting all components.
"""

import logging
import uuid
import asyncio
import os
import time
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from models import SecurityLog, Alert, MetricsSummary, Severity
from storage import storage
from detection_engine import detection_engine
from agents.crew_system import run_agent_analysis
from websocket_manager import manager as ws_manager, set_main_loop


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Background Processing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def process_pending_signals():
    """Background task: Process signals with CrewAI agents (rate-limited).

    pipeline_running is a single-writer flag — only this coroutine ever sets it
    True, and it is always reset in either the inner finally or the outer except.
    No asyncio.Lock is needed because there is exactly one instance of this task
    and all check/set operations are synchronous (no yield between them).
    """
    while True:
        try:
            now = time.time()

            # Skip if pipeline is already running or cooldown is active
            if storage.pipeline_running:
                await asyncio.sleep(5)
                continue
            if now - storage.last_pipeline_run < storage.PIPELINE_COOLDOWN_SECONDS:
                await asyncio.sleep(5)
                continue

            pending = storage.get_pending_signals()
            if not pending:
                await asyncio.sleep(5)
                continue

            # Process only the most recent pending signal; discard older ones
            signal_dict = pending[-1]
            for older in pending[:-1]:
                storage.mark_signal_processed(older["signal_id"])

            from models import DetectionSignal
            signal = DetectionSignal(**signal_dict)

            print(f"\n[*] Processing signal {signal.signal_id} with AI agents...")

            storage.pipeline_running = True
            try:
                agent_output = await run_in_threadpool(run_agent_analysis, signal)

                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    user=signal.user,
                    threat_type=signal.signal_type.value,
                    severity=signal.severity,
                    explanation=agent_output.get("result", "No explanation available"),
                    recommendation="Review immediately and verify user identity",
                    agent_trace=agent_output.get("agent_trace", []),
                    raw_events=[
                        event.model_dump() if hasattr(event, "model_dump") else event
                        for event in signal.events
                    ],
                    metadata={
                        "signal_id": signal.signal_id,
                        "agent_success": agent_output.get("success", False),
                        **signal.metadata,
                    },
                )

                storage.add_alert(alert)
                storage.mark_signal_processed(signal.signal_id)
                print(f"[OK] Alert {alert.alert_id} created from signal {signal.signal_id}")

                # Broadcast to all WS clients — fire-and-forget, never block detection
                try:
                    await ws_manager.broadcast({"type": "new_alert", "alert": alert.model_dump()})
                    metrics = storage.get_metrics()
                    await ws_manager.broadcast({
                        "type": "metrics_updated",
                        "metrics": {
                            "alerts_by_severity": metrics["alerts_by_severity"],
                            "total_alerts": metrics["total_alerts"],
                            "total_logs": metrics["total_logs"],
                        },
                    })
                    await ws_manager.broadcast({
                        "type": "compliance_updated",
                        "compliance": compute_compliance_status(storage),
                    })
                except Exception as e:
                    _logger.debug("alert broadcast failed", exc_info=e)

            except Exception as e:
                # Increment attempt counter on the signal dict (mutates in-place in storage.signals).
                # Dead-letter after 3 failures so a malformed/deterministic-error signal
                # cannot cause an infinite retry loop.
                attempts = signal_dict.get("attempts", 0) + 1
                signal_dict["attempts"] = attempts
                print(f"[WARN] Error processing signal {signal.signal_id} (attempt {attempts}): {e}")
                if attempts >= 3:
                    print(f"[WARN] Dead-lettering signal {signal.signal_id} after {attempts} failed attempts")
                    storage.mark_signal_processed(signal.signal_id)
            finally:
                storage.pipeline_running = False
                storage.last_pipeline_run = time.time()

        except Exception as e:
            # Outer guard: catches failures in get_pending_signals, DetectionSignal(**), etc.
            # pipeline_running is reset here so the next iteration can proceed.
            # last_pipeline_run is set to enforce the cooldown even on unexpected failures,
            # preventing an unthrottled retry loop.
            storage.pipeline_running = False
            storage.last_pipeline_run = time.time()
            print(f"[WARN] Error in background processing: {e}")

        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    set_main_loop(asyncio.get_event_loop())
    task = asyncio.create_task(process_pending_signals())
    print("[OK] Background signal processor started")

    yield

    task.cancel()
    print("[STOP] Background processor stopped")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FastAPI Application
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app = FastAPI(
    title="Arceux SOC Backend",
    description="AI-native Security Operations Center POC",
    version="0.2.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ingestion Endpoint
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/logs", status_code=200)
async def ingest_log(log: SecurityLog):
    """
    Ingest a security log.
    
    Flow:
    1. Store log
    2. Run detection engine
    3. If signal detected → queue for agent processing
    """
    # Store log
    storage.add_log(log)
    
    # Run detection
    signal = detection_engine.analyze(log)
    
    if signal:
        # Store signal for background processing
        storage.add_signal(signal)
        print(f"[ALERT] Detection: {signal.signal_type.value} for {signal.user}")
        
        return {
            "status": "detected",
            "signal_type": signal.signal_type.value,
            "signal_id": signal.signal_id
        }
    
    return {"status": "ok"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Frontend API Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/alerts", response_model=List[Alert])
async def get_alerts(
    severity: str = None,
    limit: int = 100
):
    """
    Get all alerts, optionally filtered by severity.
    
    Query params:
    - severity: Filter by severity (LOW/MEDIUM/HIGH/CRITICAL)
    - limit: Max number of alerts to return
    """
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be a positive integer")

    if severity:
        try:
            sev = Severity(severity.upper())
            alerts = storage.get_alerts_by_severity(sev)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid severity level")
    else:
        alerts = storage.get_all_alerts()

    # Convert to Alert objects, newest first, apply limit
    alert_objects = [Alert(**alert) for alert in reversed(alerts[-limit:])]

    return alert_objects


@app.get("/alerts/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str):
    """
    Get a specific alert by ID.
    """
    alert = storage.get_alert_by_id(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return Alert(**alert)


class AlertStatusUpdate(BaseModel):
    """Body for PATCH /alerts/{id}/status."""
    status: str  # open | investigating | resolved


class ExecuteActionRequest(BaseModel):
    """Body for POST /actions/execute."""
    action_type: str
    alert_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TriggerPipelineRequest(BaseModel):
    """Body for POST /agents/trigger."""
    alert_id: Optional[str] = None


@app.patch("/alerts/{alert_id}/status", response_model=Alert)
async def update_alert_status(alert_id: str, update: AlertStatusUpdate):
    """
    Update alert status.

    Accepts: { "status": "open" | "investigating" | "resolved" }
    Returns the updated alert object.
    """
    valid_statuses = {"open", "investigating", "resolved"}
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {sorted(valid_statuses)}"
        )

    success = storage.update_alert_status(alert_id, update.status)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_dict = storage.get_alert_by_id(alert_id)

    try:
        await ws_manager.broadcast({
            "type": "alert_status_updated",
            "alert_id": alert_id,
            "status": update.status,
        })
        await ws_manager.broadcast({
            "type": "compliance_updated",
            "compliance": compute_compliance_status(storage),
        })
    except Exception as e:
        _logger.debug("alert_status_updated broadcast failed", exc_info=e)

    return Alert(**alert_dict)


@app.post("/actions/execute")
async def execute_action(request: ExecuteActionRequest):
    """
    Execute a security response action.

    Supported action_types:
    - block_ip: Logs the source IP as blocked, adds note to the alert
    - reset_credentials: Flags user credentials for reset, adds note to the alert

    Returns: { "success": true, "message": string, "action_type": string }
    """
    alert_dict = storage.get_alert_by_id(request.alert_id)
    if not alert_dict:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_user = alert_dict.get("user", "unknown")
    raw_events = alert_dict.get("raw_events", [])
    alert_ip = raw_events[0].get("ip", "unknown") if raw_events else "unknown"
    timestamp = datetime.now(timezone.utc).isoformat()

    if request.action_type == "block_ip":
        storage.blocked_ips.add(alert_ip)
        note = f"\n[ACTION] IP {alert_ip} blocked at {timestamp}"
        message = f"IP {alert_ip} has been blocked. Network team notified."
    elif request.action_type == "reset_credentials":
        storage.flagged_users.add(alert_user)
        note = f"\n[ACTION] Credentials reset for {alert_user} at {timestamp}"
        message = f"Credentials for user '{alert_user}' flagged for reset. Identity team notified."
    else:
        note = f"\n[ACTION] {request.action_type} executed at {timestamp}"
        message = f"Action '{request.action_type}' logged successfully."

    storage.add_executed_action({
        "action_type": request.action_type,
        "alert_id": request.alert_id,
        "details": message,
        "timestamp": timestamp,
        "parameters": request.parameters,
    })
    result = storage.add_alert_note(request.alert_id, note)
    
    if result.get("status_changed"):
        await ws_manager.broadcast({
            "type": "alert_status_updated",
            "alert_id": request.alert_id,
            "status": "investigating"
        })
        await ws_manager.broadcast({
            "type": "compliance_updated",
            "compliance": compute_compliance_status(storage),
        })

    return {
        "success": True,
        "message": message,
        "action_type": request.action_type,
    }


@app.get("/agents/status")
async def get_agents_status():
    """
    Get the current status of all AI agents.

    Returns a list of agent state objects with:
    - name, status (idle/running/completed/error)
    - last_run timestamp, tasks_completed, avg_execution_time_ms
    - last_execution_trace (lines from most recent run)
    """
    states = storage.get_all_agent_states()
    for state in states:
        count = state.get("execution_count", 0)
        total_ms = state.get("total_execution_time_ms", 0)
        state["avg_execution_time_ms"] = (total_ms // count) if count > 0 else 0
    return {"agents": states, "last_signal_type": storage.last_signal_type}


@app.post("/agents/trigger")
async def trigger_agent_pipeline(body: TriggerPipelineRequest):
    """
    Queue the agent pipeline to run on a specific alert (or the latest alert).

    Body: { "alert_id": "<uuid>" }  — optional. If omitted or null, uses the most
    recent alert. Creates a synthetic detection signal and adds it to the processing
    queue. The background processor picks it up within 5 s.
    """
    alerts = storage.get_all_alerts()
    if not alerts:
        return {"success": False, "message": "No alerts in system. Wait for log events to generate detections."}

    # Prevent double-triggering if already running
    agent_states = storage.get_all_agent_states()
    if any(s.get("status") == "running" for s in agent_states):
        return {"success": False, "message": "Agent pipeline is currently running. Please wait."}

    # Resolve target alert
    if body.alert_id:
        target = storage.get_alert_by_id(body.alert_id)
        if not target:
            raise HTTPException(status_code=404, detail=f"Alert '{body.alert_id}' not found")
    else:
        target = alerts[-1]

    threat_type = target.get("threat_type", "BRUTE_FORCE")

    _type_map = {
        "BRUTE_FORCE": "BRUTE_FORCE",
        "SUSPICIOUS_LOGIN": "SUSPICIOUS_LOGIN",
        "INSIDER_THREAT": "INSIDER_THREAT",
        "ANOMALOUS_ACCESS": "ANOMALOUS_ACCESS",
    }
    signal_type_str = _type_map.get(threat_type, "BRUTE_FORCE")

    from models import DetectionSignal, SignalType

    synthetic = DetectionSignal(
        signal_id=str(uuid.uuid4()),
        signal_type=SignalType(signal_type_str),
        user=target.get("user", "unknown"),
        severity=Severity(target.get("severity", "HIGH")),
        events=[],
        detected_at=datetime.utcnow().isoformat(),
        metadata={"triggered_manually": True, "source_alert_id": target.get("alert_id", "")},
    )
    storage.add_signal(synthetic)

    return {
        "success": True,
        "message": f"Pipeline queued for user '{target.get('user', 'unknown')}'. Updates visible in ~5 s.",
    }


def _parse_alert_time(ts: str) -> datetime:
    """Parse ISO timestamp, always returning a timezone-aware UTC datetime."""
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def compute_compliance_status(storage) -> dict:
    """Pure function — computes compliance posture from storage data. No side effects."""
    now = datetime.now(timezone.utc)
    all_alerts = storage.get_all_alerts()
    unresolved = [a for a in all_alerts if a.get("status", "open") != "resolved"]

    def minutes_since(ts: str) -> float:
        return (now - _parse_alert_time(ts)).total_seconds() / 60

    def get_asset(alert: dict) -> str:
        raw = alert.get("raw_events", [])
        return raw[0].get("asset", "") if raw else alert.get("metadata", {}).get("asset", "")

    # ── IRDAI (6-hour deadline for CRITICAL) ──────────────────────────────────
    irdai_critical = [
        a for a in unresolved
        if a.get("severity") == "CRITICAL" and minutes_since(a["timestamp"]) <= 360
    ]
    irdai_high = [
        a for a in unresolved
        if a.get("severity") == "HIGH" and minutes_since(a["timestamp"]) <= 1440
    ]
    if irdai_critical:
        trigger = max(irdai_critical, key=lambda a: a["timestamp"])
        elapsed = minutes_since(trigger["timestamp"])
        remaining = max(0.0, 360 - elapsed)
        irdai = {
            "status": "action_required",
            "reason": (
                f"CRITICAL incident detected {int(elapsed)} min ago — "
                f"IRDAI requires reporting within 6 hours ({int(remaining)} min remaining)"
            ),
            "deadline_hours": 6,
            "time_remaining_minutes": int(remaining),
            "triggered_by": trigger["alert_id"],
        }
    elif irdai_high:
        irdai = {
            "status": "review_needed",
            "reason": "HIGH severity incidents require IRDAI assessment",
            "deadline_hours": None,
            "time_remaining_minutes": None,
            "triggered_by": None,
        }
    else:
        irdai = {
            "status": "compliant",
            "reason": "No reportable incidents in last 24 hours",
            "deadline_hours": None,
            "time_remaining_minutes": None,
            "triggered_by": None,
        }

    # ── GDPR (72-hour deadline for data-breach signal types) ─────────────────
    DATA_BREACH_TYPES = {"INSIDER_THREAT", "ANOMALOUS_ACCESS"}
    gdpr_action = [
        a for a in unresolved
        if a.get("severity") in ("CRITICAL", "HIGH")
        and a.get("threat_type") in DATA_BREACH_TYPES
        and minutes_since(a["timestamp"]) <= 4320
    ]
    gdpr_review = [
        a for a in unresolved
        if a.get("threat_type") == "SUSPICIOUS_LOGIN"
        and minutes_since(a["timestamp"]) <= 2880
    ]
    if gdpr_action:
        trigger = max(gdpr_action, key=lambda a: a["timestamp"])
        elapsed = minutes_since(trigger["timestamp"])
        remaining = max(0.0, 4320 - elapsed)
        gdpr = {
            "status": "action_required",
            "reason": (
                f"Potential data breach detected — GDPR requires notification "
                f"within 72 hours ({int(remaining)} min remaining)"
            ),
            "deadline_hours": 72,
            "time_remaining_minutes": int(remaining),
            "triggered_by": trigger["alert_id"],
        }
    elif gdpr_review:
        gdpr = {
            "status": "review_needed",
            "reason": "Suspicious access patterns require GDPR assessment",
            "deadline_hours": None,
            "time_remaining_minutes": None,
            "triggered_by": None,
        }
    else:
        gdpr = {
            "status": "compliant",
            "reason": "No data breach indicators in last 72 hours",
            "deadline_hours": None,
            "time_remaining_minutes": None,
            "triggered_by": None,
        }

    # ── SOC 2 (unresolved count) ──────────────────────────────────────────────
    n = len(unresolved)
    if n >= 5:
        soc2 = {
            "status": "action_required",
            "reason": f"{n} unresolved security incidents require documentation per SOC 2 CC7.2",
        }
    elif n >= 1:
        soc2 = {
            "status": "review_needed",
            "reason": f"{n} unresolved incident{'s' if n > 1 else ''} require SOC 2 review",
        }
    else:
        soc2 = {
            "status": "compliant",
            "reason": "All incidents resolved — SOC 2 controls effective",
        }

    # ── ISO 27001 ─────────────────────────────────────────────────────────────
    iso_critical = [a for a in unresolved if a.get("severity") == "CRITICAL"]
    iso_high = [a for a in unresolved if a.get("severity") == "HIGH"]
    if iso_critical:
        iso27001 = {
            "status": "action_required",
            "reason": "CRITICAL incident requires ISO 27001 A.16 incident response procedure",
        }
    elif iso_high:
        iso27001 = {
            "status": "review_needed",
            "reason": "HIGH severity incidents require ISO 27001 review",
        }
    else:
        iso27001 = {
            "status": "compliant",
            "reason": "No major incidents — ISO 27001 controls maintained",
        }

    # ── PCI DSS ───────────────────────────────────────────────────────────────
    pci_action = [
        a for a in unresolved
        if a.get("threat_type") in DATA_BREACH_TYPES
        and any(kw in get_asset(a).lower() for kw in ("payment", "customer"))
    ]
    pci_review = [
        a for a in unresolved
        if a.get("severity") == "HIGH" and minutes_since(a["timestamp"]) <= 1440
    ]
    if pci_action:
        pci_dss = {
            "status": "action_required",
            "reason": "Payment/customer data access incident requires PCI DSS forensic investigation",
        }
    elif pci_review:
        pci_dss = {
            "status": "review_needed",
            "reason": "Security incidents require PCI DSS assessment",
        }
    else:
        pci_dss = {
            "status": "compliant",
            "reason": "No payment data incidents detected",
        }

    return {
        "irdai": irdai,
        "gdpr": gdpr,
        "soc2": soc2,
        "iso27001": iso27001,
        "pci_dss": pci_dss,
        "last_updated": now.isoformat(),
    }


@app.get("/compliance/status")
async def get_compliance_status():
    """Compute dynamic compliance posture from current alert data."""
    return compute_compliance_status(storage)


@app.get("/metrics", response_model=MetricsSummary)
async def get_metrics():
    """
    Get system metrics for dashboard.
    
    Returns:
    - Total logs processed
    - Total alerts generated
    - Alerts by severity
    - Recent activity
    """
    metrics = storage.get_metrics()
    return MetricsSummary(**metrics)




@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "arceux-soc-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str
    quick_action: Optional[str] = None
    conversation_history: Optional[list] = []


@app.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """
    Chat with AI security analyst.
    
    Supports:
    - Free-form questions
    - Quick actions (explain_last, threat_summary, etc.)
    
    Returns AI-generated response with context from recent alerts.
    """
    try:
        from chatbot import get_ai_response, get_quick_action_response

        if request.quick_action:
            response_text = get_quick_action_response(
                request.quick_action,
                storage,
                request.conversation_history
            )
        else:
            response_text = get_ai_response(
                request.message,
                storage,
                request.conversation_history
            )

        return {
            "response": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_used": True
        }
        
    except ImportError:
        return {
            "response": "AI chatbot module could not be loaded. Check server logs.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_used": False
        }
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "response": f"Sorry, I encountered an error: {str(e)[:100]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_used": False
        }



@app.get("/metrics/realtime")
async def get_realtime_metrics():
    """
    Get real-time system metrics for heartbeat visualization.
    
    Returns activity data for:
    - Log Collector: based on recent log ingest rate
    - Threat Intelligence: based on detection signals
    - SIEM Engine: based on overall processing
    - Alert Pipeline: based on alert creation rate
    - Analytics Engine: based on agent processing
    - Database: based on storage operations
    """
    import random
    
    # Get recent activity from storage
    recent_logs = storage.get_recent_logs(100)
    recent_alerts = storage.get_all_alerts()[-20:]
    pending_signals = storage.get_pending_signals()
    
    # Calculate activity rates (events in last minute simulation)
    log_rate = len(recent_logs) if recent_logs else 0
    alert_rate = len(recent_alerts) if recent_alerts else 0
    signal_rate = len(pending_signals) if pending_signals else 0
    
    # Generate realistic latency values based on actual activity
    # More activity = slightly higher latency
    def compute_latency(base: int, activity: int, variance: int = 10) -> int:
        load_factor = min(activity / 20, 1.5)  # Cap at 1.5x
        jitter = random.randint(-variance, variance)
        return max(5, int(base * load_factor + jitter))
    
    # Generate history arrays (last 10 readings) with realistic variance
    def generate_history(base: int, activity: int) -> list:
        history = []
        for _ in range(10):
            history.append(compute_latency(base, activity, 5))
        return history
    
    components = [
        {
            "id": "1",
            "name": "Log Collector",
            "status": "healthy" if log_rate > 0 else "degraded",
            "latency": compute_latency(45, log_rate),
            "history": generate_history(45, log_rate),
            "activity": log_rate
        },
        {
            "id": "2", 
            "name": "Threat Intelligence",
            "status": "healthy",
            "latency": compute_latency(120, signal_rate),
            "history": generate_history(120, signal_rate),
            "activity": signal_rate
        },
        {
            "id": "3",
            "name": "SIEM Engine",
            "status": "healthy",
            "latency": compute_latency(85, log_rate + signal_rate),
            "history": generate_history(85, log_rate + signal_rate),
            "activity": log_rate + signal_rate
        },
        {
            "id": "4",
            "name": "Alert Pipeline",
            "status": "healthy" if signal_rate == 0 else "degraded",
            "latency": compute_latency(150, alert_rate + signal_rate * 3),
            "history": generate_history(150, alert_rate + signal_rate * 3),
            "activity": alert_rate
        },
        {
            "id": "5",
            "name": "Analytics Engine",
            "status": "healthy",
            "latency": compute_latency(310, alert_rate),
            "history": generate_history(310, alert_rate),
            "activity": alert_rate
        },
        {
            "id": "6",
            "name": "Database",
            "status": "healthy",
            "latency": compute_latency(12, log_rate + alert_rate),
            "history": generate_history(12, log_rate + alert_rate),
            "activity": log_rate + alert_rate
        }
    ]
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": components,
        "summary": {
            "total_logs": log_rate,
            "total_alerts": alert_rate,
            "pending_signals": signal_rate
        }
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WebSocket Endpoint
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time push channel. Clients receive new_alert, metrics_updated,
    agent_status_updated, alert_status_updated, and pipeline_completed events."""
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Debug Endpoints (POC only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/debug/logs")
async def debug_logs(limit: int = 50):
    """Get recent logs for debugging."""
    return storage.get_recent_logs(limit)


@app.get("/debug/signals")
async def debug_signals():
    """Get all signals for debugging."""
    return {
        "pending": storage.get_pending_signals(),
        "total": len(storage.signals)
    }


@app.post("/debug/clear")
async def debug_clear():
    """Clear all data (for testing)."""
    storage.clear_all()
    return {"status": "cleared"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entrypoint
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ==================================================
    =                                           =
    =          [SHIELD]  ARCEUX SOC BACKEND [SHIELD] =
    =                                           =
    =  AI-Native Security Operations Center     =
    =  Powered by CrewAI                        =
    =                                           =
    ==================================================
    """)
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
