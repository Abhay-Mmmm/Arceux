# Arceux SOC — Product Requirements Document

**Version:** 0.4 (POC — AI-Native SOC with Groq + Full Interactive UI)
**Status:** Active Development — Early Prototype
**Last Updated:** 2026-04-25

---

## Objective

Build a demonstrable proof-of-concept of the Arceux SOC platform that showcases:
- Live synthetic log ingestion → real-time rule-based threat detection
- Multi-agent AI reasoning pipeline (CrewAI + Groq)
- An AI chatbot analyst powered by Groq
- An analyst-facing dashboard with alerts, agent insights, and live system metrics

The goal is to **visually and conceptually demonstrate an agentic SOC**, not to build a production SIEM.

---

## Success Criteria

- Logs flow end-to-end in real time
- Alerts produced and explained by 6 specialized AI agents
- Alert status changes (open → investigating → resolved) persist to the backend
- AI chatbot answers live questions about the current threat landscape
- Agent Insights page shows live pipeline status and per-agent execution traces
- Analysts can execute actions (block IP, reset credentials) that persist to storage
- Entire system runs locally; demo explainable in under 5 minutes

---

## Non-Goals (Explicitly Out of Scope)

- No Kafka, Flink, or stream processing infrastructure
- No real ML model training or statistical anomaly detection
- No compliance submission or regulatory reporting automation
- No enterprise-scale performance or horizontal scaling
- No authentication, RBAC, or multi-tenancy

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Vite |
| Styling | TailwindCSS 3.4 + Framer Motion |
| Charts | Recharts 2.9 |
| Routing | React Router DOM 6.18 |
| Backend | FastAPI + Uvicorn (Python 3.11+) |
| AI Chatbot | Groq API (`groq` SDK, `llama-3.3-70b-versatile`) |
| AI Agents | CrewAI + LangChain + `langchain-groq` |
| Storage | In-memory + JSON file persistence |
| Async | Python asyncio + threading |

---

## Core Components

### 1. Synthetic Log Generator (`server/log_generator.py`)
- Emits realistic security events every 1–3 seconds via `POST /logs`
- 6 users, 6 asset types, 5 event types with weighted distribution
- Higher probability of suspicious locations on suspicious event types

### 2. Detection Engine (`server/detection_engine.py`)
Three rule-based stateful detectors:

| Rule | Trigger | Severity |
|------|---------|----------|
| BRUTE_FORCE | >5 failed logins in a 2-min sliding window per user | HIGH |
| SUSPICIOUS_LOGIN | Login from high-risk location (Russia, North Korea, Tor, Iran, etc.) | HIGH |
| INSIDER_THREAT | Privilege escalation followed by data download (per user) | CRITICAL |

### 3. 6-Agent CrewAI System (`server/agents/crew_system.py`)
Sequential pipeline powered by Groq (`llama-3.3-70b-versatile` via `langchain-groq`):

| # | Agent | Role |
|---|-------|------|
| 1 | Orchestrator Agent | Incident Commander — coordinates response lifecycle |
| 2 | Alert Handler Agent | Tier-1 triage and event correlation |
| 3 | Threat Analyzer Agent | MITRE ATT&CK mapping + attacker intent classification |
| 4 | Root Cause Agent | Forensic timeline reconstruction + blast radius |
| 5 | Compliance Agent | GDPR / IRDAI / SOC 2 regulatory evaluation |
| 6 | Response Automation Agent | Containment and remediation planning |

Falls back to simulated trace if `GROQ_API_KEY` is not set. Updates `storage.agent_states` throughout execution (idle → running → completed/error).

### 4. AI Chatbot (`server/chatbot.py`)
- Uses Groq API as "senior SOC analyst with deep threat intelligence expertise"
- Context injection: last 5 alerts as JSON + alert stats in every prompt
- Quick actions: `explain_last`, `threat_summary`, `recommend_actions`, `system_status`
- Template fallback when `GROQ_API_KEY` is absent

### 5. Backend API (`server/api.py`)
See `API_REFERENCE.md` for the complete endpoint list.

### 6. Storage (`server/storage.py`)
- Thread-safe in-memory storage with JSON persistence (alerts survive restart)
- Tracks: `blocked_ips` (Set), `flagged_users` (Set), `agent_states` (per-agent dict)

### 7. Frontend — Three Pages

**Dashboard (`client/src/pages/Dashboard.tsx`)**
- SVG heartbeat waveform for 6 system components (2s polling)
- AI Analyst chat panel (Groq-powered, 4 quick-action buttons)
- Live high/critical alert feed (5s polling)
- Threat severity chart + compliance status badges

**Alerts (`client/src/pages/Alerts.tsx`)**
- Sortable/filterable alert table with real-time search
- Take Ownership → `PATCH /alerts/{id}/status` (optimistic UI)
- Execute Actions → `POST /actions/execute` (block IP, reset credentials)
- Slide-out detail panel with full AI agent trace

**Agent Insights (`client/src/pages/AgentInsights.tsx`)**
- Live 6-agent pipeline with status dots (idle/running/completed/error), 3s polling
- "Run on Latest Alert" button → `POST /agents/trigger`
- Clickable agent cards expand detail panel with execution trace, task count, avg time
- Terminal window shows real `last_execution_trace` lines from last crew run

---

## Demo Flow (Scripted)

1. Start backend: `cd server && python main.py`
2. Start frontend: `cd client && npm run dev`
3. Logs stream live in the backend terminal
4. Detection fires (brute force, suspicious login, or insider threat)
5. 6-agent pipeline analyzes the signal (~5–30 seconds depending on Groq)
6. Alert appears in frontend with AI-generated explanation
7. Click alert → full agent trace visible
8. Click "Take Ownership" → status persists to backend
9. Click "Execute" on a recommended action → blocked IP / credential reset
10. Switch to Agent Insights → click "Run on Latest Alert" → watch pipeline live

**Key Pitch Lines:**
- "This is not alerting, this is reasoning."
- "Each alert is a mini SOC team."
- "Rules today, ML tomorrow — agents stay."
- "Agents explain what junior analysts miss."

---

## Known Gaps (Planned for Future Phases)

| Feature | Notes |
|---------|-------|
| WebSocket push | Currently HTTP polling at 2–5s |
| Database persistence | JSON file is POC-only; PostgreSQL/MongoDB needed for scale |
| Authentication / RBAC | No auth — all endpoints are open |
| SIEM connectors | Only synthetic logs; no Splunk, ELK, Chronicle |
| ML anomaly detection | Rules-only; no statistical models |
| Slack / ServiceNow | No third-party notifications or ticketing |
| Multi-tenancy | Single-instance, single-org design |
| Audit logging | No record of who viewed/actioned what |
