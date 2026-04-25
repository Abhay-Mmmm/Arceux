# Arceux SOC — System Overview

**Version:** 0.4 | **Last Updated:** 2026-04-25

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                 │
│                   (React 18 + TypeScript + Vite)                 │
│                                                                   │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────────────┐  │
│  │  Dashboard  │   │   Alerts    │   │   Agent Insights      │  │
│  │             │   │             │   │                       │  │
│  │ • Heartbeat │   │ • Table     │   │ • 6-Agent Pipeline    │  │
│  │ • AI Chat   │   │ • Filters   │   │ • Live Status Dots    │  │
│  │ • Metrics   │   │ • Ownership │   │ • Run Pipeline Btn    │  │
│  │ • Alerts    │   │ • Execute   │   │ • Per-Agent Trace     │  │
│  └─────────────┘   └─────────────┘   └──────────────────────┘  │
│                                                                   │
│    polls /metrics/realtime  polls /alerts    polls /agents/status │
│           every 2s             every 5s           every 3s       │
└──────────────────────────────────────────────────────────────────┘
                               │ HTTP REST
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                           │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          Background Signal Processor (every 5s)            │  │
│  │  Polls storage.get_pending_signals() → run_agent_analysis  │  │
│  └────────────────────────────────────────────────────────────┘  │
│          │                                          │             │
│  ┌───────┴──────┐                       ┌──────────┴──────────┐  │
│  │ Log Generator│  POST /logs           │  CrewAI 6-Agent     │  │
│  │  (1–3s loop) │──────────────────────▶│  System (Groq LLM)  │  │
│  └──────────────┘                       │                     │  │
│                                         │ 1. Orchestrator     │  │
│  ┌───────────────┐                      │ 2. Alert Handler    │  │
│  │ Detection     │ DetectionSignal      │ 3. Threat Analyzer  │  │
│  │ Engine        │─────────────────────▶│ 4. Root Cause       │  │
│  │ (3 rules)     │                      │ 5. Compliance       │  │
│  └───────────────┘                      │ 6. Response Auto.   │  │
│                                         └─────────────────────┘  │
│                               │                                   │
│                               ↓                                   │
│                    ┌─────────────────────┐                        │
│                    │   ArceuxStorage      │                        │
│                    │                      │                        │
│                    │ • logs (last 1000)   │                        │
│                    │ • signals            │                        │
│                    │ • alerts (+ JSON)    │                        │
│                    │ • executed_actions   │                        │
│                    │ • blocked_ips (Set)  │                        │
│                    │ • flagged_users (Set)│                        │
│                    │ • agent_states (6)   │                        │
│                    └─────────────────────┘                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Log → Alert (Full Pipeline)

```
Log Generator
    → POST /logs
        → storage.add_log()
        → detection_engine.analyze(log)
            → If threat detected:
                → storage.add_signal(signal)

Background processor (every 5s)
    → storage.get_pending_signals()
        → For each signal:
            → storage.update_agent_state(all, "running")
            → crew.kickoff()   [Groq LLM]
            → storage.update_agent_state(all, "completed", trace)
            → storage.add_alert(alert)
            → storage.mark_signal_processed(signal_id)

Frontend
    → GET /alerts  (every 5s on Dashboard, polling on Alerts page)
    → GET /agents/status  (every 3s on Agent Insights)
```

### Execute Action Flow

```
Frontend "Block IP" button
    → POST /actions/execute  { action_type: "block_ip", alert_id }
        → storage.blocked_ips.add(alert_ip)
        → storage.add_alert_note(alert_id, note)
        → storage.add_executed_action(action)
        → returns { success, message }
```

### Agent Trigger Flow

```
Frontend "Run on Latest Alert" button
    → POST /agents/trigger
        → Creates synthetic DetectionSignal from latest alert
        → storage.add_signal(synthetic)
        → Background processor picks it up within 5s
```

---

## File Map

```
Arceux/
├── client/                         # React frontend
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx       # Heartbeat, AI chat, alert feed, metrics
│       │   ├── Alerts.tsx          # Alert table, take ownership, execute actions
│       │   └── AgentInsights.tsx   # Live 6-agent pipeline, trigger button
│       ├── components/
│       │   ├── Layout.tsx          # Sidebar navigation
│       │   └── ui/                 # Badge, Button, Card, Modal
│       ├── services/api.ts         # All API calls + type-safe interfaces
│       ├── data/mock.ts            # Offline fallback data
│       └── types.ts                # TypeScript interfaces
│
├── server/                         # Python FastAPI backend
│   ├── api.py                      # All REST endpoints + background processor
│   ├── main.py                     # Entry point — starts all threads
│   ├── chatbot.py                  # Groq chatbot + template fallback
│   ├── detection_engine.py         # 3 stateful rule-based detectors
│   ├── storage.py                  # Thread-safe in-memory store
│   ├── models.py                   # Pydantic data models
│   ├── log_generator.py            # Synthetic log producer
│   ├── agents/
│   │   └── crew_system.py          # 6-agent CrewAI pipeline + state tracking
│   ├── requirements.txt
│   ├── .env / .env.example
│   └── data/alerts.json            # Persisted alerts (auto-generated)
│
└── artifacts/                      # Project documentation (you are here)
    ├── PRD.md                      # Product requirements
    ├── SYSTEM_OVERVIEW.md          # Architecture (this file)
    ├── START.md                    # Startup guide
    ├── API_REFERENCE.md            # Complete API docs
    └── IMPLEMENTATION.md           # Detailed implementation notes
```

---

## Detection Rules

| Rule | Trigger Condition | Severity | Stateful? |
|------|-----------------|----------|-----------|
| BRUTE_FORCE | >5 failed logins within 2 min per user, tracks unique source IPs | HIGH | Yes — sliding window per user |
| SUSPICIOUS_LOGIN | Login from: Russia, North Korea, Iran, China, Venezuela, Tor Exit Node | HIGH | No |
| INSIDER_THREAT | Privilege escalation followed by data download, correlated per user | CRITICAL | Yes — tracks per-user sequence |

---

## Agent State Machine

Each of the 6 agents transitions through these states, tracked in `storage.agent_states`:

```
idle → running → completed
               ↘ error
```

State fields per agent:
- `status`: idle | running | completed | error
- `last_run`: ISO timestamp of most recent execution
- `tasks_completed`: cumulative count
- `execution_count`: total pipeline runs
- `total_execution_time_ms`: for avg calculation
- `last_execution_trace`: up to 8 lines from last crew result

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Groq (`llama-3.3-70b-versatile`) | Free tier, fast inference, strong reasoning; easy to swap |
| Template fallback for all LLM calls | System remains fully functional without any API key |
| Sequential CrewAI pipeline | Each agent builds on previous analysis, mirrors real SOC workflow |
| In-memory + JSON persistence | Simple for POC; alerts survive backend restarts |
| HTTP polling instead of WebSocket | Simpler architecture; structure is WebSocket-ready |
| `blocked_ips` and `flagged_users` as Sets | Thread-safe, deduplicating, O(1) lookup |
| `localModifications` in Alerts.tsx | Optimistic UI — status changes persist across poll cycles even before backend confirms |
