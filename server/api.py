"""
Arxis SOC Backend API

Main FastAPI application serving:
1. Log ingestion endpoint
2. Frontend data endpoints
3. System metrics

This is the orchestration layer connecting all components.
"""

import uuid
import asyncio
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from models import SecurityLog, Alert, MetricsSummary, Severity
from storage import storage
from detection_engine import detection_engine
from agents.crew_system import run_agent_analysis


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Background Processing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def process_pending_signals():
    """Background task: Process signals with CrewAI agents."""
    while True:
        try:
            pending = storage.get_pending_signals()
            
            for signal_dict in pending:
                # Convert to DetectionSignal object
                from models import DetectionSignal
                signal = DetectionSignal(**signal_dict)
                
                print(f"\n🤖 Processing signal {signal.signal_id} with AI agents...")
                
                # Run agent analysis in threadpool to avoid blocking event loop
                agent_output = await run_in_threadpool(run_agent_analysis, signal)
                
                # Parse agent output into alert
                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    user=signal.user,
                    threat_type=signal.signal_type.value,
                    severity=signal.severity,
                    explanation=agent_output.get("result", "No explanation available"),
                    recommendation="Review immediately and verify user identity",
                    agent_trace=agent_output.get("agent_trace", []),
                    raw_events=[event.model_dump() if hasattr(event, 'model_dump') else event 
                               for event in signal.events],
                    metadata={
                        "signal_id": signal.signal_id,
                        "agent_success": agent_output.get("success", False),
                        **signal.metadata
                    }
                )
                
                # Store alert
                storage.add_alert(alert)
                storage.mark_signal_processed(signal.signal_id)
                
                print(f"✅ Alert {alert.alert_id} created from signal {signal.signal_id}")
        
        except Exception as e:
            print(f"⚠️  Error in background processing: {e}")
        
        # Check every 5 seconds
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Start background task for processing signals
    task = asyncio.create_task(process_pending_signals())
    print("✅ Background signal processor started")
    
    yield
    
    # Shutdown
    task.cancel()
    print("🛑 Background processor stopped")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FastAPI Application
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app = FastAPI(
    title="Arxis SOC Backend",
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
        print(f"🚨 Detection: {signal.signal_type.value} for {signal.user}")
        
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
    if severity:
        try:
            sev = Severity(severity.upper())
            alerts = storage.get_alerts_by_severity(sev)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid severity level")
    else:
        alerts = storage.get_all_alerts()
    
    # Convert to Alert objects and apply limit
    alert_objects = [Alert(**alert) for alert in alerts[-limit:]]
    
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
        "service": "arxis-soc-backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str
    quick_action: Optional[str] = None  # 'explain_last', 'threat_summary', etc.


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
        
        # Gather context
        alerts = storage.get_all_alerts()
        context = {}
        
        
        if alerts:
            # Get last alert with full details
            last_alert_dict = alerts[-1]
            
            # Extract asset from raw_events or metadata
            asset = "unknown"
            if last_alert_dict.get("raw_events") and len(last_alert_dict["raw_events"]) > 0:
                asset = last_alert_dict["raw_events"][0].get("asset", "unknown")
            elif last_alert_dict.get("metadata"):
                asset = last_alert_dict["metadata"].get("asset", "unknown")
            
            context["last_alert"] = {
                "title": last_alert_dict.get("threat_type", "Unknown").replace("_", " ").title(),
                "severity": last_alert_dict.get("severity", "UNKNOWN"),
                "user": last_alert_dict.get("user", "unknown"),
                "asset": asset,
                "description": last_alert_dict.get("explanation", "No description")
            }
            
            # Get recent alerts (last 10)
            recent_alerts = []
            for alert_dict in alerts[-10:]:
                alert_asset = "unknown"
                if alert_dict.get("raw_events") and len(alert_dict["raw_events"]) > 0:
                    alert_asset = alert_dict["raw_events"][0].get("asset", "unknown")
                    
                recent_alerts.append({
                    "title": alert_dict.get("threat_type", "Unknown").replace("_", " ").title(),
                    "severity": alert_dict.get("severity", "UNKNOWN"),
                    "user": alert_dict.get("user", "unknown"),
                    "asset": alert_asset
                })
            context["recent_alerts"] = recent_alerts
            
            # Alert stats
            from collections import Counter
            severity_counts = Counter(a.get("severity") for a in alerts[-20:])
            context["alert_stats"] = {
                "total": len(alerts),
                "critical": severity_counts.get("CRITICAL", 0),
                "high": severity_counts.get("HIGH", 0),
                "medium": severity_counts.get("MEDIUM", 0),
                "low": severity_counts.get("LOW", 0)
            }

        
        # Handle quick action or regular message
        if request.quick_action:
            response_text = get_quick_action_response(request.quick_action, context)
        else:
            response_text = get_ai_response(request.message, context)
        
        return {
            "response": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_used": bool(context)
        }
        
    except ImportError:
        return {
            "response": "AI chatbot is not configured. Please check OpenAI API key.",
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
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║           🛡️  ARXIS SOC BACKEND 🛡️         ║
    ║                                           ║
    ║  AI-Native Security Operations Center     ║
    ║  Powered by CrewAI                        ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
