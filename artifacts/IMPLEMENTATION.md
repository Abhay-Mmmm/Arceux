# Arceux — Implementation Overview

**Version:** 0.5.0 (Day 2 — Detection Expansion & Agent Integration)  
**Last Updated:** 2026-04-26  
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
| AI Agents | CrewAI + LiteLLM (`groq/llama-3.3-70b-versatile` string format) |
| Storage | Purely in-memory (no disk persistence) |
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
│   ├── agents/crew_system.py      # CrewAI 6-agent system (Groq via LiteLLM)
│   ├── detection_engine.py        # Rule-based threat detection (6 rules)
│   ├── storage.py                 # Thread-safe in-memory store
│   ├── models.py                  # Pydantic data models
│   └── log_generator.py           # Synthetic log generator + attack sequences
└── artifacts/                     # Design docs and implementation notes
```

---

## Fully Implemented

### Frontend

#### Dashboard (`client/src/pages/Dashboard.tsx`)
- **System Heartbeat Visualization:** SVG-based waveform charts for 6 system components with live latency polling every 2 seconds. Color-coded by health status (green/yellow/red).
- **AI Analyst Chat Panel:** Full chatbot UI with message history, role-based styling, 4 quick-action buttons (Explain last alert, Threat summary, Recommend actions, System status), markdown rendering, and Enter-to-send.
- **High Priority Alerts Feed:** Auto-fetches high/critical alerts every 5 seconds; shows severity badges, timestamps, and opens a modal on click.
- **System Perf Card:** Dynamic CPU / Memory / Network bars driven by live backend data — CPU scales with total component event throughput, Memory scales with alert backlog pressure, Network is inverse of average latency. Bars animate with `transition-all duration-700` and color-shift green → yellow → red at 60% and 85%.
- **Threat Severity Chart:** Bar chart (Recharts) showing distribution across CRITICAL / HIGH / MEDIUM / LOW.
- **Compliance Card:** Static status badges for SOC 2, ISO 27001, GDPR, IRDAI, PCI DSS.
- **Modal Dialogs:** Alert Intelligence modal (AI trace + recommendations), Service Diagnostics modal (latency history), System Check modal (live backend data).

#### Alerts Page (`client/src/pages/Alerts.tsx`)
- **Alert Table:** Severity, name, asset/user, confidence, status, timestamp columns.
- **Filter System:** Cyclic filters for severity and status; real-time search across title, user, asset, description; live filtered/total counter.
- **Take Ownership:** Optimistic UI update → backend `PATCH /alerts/{id}/status` sync.
- **Execute Actions:** Per-action buttons with spinner/done/retry states; disabled after success.
- **Export CSV:** Exports filtered alerts to a dated CSV file.
- **Detail Slide-Out Panel:** Right-side drawer with full alert details, AI agent trace, and recommended action buttons.
- **Relative Timestamps:** Human-readable ("5 mins ago") with graceful fallback for invalid dates.

#### Agent Insights Page (`client/src/pages/AgentInsights.tsx`)
- **Agent Pipeline Visualization:** 6 agents shown as connected boxes with live status indicators polled every 3 s.
- **Agent Detail Cards:** Expanded detail with last trace, task count, avg execution time, last run timestamp.
- **Run on Latest Alert:** Calls `POST /agents/trigger` to queue a pipeline run.
- **Error State:** Shows explicit error message if backend is unreachable (no silent blank page).

#### API Service Layer (`client/src/services/api.ts`)
- `fetchAlerts()`, `fetchAlertById()`, `fetchMetrics()`, `fetchRealtimeMetrics()`, `checkHealth()`, `ingestLog()`.
- `updateAlertStatus(alertId, status)` — calls `PATCH /alerts/{id}/status`.
- `executeAction({ action_type, alert_id, parameters })` — calls `POST /actions/execute`.
- `fetchAgentStatus()` — calls `GET /agents/status`.
- `triggerAgentPipeline()` — calls `POST /agents/trigger`.

#### UI Components
- `Badge.tsx`, `Button.tsx`, `Card.tsx`, `Modal.tsx`

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
| `GET /metrics/realtime` | ✅ Component health + latency history |
| `POST /chat` | ✅ Free-form or quick-action chat (Groq + template fallback) |
| `GET /health` | ✅ Basic health check |
| `GET /debug/logs` | ✅ Recent ingested logs |
| `GET /debug/signals` | ✅ Detection signals + processed status |
| `POST /debug/clear` | ✅ Clear all storage |

#### Detection Engine (`server/detection_engine.py`)
Six stateful rule-based detectors using per-user sliding windows:

| # | Rule | Trigger | Severity | Signal Type |
|---|------|---------|----------|-------------|
| 1 | **Brute Force** | >5 failed logins / 2 min, same user | HIGH | `BRUTE_FORCE` |
| 2 | **Suspicious Login** | Successful/new-country login from high-risk location | HIGH | `SUSPICIOUS_LOGIN` |
| 2b | **Suspicious Probe** | Failed login FROM high-risk location | MEDIUM | `SUSPICIOUS_LOGIN` |
| 3 | **Impossible Travel** | Same user, different country, <10 min apart | CRITICAL | `SUSPICIOUS_LOGIN` |
| 4 | **Account Takeover** | Successful login after 3+ failures in 5 min | HIGH | `SUSPICIOUS_LOGIN` |
| 5 | **Insider Threat** | Privilege escalation → data download, same user | CRITICAL | `INSIDER_THREAT` |
| 6 | **Data Exfiltration** | Downloads from 3+ different assets in 5 min | HIGH | `ANOMALOUS_ACCESS` |

New state tracked per engine instance:
- `failed_login_window` — sliding deque per user (rules 1, 4)
- `recent_escalations` — deque per user (rule 5)
- `data_download_window` — sliding deque per user (rule 6)
- `last_login_location` — `{user: {location, timestamp}}` dict (rule 3)

#### 6-Agent CrewAI System (`server/agents/crew_system.py`)
Sequential agent pipeline powered by Groq (`llama-3.3-70b-versatile` via LiteLLM string format):

| # | Agent | Role |
|---|-------|------|
| 1 | Orchestrator Agent | Coordinates incident response lifecycle |
| 2 | Alert Handler Agent | Triages and correlates events |
| 3 | Threat Analyzer Agent | MITRE ATT&CK mapping + intent classification |
| 4 | Root Cause Agent | Forensic timeline reconstruction |
| 5 | Compliance Agent | GDPR/IRDAI regulatory evaluation |
| 6 | Response Automation Agent | Remediation planning |

- LLM passed as `"groq/llama-3.3-70b-versatile"` string (LiteLLM format) — no longer uses `langchain_groq.ChatGroq`.
- `GROQ_API_KEY` read from environment; LiteLLM picks it up automatically.
- Falls back to simulated trace if key is missing or LLM call fails.
- `run_agent_analysis` updates `storage.agent_states` throughout execution.

#### Log Generator (`server/log_generator.py`)
- **Normal logs:** 6 users, 6 asset types, 5 event types with weighted distribution (50% successful_login, 25% failed_login, 15% data_download, 5% privilege_escalation, 5% new_country_login). Fires every 1–3 seconds.
- **`generate_brute_force_burst()`:** 7 rapid failed logins from same user/IP/location. All arrive within ~3 seconds — guarantees BRUTE_FORCE trigger.
- **`generate_insider_threat_sequence()`:** `privilege_escalation` followed 1 second later by `data_download` for the same user/asset — guarantees INSIDER_THREAT trigger.

#### System Orchestrator (`server/main.py`)
- **Attack sequence probabilities per cycle:**
  - 15% → brute-force burst
  - 10% → insider threat sequence
  - 75% → normal random log
- Starts API server and log generator as daemon threads.
- Runs background `process_pending_signals()` task.
- Handles SIGINT/SIGTERM for graceful shutdown.

#### Storage Layer (`server/storage.py`)
- **Purely in-memory** — no JSON file persistence. Alerts always start at zero on restart.
- Thread-safe collections for logs (capped at 1000), signals, alerts, and executed actions.
- `blocked_ips: Set[str]`, `flagged_users: Set[str]` for action tracking.
- `agent_states: Dict[str, Dict]` — per-agent state (status, last_run, tasks_completed, execution_count, total_execution_time_ms, last_execution_trace).
- Lock-based synchronization on all concurrent access.

#### Data Models (`server/models.py`)
`EventType`, `SecurityLog`, `Severity`, `SignalType`, `DetectionSignal`, `Alert`, `MetricsSummary`, `ThreatAnalysis`, `ContextEnrichment` — all Pydantic models.

#### Chatbot (`server/chatbot.py`)
- Live Groq calls (`llama-3.3-70b-versatile`) with last 5 alerts as context.
- Quick-action prompts: `explain_last`, `threat_summary`, `recommend_actions`, `system_status`.
- Template fallback when key is missing or call fails.

---

## Not Yet Started

| Feature | Notes |
|---------|-------|
| **WebSocket real-time push** | Currently HTTP polling at 2–5 s intervals. |
| **Database persistence** | Purely in-memory. PostgreSQL or MongoDB needed for scale. |
| **Authentication / RBAC** | All API endpoints are open. |
| **SIEM / log source connectors** | Only synthetic logs. No Splunk, ELK, or syslog integration. |
| **ML-based anomaly detection** | Detection engine is rules-only. No statistical or ML models. |
| **Slack / ServiceNow integration** | No third-party notification or ticketing. |
| **Multi-tenancy** | Single-instance, single-org design. |
| **Audit logging** | No record of who viewed/actioned what. |

---

## Mock / Placeholder Data

| Location | What's Mocked |
|----------|---------------|
| `Dashboard.tsx` — System Check modal | Fake progress animation (0→100% over 1.2s) |
| `Dashboard.tsx` — Service details | Uptime 99.99%, error rate 0.001% are static |
| `AgentInsights.tsx` | CPU load bar driven by agent status, not real CPU |
| `api.py` | Realtime metrics latency values are partially randomized |
| `data/mock.ts` | 5 sample alerts, 6 component definitions — offline fallback only |

---

## Known Technical Debt

1. **Alert volume** — storage caps GET /alerts at 100 by default; older alerts not deleted but may be missed if limit is hit.
2. **No API proxy in Vite config** — backend URL hardcoded to `http://localhost:8000` in `api.ts`; `VITE_API_URL` env var exists but not wired.
3. **Sequential CrewAI** — agents run one at a time; no parallelism for independent tasks.
4. **Data exfiltration fires on same asset** — exfiltration rule counts unique assets, but the log generator can repeat the same asset for a user, reducing trigger frequency.

---

## Configuration

**Backend** — `server/.env` (copy from `.env.example`):
```
GROQ_API_KEY=gsk_...                  # Required — get free key at console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile    # Model selection
API_HOST=0.0.0.0
API_PORT=8000
```

**Frontend** — `client/.env.local`:
```
VITE_API_URL=http://localhost:8000
```

**Python dependencies** — `server/requirements.txt`:
```
fastapi, uvicorn[standard], pydantic, crewai, litellm, groq,
python-dotenv, requests, aiohttp<3.10, pytest
```

---

## Overall Assessment

The core pipeline — log ingestion → 6-rule detection engine → CrewAI agent analysis (Groq via LiteLLM) → alert creation → frontend visualization — is fully functional end-to-end. Six distinct threat patterns fire reliably: Brute Force, Suspicious Login (success + probe), Impossible Travel, Account Takeover, Insider Threat, and Data Exfiltration. The System Perf card in the Dashboard updates dynamically from live backend data. Storage is purely in-memory so each server restart begins with a clean slate. The chatbot uses live Groq calls when a key is configured, falling back to data-driven templates when not.

---

## Bug Fixes & Debugging Log

### 2026-04-25 — AgentInsights.tsx Blank Page

*Root Cause:* `AgentInsights.tsx` silently swallowed all fetch errors in its catch block, leaving `agents = []` and `loading = false`, which produced a blank page.

*Fix:*
- Added explicit `error` state in `AgentInsights.tsx`; catch block now sets error message.
- Added error UI in pipeline and cards sections.

*Files Changed:* `client/src/pages/AgentInsights.tsx`

---

### 2026-04-25 — Alert History Persisting Across Restarts

*Root Cause:* `ArceuxStorage._load_from_disk()` reloaded `data/alerts.json` on every startup. Two separate `data/` directories existed (`Arceux/data/` and `Arceux/server/data/`) causing confusion about which file was active.

*Fix:*
- Removed `_load_from_disk()` and all `_persist_to_disk()` calls entirely.
- Removed `json`, `Path`, and `data_dir` from storage — now purely in-memory.
- Deleted `server/data/alerts.json` (627 stale alerts).

*Files Changed:* `server/storage.py`

---

### 2026-04-25 — CrewAI Agent LLM Validation Error

*Root Cause:* `crew_system.py` passed a `langchain_groq.ChatGroq` object as the `llm` parameter. Newer CrewAI dropped LangChain LLM support and now validates `llm` as either a string or its own `BaseLLM` type.

*Fix:*
- Removed `langchain_groq` import entirely.
- Changed `groq_llm` to a LiteLLM-format string: `"groq/llama-3.3-70b-versatile"`.
- Installed `litellm` and removed `langchain`/`langchain-groq` from `requirements.txt`.
- Resolved pydantic/python-dotenv version conflicts by upgrading crewai and litellm together.

*Files Changed:* `server/agents/crew_system.py`, `server/requirements.txt`

---

### 2026-04-26 — No Detections Firing

*Root Cause:* Three compounding issues:
1. Brute force requires >5 failures; random log distribution rarely produced 6 for the same user in 2 minutes.
2. Suspicious login rule only checked `successful_login` and `new_country_login` — `failed_login` attempts from North Korea/Russia/Tor were silently ignored.
3. Insider threat timing was random — `data_download` frequently arrived before `privilege_escalation`.

*Fix:*
- Added `generate_brute_force_burst()` (7 rapid failed logins) with 15% fire probability per cycle.
- Added `generate_insider_threat_sequence()` (escalation → download, same user) with 10% fire probability per cycle.
- Added Rule 2b: failed login from suspicious location → MEDIUM `SUSPICIOUS_LOGIN` signal.
- Added 3 new detection rules: Impossible Travel (CRITICAL), Account Takeover (HIGH), Data Exfiltration (HIGH → `ANOMALOUS_ACCESS`).

*Files Changed:* `server/detection_engine.py`, `server/log_generator.py`, `server/main.py`
