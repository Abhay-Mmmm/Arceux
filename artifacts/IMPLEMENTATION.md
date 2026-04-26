# Arceux — Implementation Overview

**Version:** 0.9.1 (Day 2 — Dynamic Confidence Scoring)  
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
| AI Chatbot | Groq API (`groq` SDK, `llama-3.1-8b-instant`) — dedicated key (`GROQ_API_KEY_CHAT`) |
| AI Agents | CrewAI + LiteLLM (`groq/llama-3.3-70b-versatile`) — signal-type routed, per-agent keys |
| ML Detection | River 0.21.0 (`HalfSpaceTrees`) — online anomaly detection, no retraining |
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
- **Threat Severity Chart:** Real-time bar chart (Recharts) showing distribution across CRITICAL / HIGH / MEDIUM / LOW. Polls `GET /metrics` every 5 seconds via `fetchMetrics()`; chart data derived from `alerts_by_severity` in the response via `useMemo`. Uses `isAnimationActive={false}` to prevent the bar-grow animation from replaying on each poll update. `allowDecimals={false}` on YAxis. No static fallback — starts at zero until first poll resolves.
- **Compliance Card:** Static status badges for SOC 2, ISO 27001, GDPR, IRDAI, PCI DSS.
- **Modal Dialogs:** Alert Intelligence modal (AI trace + recommendations), Service Diagnostics modal (latency history), System Check modal (live backend data).

#### Alerts Page (`client/src/pages/Alerts.tsx`)
- **Alert Table:** Severity, name, asset/user, confidence, status, timestamp columns.
- **Filter System:** Cyclic filters for severity and status; real-time search across title, user, asset, description; live filtered/total counter.
- **Auto-Refresh:** Polls `GET /alerts` every 10 seconds via `setInterval`.
- **Take Ownership:** Optimistic UI update → backend `PATCH /alerts/{id}/status` sync.
- **Execute Actions:** Per-action buttons with spinner/done/retry states; disabled after success.
- **Export CSV:** Exports filtered alerts to a dated CSV file.
- **Detail Slide-Out Panel:** Right-side drawer with full alert details, AI agent trace, and recommended action buttons.
- **Relative Timestamps:** Human-readable ("5 mins ago") with graceful fallback for invalid dates.
- **Run Playbook:** Top-right button that finds the highest-severity open alert from the current filtered list (CRITICAL > HIGH > MEDIUM > LOW) and calls `POST /agents/trigger` with that alert's ID. Button states: default "Run Playbook" → loading "Running…" (disabled, spinner) → success "Playbook Started ✓" (disabled, re-enables after 3 s) → error "Failed — Retry" (red border, re-enables immediately). On success, an inline notification below the buttons shows "Pipeline triggered on: [Alert Name] ([SEVERITY])" and auto-dismisses after 5 s. If no open alert exists in the filtered list, shows "No open alerts to run playbook on" (neutral color, auto-dismisses after 5 s).
- **Confidence Score:** Computed in `transformBackendAlert()` in `api.ts` using a combined strategy:
  1. **River ML score** — if `metadata.river_ml === true` and `metadata.anomaly_score` is present, confidence = `Math.round(anomaly_score × 100)`. River's HST score is a calibrated 0–1 float, so this maps directly to a percentage.
  2. **Severity fallback** — for rule-based signals (no River score), confidence is derived from severity: `{ critical: 95, high: 80, medium: 60, low: 40 }`, with a default of 75 for any unmapped value.

#### Agent Insights Page (`client/src/pages/AgentInsights.tsx`)
Complete rewrite with React performance optimizations to eliminate yellow-flash artifacts during state transitions:

- **Anti-Flicker Polling:** `setAgents` uses structural comparator (`compareAgentLists`) before applying updates — if the server returns identical data, the previous state reference is preserved and no re-render occurs.
- **Stable `useCallback`:** `loadAgents` is defined with an empty dependency array `[]` and uses an `everLoadedRef` (`useRef(false)`) to distinguish first-load failures from transient polling errors. The polling `setInterval` never restarts unnecessarily.
- **`React.memo` Components:** `AgentCard` and `PipelineNode` are wrapped in `React.memo` — child components only re-render when their own props actually change.
- **Tiered Error States:**
  - `initialLoading` — shows skeleton placeholder during first fetch only.
  - `pollFailed` — subtle subtitle indicator shown when a background poll fails but agents were already loaded.
  - `hardError` — explicit error message only shown when the backend never responded (first fetch failed).
- **Status Configuration:** `STATUS_CFG` object defined outside the component (stable reference, never recreated):

  | Status | Dot Color | Label |
  |--------|-----------|-------|
  | `idle` | zinc-600 | IDLE |
  | `running` | amber-400 (animate-ping at opacity-40) | RUNNING |
  | `completed` | emerald-500 | DONE |
  | `error` | red-400 | FAILED |

- **Agent Pipeline Visualization:** 6 agents shown as connected boxes with live status indicators polled every 3 seconds.
- **Agent Detail Cards:** Expanded detail with last trace, task count, avg execution time, last run timestamp.
- **`selected`** derived via `useMemo` to avoid redundant computation on each render.
- **Live Activity Feed Bar:** Full-width horizontal status bar directly below the page title. Derives its state entirely from the existing 3 s `GET /agents/status` poll (zero additional API calls). Four states:

  | State | Trigger | Display |
  |-------|---------|---------|
  | Active | Any agent `status === "running"` | Amber pulsing dot — "Pipeline active — [SIGNAL TYPE] signal — [Agent] is analyzing…" |
  | Completed | All idle/completed, any `last_run` within 30 s | Emerald ✓ — "Last run completed Xs ago — [SIGNAL TYPE] — N agents ran" |
  | Error | Any agent `status === "error"` | Red ✗ — "Last run encountered an error — [Agent] failed" |
  | Idle | All agents idle, no recent run | Zinc dot — "Pipeline idle — waiting for next signal" |

  Signal type shown via `last_signal_type` field from `GET /agents/status` response. "Run on Latest Alert" button removed — pipeline is triggered automatically by the backend or via the Alerts page "Run Playbook" button.

#### API Service Layer (`client/src/services/api.ts`)
- `fetchAlerts()`, `fetchAlertById()`, `fetchMetrics()`, `fetchRealtimeMetrics()`, `checkHealth()`, `ingestLog()`.
- `updateAlertStatus(alertId, status)` — calls `PATCH /alerts/{id}/status`.
- `executeAction({ action_type, alert_id, parameters })` — calls `POST /actions/execute`.
- `fetchAgentStatus()` — calls `GET /agents/status`; returns `{ agents: AgentStatus[], last_signal_type: string | null }`.
- `triggerAgentPipeline(alertId?)` — calls `POST /agents/trigger` with body `{ alert_id: alertId | null }`.
- `transformBackendAlert()` — `confidence` field is now dynamic: River ML anomaly score × 100 when `metadata.river_ml` is true; severity-based fallback (`critical=95, high=80, medium=60, low=40`) otherwise.

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
| `GET /agents/status` | ✅ All 6 agent states with stats + `last_signal_type` top-level field |
| `POST /agents/trigger` | ✅ Queue pipeline run; optional body `{ "alert_id": "..." }` — if provided runs on that alert, otherwise latest |
| `GET /metrics` | ✅ Summary (totals, by-severity, recent activity) |
| `GET /metrics/realtime` | ✅ Component health + latency history |
| `POST /chat` | ✅ Free-form or quick-action chat (Groq + template fallback) |
| `GET /health` | ✅ Basic health check |
| `GET /debug/logs` | ✅ Recent ingested logs |
| `GET /debug/signals` | ✅ Detection signals + processed status |
| `POST /debug/clear` | ✅ Clear all storage |

**Pipeline rate-limit enforcement** in `process_pending_signals()`:
- Checks `storage.pipeline_running` (concurrent run guard) and `now - storage.last_pipeline_run < PIPELINE_COOLDOWN_SECONDS` (15 s cooldown) before proceeding.
- Processes only the most recent pending signal (`pending[-1]`); marks all older pending signals as processed (discarded as stale).
- `try/finally` always resets `pipeline_running = False` and updates `last_pipeline_run = time.time()`.

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
| 7 | **River ML (HST)** | Behavioral anomaly score ≥ threshold (default 0.75) | HIGH | `ANOMALOUS_ACCESS` |

**High-risk locations set:** `{"Russia", "North Korea", "Unknown", "Tor Exit Node", "Romania", "Iran"}`

Sliding window deques per-user (all capped at `maxlen` to bound memory):
- `failed_login_window` — per user, deque of timestamps (rules 1, 4)
- `recent_escalations` — per user, deque of `(timestamp, asset)` tuples (rule 5)
- `data_download_window` — per user, deque of `(timestamp, asset)` tuples (rule 6)
- `last_login_location` — `{user: {location, timestamp}}` dict (rule 3)

#### River Online ML Detector (`RiverAnomalyDetector`)

Online anomaly detection using River's `HalfSpaceTrees` (HST). Runs on every incoming event alongside the rule-based checks. Rule signals take priority; the River signal is returned only when no rule fires.

**User cohorts** — each cohort gets its own independent HST model:

| Cohort | Match condition |
|--------|----------------|
| `admin_cohort` | username contains "admin" or "root" |
| `service_cohort` | username contains "service" or "svc" |
| `standard_cohort` | all other users (default) |

**HalfSpaceTrees config** (identical for all 3 cohorts):
```
n_trees=10, height=8, window_size=50, seed=42
```

**6 numeric features extracted per event:**

| Feature | Computation |
|---------|-------------|
| `hour_of_day` | `datetime.hour` of the event timestamp (0–23) |
| `is_suspicious_location` | 1.0 if location is in `SUSPICIOUS_LOCATIONS`, else 0.0 |
| `is_failed_login` | 1.0 if `event_type == "failed_login"`, else 0.0 |
| `is_privilege_escalation` | 1.0 if `event_type == "privilege_escalation"`, else 0.0 |
| `is_data_download` | 1.0 if `event_type == "data_download"`, else 0.0 |
| `user_event_rate` | Count of events from this user in the last 60 seconds (per-user deque, `maxlen=200`) |

**Scoring:** `learn_one(features)` is called first on every event (model always updates). `score_one(features)` is then called; if score ≥ `RIVER_ANOMALY_THRESHOLD` (default `0.75`), a `ANOMALOUS_ACCESS / HIGH` signal is returned with `metadata.river_ml = True` and the score in `metadata.risk_reason`.

**Warmup:** The first ~50 events per cohort produce near-zero scores while HST builds its baseline — this is expected behavior, not a bug.

**Graceful degradation:** If `river` is not installed, `RiverAnomalyDetector._available` is `False`, `DetectionEngine.river_detector` is set to `None`, and the detect call is skipped entirely. All 6 existing rules continue to fire normally.

**Configuration:** `RIVER_ANOMALY_THRESHOLD=0.75` in `server/.env`.

#### 6-Agent CrewAI System (`server/agents/crew_system.py`)
Signal-type routed pipeline powered by Groq (`llama-3.3-70b-versatile` via LiteLLM / CrewAI LLM class):

| # | Agent | Role |
|---|-------|------|
| 1 | Orchestrator Agent | Coordinates incident response lifecycle |
| 2 | Alert Handler Agent | Triages and correlates events |
| 3 | Threat Analyzer Agent | MITRE ATT&CK mapping + intent classification |
| 4 | Root Cause Agent | Forensic timeline reconstruction |
| 5 | Compliance Agent | GDPR/IRDAI regulatory evaluation |
| 6 | Response Automation Agent | Remediation planning |

**Signal-type routing** — only relevant agents run per signal:

| Signal Type | Agents Selected |
|-------------|----------------|
| `BRUTE_FORCE` | Alert Handler, Threat Analyzer, Response Automation |
| `SUSPICIOUS_LOGIN` | Alert Handler, Threat Analyzer, Compliance |
| `INSIDER_THREAT` | All 6 agents (full pipeline) |
| `ANOMALOUS_ACCESS` | Alert Handler, Root Cause, Compliance |
| DEFAULT | Alert Handler, Threat Analyzer |

**Per-agent API keys** — each agent reads its own key (`GROQ_API_KEY_ORCHESTRATOR`, etc.) with fallback to `GROQ_API_KEY`. Key prefix logged on startup for verification.

**Output limits** — every Agent has `max_iter=1`, `memory=False`. Every Task has a strict word-count cap in its `expected_output` (60–100 words). Crew runs with `verbose=False`.

**Stale-error reset** — before each pipeline run, any agent NOT selected for the current signal that still holds `status == "error"` from a previous failed run is reset to `"idle"`. This prevents zombie error display on agents that are simply not participants in the current routing path.

- Only agents in `selected_names` get their `agent_states` updated during a run.
- Falls back to simulated trace if key is missing or LLM call fails.

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
- Pipeline rate-limit fields: `last_pipeline_run: float = 0.0`, `pipeline_running: bool = False`, `PIPELINE_COOLDOWN_SECONDS: int = 15`.
- `last_signal_type: Optional[str] = None` — set by `crew_system.py` at the start of each pipeline run; exposed via `GET /agents/status` to power the Agent Insights activity feed. Reset to `None` on `POST /debug/clear`.
- Lock-based synchronization on all concurrent access.

#### Data Models (`server/models.py`)
`EventType`, `SecurityLog`, `Severity`, `SignalType`, `DetectionSignal`, `Alert`, `MetricsSummary`, `ThreatAnalysis`, `ContextEnrichment` — all Pydantic models.

#### Chatbot (`server/chatbot.py`)
- Live Groq calls using `llama-3.1-8b-instant` (fast, low token cost) via `GROQ_API_KEY_CHAT` (fallback: `GROQ_API_KEY`).
- Key prefix logged on startup for verification.
- Quick-action prompts: `explain_last`, `threat_summary`, `recommend_actions`, `system_status`.
- Template fallback when key is missing or call fails.

---

## Performance & Token Optimizations

### Signal-Type Agent Routing
Only the agents relevant to a signal type are instantiated and run. BRUTE_FORCE, for example, skips the Root Cause and Compliance agents entirely — cutting token usage by ~50% vs. the full 6-agent pipeline.

| Signal Type | Agents | Approx. Tokens Saved |
|-------------|--------|----------------------|
| BRUTE_FORCE | 3 of 6 | ~50% |
| SUSPICIOUS_LOGIN | 3 of 6 | ~50% |
| INSIDER_THREAT | 6 of 6 | 0% (full pipeline warranted) |
| ANOMALOUS_ACCESS | 3 of 6 | ~50% |

### Per-Agent Output Limits
Every agent is constrained to 60–100 words via `expected_output`. `max_iter=1` eliminates retry loops. `memory=False` removes hidden token overhead from CrewAI's internal memory. `verbose=False` on Crew suppresses internal framework logging tokens.

### Pipeline Cooldown (15 seconds)
`storage.pipeline_running` flag and `storage.last_pipeline_run` timestamp enforce a 15-second cooldown between pipeline runs. Only the most recent pending signal is processed per window; older queued signals are discarded as stale. Prevents burst-detection scenarios from triggering back-to-back agent runs.

### Model Split Strategy
- **Agents** use `llama-3.3-70b-versatile` (`GROQ_MODEL_AGENTS`) — highest quality for deep analysis.
- **Chatbot** uses `llama-3.1-8b-instant` (`GROQ_MODEL_CHAT`) — 4× faster, dramatically lower token consumption, separate rate-limit impact.

### Per-Agent API Key Isolation
Each agent and the chatbot can be assigned a dedicated Groq API key from a separate account, giving each its own rate-limit pool. Keys configured via: `GROQ_API_KEY_ORCHESTRATOR`, `GROQ_API_KEY_ALERT_HANDLER`, `GROQ_API_KEY_THREAT_ANALYZER`, `GROQ_API_KEY_ROOT_CAUSE`, `GROQ_API_KEY_COMPLIANCE`, `GROQ_API_KEY_RESPONSE`, `GROQ_API_KEY_CHAT`. All fall back to `GROQ_API_KEY` if not set.

---

## Not Yet Started

| Feature | Notes |
|---------|-------|
| **WebSocket real-time push** | Currently HTTP polling at 2–10 s intervals depending on page. |
| **Database persistence** | Purely in-memory. PostgreSQL or MongoDB needed for scale. |
| **Authentication / RBAC** | All API endpoints are open. |
| **SIEM / log source connectors** | Only synthetic logs. No Splunk, ELK, or syslog integration. |
| **Slack / ServiceNow integration** | No third-party notification or ticketing. |
| **Multi-tenancy** | Single-instance, single-org design. |
| **Audit logging** | No record of who viewed/actioned what. |

---

## Mock / Placeholder Data

| Location | What's Mocked | Live Alternative |
|----------|---------------|-----------------|
| `Dashboard.tsx` — System Check modal | Fake progress animation (0→100% over 1.2s) | None |
| `Dashboard.tsx` — Service details | Uptime 99.99%, error rate 0.001% are static strings | None |
| `Dashboard.tsx` — Compliance card | SOC 2 / ISO 27001 / GDPR / IRDAI / PCI DSS badges always static | None |
| `AgentInsights.tsx` | CPU load bar driven by agent status, not real CPU metrics | None |
| `api.py` — realtime metrics | Latency values are partially randomized per request | None |
| `data/mock.ts` | 5 sample alerts + 6 component definitions — offline fallback only; never shown when backend is reachable | `GET /alerts`, `GET /metrics/realtime` |

**Note on `data/mock.ts`:** The 6 component definitions in `mock.ts` are UI scaffolding for the heartbeat visualization — they are not related to the 6 CrewAI agents. The real agent states come exclusively from `GET /agents/status`.

---

## Known Technical Debt

1. **Alert volume** — storage caps `GET /alerts` at 100 by default; older alerts not deleted but may be missed if limit is hit.
2. **No API proxy in Vite config** — backend URL hardcoded to `http://localhost:8000` in `api.ts`; `VITE_API_URL` env var exists but not wired.
3. **Sequential CrewAI** — agents run one at a time; no parallelism for independent tasks.
4. **Data exfiltration fires on same asset** — exfiltration rule counts unique assets, but the log generator can repeat the same asset for a user, reducing trigger frequency.
5. **Per-agent keys require separate Groq accounts** — keys from the same account share the same rate-limit pool; true isolation only works when each `GROQ_API_KEY_*` is from a different account. Single-account fallback still helps isolate chatbot vs. agent traffic.

---

## Configuration

**Backend** — `server/.env` (copy from `.env.example`):
```
# Shared fallback
GROQ_API_KEY=gsk_...                        # Required — get free key at console.groq.com

# Per-agent keys (optional — separate Groq accounts for true pool isolation)
GROQ_API_KEY_ORCHESTRATOR=gsk_...
GROQ_API_KEY_ALERT_HANDLER=gsk_...
GROQ_API_KEY_THREAT_ANALYZER=gsk_...
GROQ_API_KEY_ROOT_CAUSE=gsk_...
GROQ_API_KEY_COMPLIANCE=gsk_...
GROQ_API_KEY_RESPONSE=gsk_...
GROQ_API_KEY_CHAT=gsk_...

# Model selection
GROQ_MODEL_AGENTS=llama-3.3-70b-versatile   # Agent pipeline
GROQ_MODEL_CHAT=llama-3.1-8b-instant        # Chatbot (fast + cheap)

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
python-dotenv, requests, aiohttp<3.10, river==0.21.0, pytest
```

---

## Overall Assessment

The core pipeline — log ingestion → 6-rule detection engine → CrewAI agent analysis (Groq via LiteLLM) → alert creation → frontend visualization — is fully functional end-to-end. Six distinct threat patterns fire reliably: Brute Force, Suspicious Login (success + probe), Impossible Travel, Account Takeover, Insider Threat, and Data Exfiltration. The System Perf card in the Dashboard updates dynamically from live backend data. The Threat Severity bar chart polls `GET /metrics` every 5 seconds for real counts. Storage is purely in-memory so each server restart begins with a clean slate. The chatbot uses live Groq calls when a key is configured, falling back to data-driven templates when not. Agent Insights renders without yellow-flash artifacts through React.memo, JSON-diff state updates, and stable polling references.

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

### 2026-04-26 — Groq Rate Limits Triggered Within 10 Seconds of Startup

*Root Cause:* Four compounding issues: (1) All 6 agents ran on every signal regardless of type, wasting tokens and saturating the rate limit immediately. (2) Agent tasks had no output length constraints, producing verbose multi-paragraph responses that consumed large token budgets. (3) The background processor ran a new pipeline every 5 s even when the previous one hadn't finished, causing concurrent API calls. (4) The chatbot used the same large model and key pool as the agents, competing for rate limit headroom.

*Fix:*
- **Signal-type routing** — `get_agents_for_signal()` selects 3–6 agents per signal type; skipped agents retain their previous state and are not updated.
- **Output limits** — `max_iter=1`, `memory=False` on every Agent; strict word-count cap in every Task's `expected_output`; `verbose=False` on Crew.
- **Pipeline cooldown** — 15-second cooldown enforced via `storage.pipeline_running` flag and `storage.last_pipeline_run` timestamp; only the most recent pending signal is processed per window.
- **Model split** — chatbot switched to `llama-3.1-8b-instant` via `GROQ_MODEL_CHAT`; agents keep `llama-3.3-70b-versatile` via `GROQ_MODEL_AGENTS`.
- **Per-agent API keys** — each agent reads `GROQ_API_KEY_<NAME>` with fallback to `GROQ_API_KEY`; chatbot reads `GROQ_API_KEY_CHAT`; key prefix logged on startup.

*Files Changed:* `server/agents/crew_system.py`, `server/storage.py`, `server/api.py`, `server/chatbot.py`, `server/.env.example`

---

### 2026-04-26 — No Detections Firing

*Root Cause:* Three compounding issues:
1. Brute force requires >5 failures; random log distribution rarely produced 6 for the same user in 2 minutes.
2. Suspicious login rule only checked `successful_login` and `new_country_login` — `failed_login` attempts from high-risk locations were silently ignored.
3. Insider threat timing was random — `data_download` frequently arrived before `privilege_escalation`.

*Fix:*
- Added `generate_brute_force_burst()` (7 rapid failed logins) with 15% fire probability per cycle.
- Added `generate_insider_threat_sequence()` (escalation → download, same user) with 10% fire probability per cycle.
- Added Rule 2b: failed login from suspicious location → MEDIUM `SUSPICIOUS_LOGIN` signal.
- Added 3 new detection rules: Impossible Travel (CRITICAL), Account Takeover (HIGH), Data Exfiltration (HIGH → `ANOMALOUS_ACCESS`).

*Files Changed:* `server/detection_engine.py`, `server/log_generator.py`, `server/main.py`

---

### 2026-04-26 — AgentInsights Yellow Flash During State Transitions

*Root Cause:* Three compounding issues:
1. `setAgents(data)` was called on every 3-second poll even when the server returned identical data, always creating a new array reference and triggering a full re-render of all 6 agent cards simultaneously.
2. `AgentCard` and `PipelineNode` were not memoized, so any parent re-render re-rendered all children regardless of prop changes.
3. `useCallback` had `[agents.length]` in its dependency array (an earlier fix attempt), causing the polling interval to restart every time an agent changed status — producing extra immediate fetches and additional re-renders mid-transition. The amber `animate-ping` pulse active during the `running` state made each simultaneous re-render visually appear as a full-page yellow flash.
4. Agents not selected by the signal-type router retained `status: "error"` from a previous failed run indefinitely, displayed as an error badge even when no error was occurring.

*Fix:*
- **JSON diff in `setAgents`:** `setAgents(prev => JSON.stringify(prev) === JSON.stringify(data) ? prev : data)` — preserves previous reference when data is unchanged, suppressing the re-render entirely.
- **`React.memo`** on `AgentCard` and `PipelineNode` — child re-renders only when their own props change.
- **Stable `useCallback`** with empty dependency array `[]`; `everLoadedRef` (`useRef(false)`) tracks whether any successful fetch has occurred, used in the catch block to decide whether to show `hardError` vs. `pollFailed`.
- **Stale-error reset in `crew_system.py`:** Before each pipeline run, non-selected agents with `status == "error"` are reset to `"idle"`, preventing zombie error display.
- **Reduced `animate-ping` opacity** from default to `opacity-40` to soften the running pulse.
- **Removed `transition-all`** from heavy container elements that don't need animated layout shifts.
- **Status label `ERROR` → `FAILED`** to reflect that the failure is a task/LLM failure, not a system error.

*Files Changed:* `client/src/pages/AgentInsights.tsx`, `server/agents/crew_system.py`

---

### 2026-04-26 — Threat Severity Chart Was Static

*Root Cause:* The bar chart in Dashboard used a hardcoded `SEVERITY_DATA` constant with fixed values `[{ name: 'Crit', value: 12 }, ...]` that never updated.

*Fix:*
- Removed `SEVERITY_DATA` constant.
- Added `severityCounts` state initialized to `{ CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }`.
- Added `useEffect` that polls `fetchMetrics()` every 5 seconds and writes `data.alerts_by_severity` into `severityCounts`.
- Derived `severityChartData` via `useMemo` from `severityCounts` so Recharts only receives a new array reference when counts actually change.
- Set `isAnimationActive={false}` on `Bar` to prevent the grow animation from replaying on every poll tick.

*Files Changed:* `client/src/pages/Dashboard.tsx`

---

### 2026-04-26 — Confidence Score Audit

*Audit Result:* Fix already correctly in place. Full audit of `client/src/services/api.ts`, `client/src/pages/Alerts.tsx`, and `client/src/types.ts` found no hardcoded confidence values.

`transformBackendAlert()` computes confidence dynamically (lines 77–81 of `api.ts`):
- River ML alerts (`metadata.river_ml === true` + `anomaly_score != null`): `Math.round(anomaly_score × 100)`
- Rule-based alerts: `{ critical: 95, high: 80, medium: 60, low: 40 }[severity]` with `?? 75` fallback

`Alerts.tsx` reads `alert.confidence` directly with no override. `types.ts` declares `confidence: number` with no default.

All alerts currently showing 80% is expected: the detection engine generates `HIGH` severity for Brute Force, Suspicious Login, Account Takeover, and Data Exfiltration — the four most frequently triggered rules. `CRITICAL` (95%) appears on Impossible Travel and Insider Threat; `MEDIUM` (60%) appears on failed-login probes from high-risk locations.

*Files Changed:* None
