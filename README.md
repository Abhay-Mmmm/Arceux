# Arceux

**AI-native Security Operations Center platform for financial institutions — real-time threat detection, agentic investigation, and automated compliance reporting.**

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)
![React 18](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## Overview

Arceux is a full-stack Security Operations Center platform built for financial institutions that need continuous, intelligent threat monitoring without the latency of manual triage. It ingests a stream of security events, runs them through a three-layer detection stack (rule-based, River online ML, and NetworkX graph analysis), and routes any detected signal to a six-agent CrewAI pipeline that produces structured incident reports enriched with MITRE ATT&CK context and regulatory compliance assessments. The entire pipeline — from log ingestion to alert delivery on the analyst dashboard — operates over WebSockets with sub-second latency, so analysts see threats as they emerge rather than on the next polling cycle. Built as a prototype for IIT Bombay SoC '26, Arceux demonstrates how large language models, online machine learning, and graph-structural analysis can be composed into a coherent, production-shaped SOC platform.

---

## Key Features

- **Real-time threat detection** — a three-layer stack combining 6 deterministic rule-based detectors (brute force, impossible travel, insider threat, etc.), River HalfSpaceTrees for cohort-based online anomaly scoring, and NetworkX graph analysis for structural multi-entity attack patterns.
- **6-agent CrewAI investigation pipeline** — signal-type routing selects 3–6 agents per incident (Alert Handler, Threat Analyzer, Root Cause, Compliance, Response Automation, Orchestrator), cutting token usage by ~50% for common signal types.
- **WebSocket push — sub-second alert delivery** — `new_alert`, `metrics_updated`, `agent_status_updated`, `compliance_updated`, and `pipeline_completed` events are pushed to all connected clients the moment they occur; HTTP polling serves only as a fallback.
- **AI analyst chatbot** — Groq `llama-3.1-8b-instant` with dynamic SOC context injection (live alerts, agent states, severity counts) and multi-turn conversation support; four quick-action prompts for structured analyst workflows.
- **Dynamic compliance tracking** — `GET /compliance/status` computes live IRDAI (6-hour), GDPR (72-hour), SOC 2, ISO 27001, and PCI DSS posture from unresolved alert data; the Dashboard shows a client-side countdown timer for IRDAI deadlines.
- **Cohort-based online anomaly detection** — River `HalfSpaceTrees` maintains three independent models (admin, service, standard cohorts) that learn continuously from every event without retraining.
- **Graph-based multi-entity attack detection** — a rolling-window `MultiDiGraph` of IP→user→asset relationships detects lateral movement, coordinated probes, hub-asset pressure, and IP reuse across entities.
- **Synthetic log generator** — realistic attack sequences (brute-force bursts, insider threat, lateral movement, coordinated probes) fire at configurable probabilities so all detection paths exercise reliably during demos.

---

## Architecture Overview

The backend is organized around three independent detection layers that each inspect every incoming log. The rule-based layer runs six stateful sliding-window detectors that fire first on clear-signal events (e.g., >5 failed logins in 2 minutes triggers Brute Force at HIGH severity). When no rule fires, the River online ML layer scores the event against a per-cohort HalfSpaceTrees model and emits an `ANOMALOUS_ACCESS` signal if the score exceeds a configurable threshold. As a final layer, the NetworkX graph detector maintains a rolling temporal graph of relationships between IP addresses, users, and assets; it checks for structural patterns — same IP reaching multiple users, multiple IPs converging on one user — that no single-event rule can catch.

When a detection signal is produced, it is queued in memory and picked up by the background `process_pending_signals` coroutine running inside the FastAPI event loop. A 15-second cooldown and a single-run guard prevent concurrent pipeline executions. The coroutine routes the signal through the CrewAI pipeline, which uses `signal_type` to select the relevant subset of agents rather than running all six every time. Each agent calls Groq (`llama-3.3-70b-versatile`) via LiteLLM and produces a constrained output (60–100 words, `max_iter=1`). Per-agent API keys allow rate-limit isolation across separate Groq accounts.

The WebSocket layer sits alongside the REST API inside the same FastAPI application. A `ConnectionManager` tracks all active connections; after every alert creation, status change, or pipeline completion, `broadcast()` fans the event out to every connected client concurrently using `asyncio.gather`. The crew system calls `broadcast_sync()` from its thread-pool context via `asyncio.run_coroutine_threadsafe`, ensuring no blocking cross-thread calls. The frontend `ArceuxWebSocket` singleton maintains a single persistent connection, reconnects with exponential backoff, and sends `ping` frames every 25 seconds to prevent idle disconnections.

The frontend is a three-page React 18 application. The Dashboard shows a live system heartbeat visualization, the AI analyst chatbot, a high-priority alerts feed, a real-time threat severity chart, a system performance card, and the dynamic compliance status panel. The Alerts page provides a searchable, filterable table with a slide-out detail panel, take-ownership and execute-action controls, Run Playbook triggering, and CSV export. The Agent Insights page renders the six-agent pipeline with live status indicators, execution traces, and an activity feed bar driven by WebSocket events — all optimized with `React.memo` and structural comparator state updates to eliminate visual artifacts during rapid state transitions.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 18 + TypeScript + Vite | Single-page application, three analyst pages |
| Styling | TailwindCSS 3.4 + Framer Motion | Utility-first CSS, layout animations |
| Charts | Recharts 2.9 | Threat severity bar chart, heartbeat waveforms |
| Routing | React Router DOM 6.18 | Client-side navigation between Dashboard, Alerts, Agent Insights |
| Backend | FastAPI + Uvicorn (Python) | Async REST API + WebSocket endpoint |
| AI Chatbot | Groq SDK (`llama-3.1-8b-instant`) | Fast, low-cost conversational SOC analyst |
| AI Agents | CrewAI + LiteLLM (`llama-3.3-70b-versatile`) | Six-agent incident investigation pipeline |
| ML Detection | River 0.23.0 (`HalfSpaceTrees`) | Online anomaly detection, no retraining |
| Graph Detection | NetworkX ≥3.0 (`MultiDiGraph`) | Structural multi-entity attack pattern detection |
| Real-time | WebSocket (FastAPI/Starlette) | Sub-second server push to all connected clients |
| Storage | Purely in-memory | No disk persistence, always starts clean |
| Async | Python asyncio + threading | Event loop for API + background signal processor |

---

## Project Structure

```
Arceux/
├── README.md                          # This file
├── CONTRIBUTING.md                    # Contribution guidelines
├── client/                            # React 18 frontend
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx          # Heartbeat, chatbot, alerts feed, compliance
│       │   ├── Alerts.tsx             # Alert table, filters, detail panel, actions
│       │   └── AgentInsights.tsx      # Pipeline visualization, traces, activity feed
│       ├── components/ui/             # Badge, Button, Card, Modal primitives
│       ├── hooks/
│       │   └── useWebSocket.ts        # Typed hook for subscribing to WS event types
│       ├── services/
│       │   ├── api.ts                 # REST fetch functions + transformBackendAlert()
│       │   └── websocket.ts           # Singleton ArceuxWebSocket client + reconnect logic
│       ├── data/mock.ts               # Offline fallback data (never shown when backend up)
│       └── types.ts                   # TypeScript interfaces (Alert, ComplianceStatus, etc.)
├── server/                            # FastAPI Python backend
│   ├── main.py                        # Orchestrator: starts API + log generator, shutdown handler
│   ├── api.py                         # All REST endpoints + /ws WebSocket + compliance computation
│   ├── websocket_manager.py           # ConnectionManager, broadcast(), broadcast_sync()
│   ├── detection_engine.py            # 6 rule detectors + River ML + NetworkX graph detector
│   ├── chatbot.py                     # Groq chatbot, system prompt, context builder, fallbacks
│   ├── storage.py                     # Thread-safe in-memory store for all runtime data
│   ├── models.py                      # Pydantic models: SecurityLog, Alert, DetectionSignal, etc.
│   ├── log_generator.py               # Synthetic log generator + attack sequence injectors
│   ├── agents/
│   │   └── crew_system.py             # CrewAI 6-agent pipeline, signal-type routing, per-agent keys
│   ├── requirements.txt               # Python dependencies
│   └── .env.example                   # Environment variable template (copy to .env)
└── artifacts/                         # Design docs and demo materials
    ├── IMPLEMENTATION.md              # Detailed technical specification and changelog
    ├── ARCHITECTURE.md                # Mermaid system architecture diagram
    └── DEMO_SCRIPT.md                 # 5-minute presenter guide
```

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- A Groq API key — free at [console.groq.com](https://console.groq.com)

### Installation

**Backend:**

```bash
cd server
pip install -r requirements.txt
cp .env.example .env
# Open .env and add your GROQ_API_KEY
python main.py
```

**Frontend** (separate terminal):

```bash
cd client
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — the dashboard should connect and alerts will start appearing within a few seconds.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Shared fallback Groq key for all agents and chatbot. Get one free at console.groq.com. |
| `GROQ_API_KEY_ORCHESTRATOR` | No | `GROQ_API_KEY` | Dedicated key for the Orchestrator agent (separate rate-limit pool if from a different account). |
| `GROQ_API_KEY_ALERT_HANDLER` | No | `GROQ_API_KEY` | Dedicated key for the Alert Handler agent. |
| `GROQ_API_KEY_THREAT_ANALYZER` | No | `GROQ_API_KEY` | Dedicated key for the Threat Analyzer agent. |
| `GROQ_API_KEY_ROOT_CAUSE` | No | `GROQ_API_KEY` | Dedicated key for the Root Cause agent. |
| `GROQ_API_KEY_COMPLIANCE` | No | `GROQ_API_KEY` | Dedicated key for the Compliance agent. |
| `GROQ_API_KEY_RESPONSE` | No | `GROQ_API_KEY` | Dedicated key for the Response Automation agent. |
| `GROQ_API_KEY_CHAT` | No | `GROQ_API_KEY` | Dedicated key for the chatbot (uses `llama-3.1-8b-instant`). |
| `GROQ_MODEL_AGENTS` | No | `llama-3.3-70b-versatile` | Model used by all six CrewAI agents. |
| `GROQ_MODEL_CHAT` | No | `llama-3.1-8b-instant` | Model used by the chatbot. |
| `RIVER_ANOMALY_THRESHOLD` | No | `0.75` | Minimum HalfSpaceTrees score (0.0–1.0) to emit an anomaly signal. |
| `GRAPH_WINDOW_SECONDS` | No | `300` | Rolling temporal window for graph edges (seconds). |
| `GRAPH_MIN_USERS` | No | `3` | Minimum distinct users before lateral movement pattern fires. |
| `API_HOST` | No | `0.0.0.0` | Host address for the Uvicorn server. |
| `API_PORT` | No | `8000` | Port for the Uvicorn server. |

---

## Detection System

| # | Name | Trigger | Severity | Signal Type |
|---|------|---------|----------|-------------|
| 1 | **Brute Force** | >5 failed logins from the same user within 2 minutes | HIGH | `BRUTE_FORCE` |
| 2 | **Suspicious Login** | Successful or new-country login from a high-risk location | HIGH | `SUSPICIOUS_LOGIN` |
| 2b | **Suspicious Probe** | Failed login originating from a high-risk location | MEDIUM | `SUSPICIOUS_LOGIN` |
| 3 | **Impossible Travel** | Same user authenticated from two different countries within 10 minutes | CRITICAL | `SUSPICIOUS_LOGIN` |
| 4 | **Account Takeover** | Successful login immediately following 3+ failures within 5 minutes | HIGH | `SUSPICIOUS_LOGIN` |
| 5 | **Insider Threat** | Privilege escalation followed by data download from the same user | CRITICAL | `INSIDER_THREAT` |
| 6 | **Data Exfiltration** | Downloads from 3+ distinct assets within 5 minutes | HIGH | `ANOMALOUS_ACCESS` |
| 7 | **River ML (HST)** | Per-cohort behavioral anomaly score ≥ threshold (default 0.75) | HIGH | `ANOMALOUS_ACCESS` |
| 8 | **Graph ML** | Structural patterns on ip/user/asset graph: lateral movement, coordinated probe, hub-asset pressure, IP reuse | CRITICAL/HIGH | varies |

High-risk locations: `Russia`, `North Korea`, `Unknown`, `Tor Exit Node`, `Romania`, `Iran`.

---

## Agent Pipeline

| Agent | Role | Runs On |
|-------|------|---------|
| Orchestrator Agent | Coordinates incident response lifecycle; determines scope and assigns agents | `INSIDER_THREAT` only |
| Alert Handler Agent | Triages and correlates events; deduplicates noise and extracts indicators | All signal types |
| Threat Analyzer Agent | Maps behavior to MITRE ATT&CK; classifies attacker intent and technique | `BRUTE_FORCE`, `SUSPICIOUS_LOGIN`, `INSIDER_THREAT`, DEFAULT |
| Root Cause Agent | Reconstructs forensic timeline; identifies initial vector and blast radius | `INSIDER_THREAT`, `ANOMALOUS_ACCESS` |
| Compliance Agent | Evaluates incident against GDPR, IRDAI, and SOC 2; assesses reportability and deadlines | `SUSPICIOUS_LOGIN`, `INSIDER_THREAT`, `ANOMALOUS_ACCESS` |
| Response Automation Agent | Drafts immediate containment and short-term remediation plans | `BRUTE_FORCE`, `INSIDER_THREAT` |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/logs` | Ingest a security log; runs detection engine; queues signal if detected |
| `GET` | `/alerts` | All alerts, optionally filtered by `severity` and `limit` query params |
| `GET` | `/alerts/{id}` | Single alert by ID |
| `PATCH` | `/alerts/{id}/status` | Update alert status: `open`, `investigating`, or `resolved` |
| `POST` | `/actions/execute` | Execute a response action (`block_ip` or `reset_credentials`) against an alert |
| `GET` | `/agents/status` | Current status of all 6 agents with execution stats and last trace |
| `POST` | `/agents/trigger` | Queue agent pipeline on a specific alert (or latest if no ID given) |
| `GET` | `/compliance/status` | Live compliance posture for IRDAI, GDPR, SOC 2, ISO 27001, PCI DSS |
| `GET` | `/metrics` | Summary: total logs, total alerts, alerts by severity |
| `GET` | `/metrics/realtime` | Component health and latency history for system heartbeat |
| `POST` | `/chat` | Chat with the AI analyst (free-form or quick action) |
| `GET` | `/health` | Basic health check |
| `GET` | `/debug/logs` | Recent ingested logs (debug) |
| `GET` | `/debug/signals` | Detection signals and processed status (debug) |
| `POST` | `/debug/clear` | Clear all in-memory data (debug) |
| `WS` | `/ws` | Real-time event stream — push channel for all server-side events |

---

## Known Limitations

- **In-memory storage only** — all alerts, signals, and logs reset on server restart; no PostgreSQL or file persistence.
- **No authentication** — all API endpoints are open; suitable for local demo, not for any multi-user deployment.
- **Synthetic logs only** — no connectors to real SIEMs (Splunk, ELK, syslog); all threat data is generated by the built-in log generator.
- **Per-agent Groq key isolation requires separate accounts** — keys from the same Groq account share a rate-limit pool; true isolation only applies when each `GROQ_API_KEY_*` is registered to a different account.
- **River ML warmup period** — the first ~50 events per cohort produce near-zero anomaly scores while HalfSpaceTrees builds its baseline; anomaly detection is unreliable for approximately the first 60 seconds of operation.
- **Sequential CrewAI execution** — agents within a pipeline run one at a time; there is no parallelism for independent tasks.

---

## Roadmap

- **Database persistence** — migrate from in-memory to PostgreSQL or MongoDB so alerts survive restarts and scale beyond a single process.
- **Authentication and RBAC** — add user login, role-based access control, and audit logging for who viewed or actioned which alerts.
- **SIEM and log source connectors** — integrate with Splunk, Elastic, and syslog so the platform can ingest real event streams rather than synthetic data.
- **Slack and ServiceNow integration** — push critical alert notifications to Slack channels and auto-create ServiceNow tickets for `CRITICAL` incidents.
- **Multi-tenancy** — tenant isolation for organizations running the platform as a shared service.
- **Audit trail** — immutable record of all analyst actions (take ownership, execute, resolve) for compliance evidence.

---

## License

MIT License
