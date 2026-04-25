# Arceux SOC — API Reference

**Base URL:** `http://localhost:8000`  
**Last Updated:** 2026-04-25

Interactive docs available at: `http://localhost:8000/docs`

---

## Log Ingestion

### `POST /logs`
Ingest a security log event. Runs the detection engine synchronously.

**Request body:**
```json
{
  "timestamp": "2026-04-25T12:01:22Z",
  "user": "alice.kumar@company.com",
  "event_type": "FAILED_LOGIN",
  "ip": "91.203.12.4",
  "location": "Russia",
  "asset": "customer-db"
}
```

`event_type` values: `LOGIN_ATTEMPT`, `FAILED_LOGIN`, `PRIVILEGE_ESCALATION`, `DATA_ACCESS`, `FILE_TRANSFER`, `LOGOUT`

**Response (no detection):**
```json
{ "status": "ok" }
```

**Response (detection triggered):**
```json
{
  "status": "detected",
  "signal_type": "SUSPICIOUS_LOGIN",
  "signal_id": "uuid"
}
```

---

## Alerts

### `GET /alerts`
Fetch all alerts, newest last.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `severity` | string | Filter by `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `limit` | int | Max number of alerts to return (default 100) |

**Response:** Array of Alert objects (see schema below).

---

### `GET /alerts/{alert_id}`
Fetch a single alert by ID.

**Response:** Alert object or `404`.

---

### `PATCH /alerts/{alert_id}/status`
Update alert status.

**Request body:**
```json
{ "status": "investigating" }
```

`status` values: `open`, `investigating`, `resolved`

**Response:** Updated Alert object.

---

### Alert Schema

```json
{
  "alert_id": "uuid",
  "timestamp": "2026-04-25T12:05:00Z",
  "user": "alice.kumar@company.com",
  "threat_type": "SUSPICIOUS_LOGIN",
  "severity": "HIGH",
  "explanation": "User logged in from Russia for the first time...",
  "recommendation": "Verify user identity and reset credentials",
  "agent_trace": [
    "Orchestrator Agent",
    "Alert Handler Agent",
    "Threat Analyzer Agent",
    "Root Cause Agent",
    "Compliance Agent",
    "Response Automation Agent"
  ],
  "raw_events": [...],
  "metadata": {
    "signal_id": "uuid",
    "agent_success": true,
    "notes": [
      { "text": "[ACTION] IP 91.203.12.4 blocked at ...", "timestamp": "..." }
    ]
  },
  "status": "open"
}
```

---

## Actions

### `POST /actions/execute`
Execute a security response action against an alert.

**Request body:**
```json
{
  "action_type": "block_ip",
  "alert_id": "uuid",
  "parameters": {}
}
```

`action_type` values:
- `block_ip` — Adds source IP to `storage.blocked_ips`, appends timestamped note to alert
- `reset_credentials` — Adds user to `storage.flagged_users`, appends note to alert
- Any other string — Logged generically and returns success

**Response:**
```json
{
  "success": true,
  "message": "IP 91.203.12.4 has been blocked. Network team notified.",
  "action_type": "block_ip"
}
```

---

## Agents

### `GET /agents/status`
Get the current state of all 6 AI agents.

**Response:** Array of AgentState objects:
```json
[
  {
    "name": "Orchestrator Agent",
    "status": "completed",
    "last_run": "2026-04-25T12:10:00Z",
    "tasks_completed": 3,
    "execution_count": 3,
    "total_execution_time_ms": 45000,
    "avg_execution_time_ms": 15000,
    "last_execution_trace": [
      "Incident analysis for user alice.kumar",
      "MITRE T1078 Valid Accounts identified",
      "..."
    ]
  },
  ...
]
```

`status` values: `idle`, `running`, `completed`, `error`

---

### `POST /agents/trigger`
Queue the agent pipeline to run on the most recent alert's context. Creates a synthetic `DetectionSignal` and adds it to the processing queue. The background processor picks it up within 5 seconds.

**Response:**
```json
{
  "success": true,
  "message": "Pipeline queued for user 'alice.kumar'. Updates visible in ~5 s."
}
```

Returns `success: false` if:
- No alerts exist yet in the system
- A pipeline run is already in progress

---

## Metrics

### `GET /metrics`
Get system-wide metrics summary.

**Response:**
```json
{
  "total_logs": 1240,
  "total_alerts": 18,
  "alerts_by_severity": {
    "LOW": 2,
    "MEDIUM": 5,
    "HIGH": 8,
    "CRITICAL": 3
  },
  "recent_activity": [...]
}
```

---

### `GET /metrics/realtime`
Get real-time component health and latency for the dashboard heartbeat visualization.

**Response:**
```json
{
  "timestamp": "2026-04-25T12:15:00Z",
  "components": [
    {
      "id": "1",
      "name": "Log Collector",
      "status": "healthy",
      "latency": 47,
      "history": [42, 51, 48, 45, 50, 44, 47, 53, 46, 47],
      "activity": 85
    },
    ...
  ],
  "summary": {
    "total_logs": 85,
    "total_alerts": 18,
    "pending_signals": 0
  }
}
```

Components: `Log Collector`, `Threat Intelligence`, `SIEM Engine`, `Alert Pipeline`, `Analytics Engine`, `Database`

`status` values: `healthy`, `degraded`, `down`

---

## Chat

### `POST /chat`
Send a message to the AI analyst chatbot (Groq `llama-3.3-70b-versatile`).

**Request body:**
```json
{
  "message": "What should I do about the latest alert?",
  "quick_action": null
}
```

Or for a quick action (omit `message`):
```json
{
  "message": "",
  "quick_action": "threat_summary"
}
```

`quick_action` values: `explain_last`, `threat_summary`, `recommend_actions`, `system_status`

**Response:**
```json
{
  "response": "## Current Threat Landscape\n\n...",
  "timestamp": "2026-04-25T12:15:00Z",
  "context_used": true
}
```

---

## Health

### `GET /health`
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "arceux-soc-backend",
  "timestamp": "2026-04-25T12:15:00Z"
}
```

---

## Debug Endpoints (POC Only)

### `GET /debug/logs?limit=50`
Return the most recent ingested logs.

### `GET /debug/signals`
Return all detection signals and their processed status.

### `POST /debug/clear`
Clear all logs, signals, and alerts from storage.

```json
{ "status": "cleared" }
```
