# Arceux — Implementation Overview

**Version:** 0.4.1 (Day 1 Fixes v2.1 — Bug Fixes & Error Handling)  
**Last Updated:** 2026-04-25  
**Status:** Active Development — Early Prototype

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Vite |
| Styling | TailwindCSS 3.4 + Framer Motion |
| Charts | Recharts 2.9 |
| Routing | React Router DOM 6.18 |
| Backend | FastAPI + Uvicorn (Python) |
| AI Chatbot | Groq API (`groq` SDK, `llama-3.3-70b-versatile`) |
| AI Agents | CrewAI + LangChain + `langchain-groq` (Groq) |
| Storage | In-memory + JSON file persistence |
| Async | Python asyncio + threading |

---

## Project Structure

```
Arceux/
├── client/                        # React frontend
│   └── src/
│       ├── pages/                 # Dashboard, Alerts, AgentInsights
│       ├── components/            # Badge, Button, Card, Modal
│       ├── services/api.ts        # API layer + useAlerts hook
│       ├── data/mock.ts           # Mock data for offline fallback
│       └── types.ts               # TypeScript interfaces
├── server/                        # Python FastAPI backend
│   ├── api.py                     # All API endpoints
│   ├── main.py                    # Orchestrator/entry point
│   ├── chatbot.py                 # Groq chatbot + template fallback
│   ├── agents/crew_system.py      # CrewAI 6-agent system (Groq LLM)
│   ├── detection_engine.py        # Rule-based threat detection
│   ├── storage.py                 # Thread-safe in-memory store
│   ├── models.py                  # Pydantic data models
│   └── log_generator.py           # Synthetic log generator
└── artifacts/                     # Design docs and implementation notes
```

---

## Fully Implemented

### Frontend

#### Dashboard (`client/src/pages/Dashboard.tsx`)
- **System Heartbeat Visualization:** SVG-based waveform charts for 6 system components with live latency polling every 2 seconds. Color-coded by health status (green/yellow/red).
- **AI Analyst Chat Panel:** Full chatbot UI with message history, role-based styling, 4 quick-action buttons (Explain last alert, Threat summary, Recommend actions, System status), markdown rendering, and Enter-to-send.
- **Alerts Feed:** Auto-fetches high/critical alerts every 5 seconds; shows severity badges, timestamps, and opens a modal on click.
- **System Metrics Cards:** Threat severity distribution bar chart (Recharts), compliance status badges (SOC 2, ISO 27001, GDPR, IRDAI, PCI DSS).
- **Modal Dialogs:** Alert Intelligence modal (AI trace + recommendations), Service Diagnostics modal (latency history), System Check modal (diagnostic progress).

#### Alerts Page (`client/src/pages/Alerts.tsx`)
- **Alert Table:** Sortable by severity, name, asset/user, confidence, status, timestamp.
- **Filter System:** Cyclic filters for severity and status; real-time search across title, user, asset, description; live filtered/total counter.
- **Take Ownership:** Optimistic UI update → backend `PATCH /alerts/{id}/status` sync. `localModifications` cleared on success, kept as fallback on failure.
- **Execute Actions:** Execute buttons in the detail panel call `POST /actions/execute`. Buttons show spinner during execution, "Done ✓" on success, "Retry" on error, and are disabled after success to prevent double-firing.
- **Detail Slide-Out Panel:** Right-side drawer with full alert details, AI agent trace (numbered timeline), and live-wired recommended action buttons. Smooth slide-in/out animation.
- **Relative Timestamps:** Human-readable ("5 mins ago") with graceful handling of invalid dates.

#### Agent Insights Page (`client/src/pages/AgentInsights.tsx`)
- **Agent Pipeline Visualization:** 6 agents shown as connected boxes with live status indicators (idle/running/completed/error) polled every 3 s.
- **Agent Detail Cards:** Click any agent for expanded detail panel showing last trace, task count, avg execution time, last run timestamp.
- **Run on Latest Alert button:** Calls `POST /agents/trigger` to queue a pipeline run on the most recent alert context.
- **Live Terminal Output:** Each card's terminal shows real `last_execution_trace` lines from the most recent crew run. Running state shows amber cursor animation.
- **CPU/Runs indicator:** Bottom bar shows run count and load bar state based on agent status (idle/running/completed).

#### Layout & Navigation
- Sidebar icon navigation to all 3 pages.
- Hover-activated user profile panel (name, role, ID).
- Full dark theme with CSS custom properties.
- Fade-in animations and hover states throughout.

#### API Service Layer (`client/src/services/api.ts`)
- `fetchAlerts()`, `fetchAlertById()`, `fetchMetrics()`, `fetchRealtimeMetrics()`, `checkHealth()`, `ingestLog()`.
- `updateAlertStatus(alertId, status)` — calls `PATCH /alerts/{id}/status`.
- `executeAction({ action_type, alert_id, parameters })` — calls `POST /actions/execute`.
- `fetchAgentStatus()` — calls `GET /agents/status`.
- `triggerAgentPipeline()` — calls `POST /agents/trigger`.
- Alert transformation: maps backend schema → frontend format, uses backend `status` field.
- `useAlerts()` React hook: polling with configurable interval, loading/error/refetch states.

#### UI Components
- `Badge.tsx` — severity/status variants with color mapping.
- `Button.tsx` — size and variant props.
- `Card.tsx` — container with optional padding.
- `Modal.tsx` — dialog with close handler.

---

### Backend

#### API (`server/api.py`)
| Endpoint | Status |
|----------|--------|
| `POST /logs` | ✅ Log ingestion → detection engine |
| `GET /alerts` | ✅ All alerts, optional severity filter + limit |
| `GET /alerts/{id}` | ✅ Single alert by ID |
| `PATCH /alerts/{id}/status` | ✅ Update alert status (open/investigating/resolved) |
| `POST /actions/execute` | ✅ Execute response action (block_ip, reset_credentials) |
| `GET /agents/status` | ✅ All 6 agent states with stats |
| `POST /agents/trigger` | ✅ Queue pipeline run from latest alert |
| `GET /metrics` | ✅ Summary (totals, by-severity, recent activity) |
| `GET /metrics/realtime` | ✅ Component health + latency history (6 components) |
| `POST /chat` | ✅ Free-form or quick-action chat (Groq + template fallback) |
| `GET /health` | ✅ Basic health check |
| `GET /debug/logs` | ✅ Recent ingested logs |
| `GET /debug/signals` | ✅ Detection signals + processed status |
| `POST /debug/clear` | ✅ Clear all storage |

#### Detection Engine (`server/detection_engine.py`)
Three rule-based detectors, all stateful:
- **BRUTE_FORCE:** >5 failed logins within a 2-minute sliding window per user, tracking unique source IPs.
- **SUSPICIOUS_LOGIN:** Login from a hardcoded set of suspicious locations (Russia, North Korea, Iran, Tor Exit Node, etc.) → HIGH severity.
- **INSIDER_THREAT:** Privilege escalation followed by data download → CRITICAL severity, correlated per user.

#### 6-Agent CrewAI System (`server/agents/crew_system.py`)
Sequential agent pipeline powered by Groq (`llama-3.3-70b-versatile` via `langchain-groq`):

| # | Agent | Role |
|---|-------|------|
| 1 | Orchestrator Agent | Coordinates incident response lifecycle |
| 2 | Alert Handler Agent | Triages and correlates events |
| 3 | Threat Analyzer Agent | MITRE ATT&CK mapping + intent classification |
| 4 | Root Cause Agent | Forensic timeline reconstruction |
| 5 | Compliance Agent | GDPR/IRDAI regulatory evaluation |
| 6 | Response Automation Agent | Remediation planning |

- All agents receive `llm=groq_llm` when `GROQ_API_KEY` is set; fall back to simulated trace otherwise.
- `run_agent_analysis` updates `storage.agent_states` throughout execution: sets all agents to `running` at start, `completed` (with elapsed ms and trace) on success, `error` on failure.
- Entire `run_agent_analysis` wrapped in try/except — never crashes the background processor.
- Background task in `main.py` polls storage every 5 seconds, runs crew on pending signals, creates alerts.

#### Chatbot (`server/chatbot.py`)
- **Live LLM:** Uses Groq API (`groq` SDK, `llama-3.3-70b-versatile`).
- **System prompt:** "Senior SOC analyst with deep threat intelligence expertise" injected as system role into every Groq call.
- **Context injection:** Last 5 alerts as JSON + alert stats included in every user prompt.
- **Quick-action prompts:** Each action type (`explain_last`, `threat_summary`, `recommend_actions`, `system_status`) gets its own focused prompt.
- **Template fallback:** If `GROQ_API_KEY` is not set or any Groq call fails, falls back to data-driven templates — no crash, no empty response.

#### Execute Action Handlers (`server/api.py — POST /actions/execute`)
- **`block_ip`:** Extracts source IP from alert's `raw_events`, adds it to `storage.blocked_ips` (thread-safe set), adds timestamped note to alert metadata.
- **`reset_credentials`:** Adds alert user to `storage.flagged_users` (thread-safe set), adds timestamped note to alert metadata.
- All actions logged in `storage.executed_actions` (thread-safe).
- Unknown action types are logged generically and return success.

#### Agent Status API (`server/api.py`)
| Endpoint | Description |
|----------|-------------|
| `GET /agents/status` | Returns all 6 agent states (status, last_run, tasks_completed, avg_execution_time_ms, last_execution_trace) |
| `POST /agents/trigger` | Queues a synthetic signal from latest alert for background pipeline processing |

#### Storage Layer (`server/storage.py`)
- Thread-safe in-memory collections for logs, signals, alerts, and executed actions.
- JSON file persistence: saves alerts to disk on update, restores on startup.
- `update_alert_status(alert_id, status)` — updates alert status field and persists.
- `add_alert_note(alert_id, note)` — appends a note to `alert.metadata.notes`.
- `add_executed_action(action)` — logs executed response actions.
- `blocked_ips: Set[str]` — set of IPs blocked via the execute action handler.
- `flagged_users: Set[str]` — set of users flagged for credential reset.
- `agent_states: Dict[str, Dict]` — per-agent state dict (status, last_run, tasks_completed, execution_count, total_execution_time_ms, last_execution_trace).
- `update_agent_state(name, updates)` — thread-safe partial update of agent state.
- `get_all_agent_states()` — returns snapshot list of all 6 agent state dicts.
- Lock-based synchronization for all concurrent access.

#### Data Models (`server/models.py`)
`EventType`, `SecurityLog`, `Severity`, `SignalType`, `DetectionSignal`, `Alert`, `MetricsSummary`, `ThreatAnalysis`, `ContextEnrichment` — all Pydantic models.  
`Alert` now includes `status: str = "open"` field (open | investigating | resolved).

#### Log Generator (`server/log_generator.py`)
- Synthetic realistic logs: 6 users, 6 asset types, 5 event types with weighted distribution.
- Suspicious-location bias: higher chance of suspicious location on suspicious event types.
- Runs in background thread, POSTs a new log every 1–3 seconds.

#### System Orchestrator (`server/main.py`)
- Starts API server and log generator as daemon threads.
- Runs background async `process_pending_signals()` task.
- Handles SIGINT/SIGTERM for graceful shutdown.

---

## Not Yet Started

These are planned/implied by the architecture but have no code yet:

| Feature | Notes |
|---------|-------|
| **WebSocket real-time push** | Currently HTTP polling at 2–5s intervals. Frontend and API are structurally ready for an upgrade. |
| **Database persistence** | JSON file storage is POC-only. PostgreSQL or MongoDB integration needed for scale. |
| **Authentication / RBAC** | No auth at all currently. All API endpoints are open. |
| **SIEM / log source connectors** | Only synthetic logs. No Splunk, ELK, Chronicle, or syslog integration. |
| **ML-based anomaly detection** | Detection engine is rules-only (3 patterns). No statistical or ML models. |
| **Slack / ServiceNow integration** | No third-party notification or ticketing. |
| **Multi-tenancy** | Single-instance, single-org design. |
| **Audit logging** | No record of who viewed/actioned what. |
| **Stream processing (Kafka/Flink)** | Log generator goes direct to API; no message queue. |

---

## Mock / Placeholder Data

Items that render in the UI but use hardcoded or randomly generated values:

| Location | What's Mocked |
|----------|---------------|
| `Dashboard.tsx` | CPU (78%), RAM (45%), NET (92%) — hardcoded strings |
| `Dashboard.tsx` | System Check modal — fake progress bar (0→100% over 1.2s) |
| `Dashboard.tsx` | Service details — uptime 99.99%, error rate 0.001%, load 45% |
| `AgentInsights.tsx` | CPU load bar — driven by agent status (idle/running/completed), not real CPU |
| `api.py` | Realtime metrics — partially randomized latency generation |
| `data/mock.ts` | 5 sample alerts, 6 component definitions, 5 agent profiles, 5 compliance items — used as offline fallback |

---

## Known Technical Debt

1. **Alert aging** — storage caps at 100 alerts per query; older alerts are not deleted but older pages may be missed if limit is hit.
2. **No API proxy in Vite config** — backend URL hardcoded to `http://localhost:8000` in `api.ts:9`; env variable `VITE_API_URL` exists but needs wiring.
3. **Sequential CrewAI** — agents run one at a time (sequential process); no parallelism even for independent tasks.

---

## Configuration

**Backend** — `server/.env` (copy from `.env.example`):
```
GROQ_API_KEY=...                      # Required for live AI reasoning (free tier at console.groq.com)
GROQ_MODEL=llama-3.3-70b-versatile    # Model selection
API_HOST=0.0.0.0
API_PORT=8000
```

**Frontend** — `client/.env`:
```
VITE_API_URL=http://localhost:8000   # Override backend URL
```

---

## Overall Assessment

The core pipeline — log ingestion → rule-based detection → CrewAI agent analysis (Groq) → alert creation → frontend visualization — is fully functional end-to-end. Alert status changes persist to the backend. Execute buttons on recommended actions trigger real backend handlers that populate `blocked_ips` and `flagged_users` sets. The chatbot uses live Groq calls when a key is configured, falling back to data-driven templates when not. The Agent Insights page polls live agent state and supports manual pipeline triggering. The UI is polished, dark-themed, and animated.

---

## Bug Fixes & Debugging Log

**2026-04-25 — AgentInsights.tsx Blank Page**

*Root Cause:* The running backend process was not the current code (missing `/agents/status` endpoint). Additionally, `AgentInsights.tsx` silently swallowed all fetch errors, resulting in a blank page when the API call failed.

*Diagnosis:*
1. Verified `/agents/status` endpoint exists in source code (`server/api.py:282`).
2. Checked running server routes via OpenAPI — endpoint was missing.
3. Source file had correct endpoint but wasn't running the latest code.
4. Frontend catch block silenced all errors (lines 69-78 of `AgentInsights.tsx`).

*Fix:*
1. **Backend:** Replaced Windows-incompatible emoji characters causing encoding crashes. Fixed in:
   - `server/storage.py` — Changed `✅`/`⚠️` to `[OK]`/`[WARN]`.
   - `server/api.py` — Changed `🤖`/`🚨`/`✅`/`🛑` to `[*]`/`[ALERT]`/`[OK]`/`[STOP]`.
   - `server/main.py` — Changed all print emojis to ASCII equivalents.
2. **Frontend:** Added explicit error state in `AgentInsights.tsx`:
   - Added `error` state variable.
   - Modified `loadAgents` to set error message on failure.
   - Added error rendering in pipeline flow and agent cards grid.

*Files Changed:*
- `server/storage.py` — Emoji → ASCII
- `server/api.py` — Emoji → ASCII  
- `server/main.py` — Emoji → ASCII
- `client/src/pages/AgentInsights.tsx` — Added error handling and rendering

*Verification:*
- `GET /agents/status` returns 200 with all 6 agent states.
- Frontend properly renders agents or shows error message (not blank).

Remaining gaps before production-grade use: a real database, authentication, SIEM connectors, and WebSocket real-time push.
