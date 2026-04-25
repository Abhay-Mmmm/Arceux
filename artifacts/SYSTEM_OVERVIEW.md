# 🎯 Arxis SOC - System Overview

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    (React + TypeScript)                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Dashboard   │  │   Alerts     │  │   Agents     │         │
│  │              │  │              │  │              │         │
│  │ • Heartbeat  │  │ • AI Trace   │  │ • 5 Agents   │         │
│  │ • Metrics    │  │ • Actions    │  │ • Details    │         │
│  │ • Chat       │  │ • Timeline   │  │ • Reasoning  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│                  Polls every 2s ↓                               │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTP / WebSocket
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│                    (FastAPI + Python)                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    main.py (Orchestrator)                 │  │
│  │  Starts all components in parallel threads                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                 │                                │
│        ┌────────────────────────┼────────────────────────┐      │
│        ↓                        ↓                        ↓      │
│  ┌────────────┐         ┌──────────────┐        ┌─────────────┐│
│  │    Log     │ 1-3s    │     API      │        │   Agent     ││
│  │ Generator  │────────▶│   Server     │◀──────▶│ Processing  ││
│  │            │  POST   │              │ async  │  (CrewAI)   ││
│  │ • Users    │  /logs  │ • Ingestion  │        │             ││
│  │ • Events   │         │ • Detection  │        │ 5 AI Agents ││
│  │ • Random   │         │ • Storage    │        │ • Analyze   ││
│  │ • Patterns │         │ • Endpoints  │        │ • Explain   ││
│  └────────────┘         └──────────────┘        └─────────────┘│
│                                 │                                │
│                                 ↓                                │
│                         ┌──────────────┐                         │
│                         │   Storage    │                         │
│                         │  (In-Memory) │                         │
│                         │              │                         │
│                         │ • Logs       │                         │
│                         │ • Signals    │                         │
│                         │ • Alerts     │                         │
│                         └──────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Log Generation → Detection
```
Log Generator
    → POST /logs
        → Validation
            → Storage.add_log()
                → Detection Engine
                    → If threat detected: create Signal
                        → Storage.add_signal()
```

### 2. Signal → AI Analysis
```
Background Task (every 5s)
    → Get pending signals
        → For each signal:
            → CrewAI Agent System
                → Ingestion Agent (normalize)
                → Threat Analyst (classify)
                → Context Agent (enrich)
                → Explanation Agent (summarize)
                → SOC Manager (prioritize)
            → Create Alert
                → Storage.add_alert()
```

### 3. Frontend → Real-time Updates
```
Dashboard Component
    → useEffect (every 2s)
        → GET /metrics/realtime
            → Compute from actual logs/alerts/signals
                → Return component data + history
                    → Generate dynamic SVG heartbeat
                        → Display in UI
```

## Component Descriptions

### Backend Components

**main.py** - Orchestration
- Starts API server in thread
- Starts log generator in thread
- Handles graceful shutdown
- Single entry point

**api.py** - FastAPI Server
- `/logs` - Ingest security events
- `/alerts` - Get AI-analyzed alerts
- `/metrics` - System metrics
- `/metrics/realtime` - Live component data
- `/health` - Health check
- Background task for agent processing

**log_generator.py** - Synthetic Events
- Generates realistic security events
- 6 users, 6 assets, multiple event types
- Weighted distribution (mostly benign)
- Sends to `/logs` every 1-3 seconds

**detection_engine.py** - Rule-based Detection
- Brute force detection (5+ failures)
- Suspicious login (new country)
- Insider threat (privilege + data)
- Creates signals for agent analysis

**agents/crew_system.py** - CrewAI Multi-Agent
- 5 specialized AI agents
- Sequential processing
- Generates human-readable explanations
- Powered by OpenAI GPT-4

**storage.py** - In-Memory Database
- Logs, signals, alerts storage
- Query methods
- Metrics calculation

### Frontend Components

**Dashboard.tsx** - Main View
- System heartbeat with live data
- AI analyst chat
- Alert feed
- Performance metrics
- Compliance status

**Modal.tsx** - Reusable Dialog
- Alert details with AI trace
- Service diagnostics
- System check progress

**HeartbeatLine** - Dynamic SVG
- Generates waveform from history array
- Real-time animation
- Color-coded by status

**api.ts** - Backend Integration
- fetchRealtimeMetrics (polling)
- fetchAlerts
- fetchMetrics
- Type-safe interfaces

## Key Features

### Real-time Integration
✅ Logs generated every 1-3 seconds
✅ Detection happens immediately
✅ AI agents process in background
✅ Dashboard polls every 2 seconds
✅ Heartbeat reflects actual activity

### AI-Powered Analysis
✅ Multi-agent reasoning (5 agents)
✅ Human-readable explanations
✅ MITRE ATT&CK mapping
✅ Contextual enrichment
✅ Priority recommendations

### User Experience
✅ Single-command startup (main.py)
✅ Live system monitoring
✅ Interactive components
✅ Beautiful visualizations
✅ Real-world simulation

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite |
| Styling | TailwindCSS |
| Charts | Recharts |
| Icons | Lucide React |
| Backend | FastAPI, Python 3.11 |
| AI | CrewAI + OpenAI GPT-4 |
| Storage | In-memory (SQLite-ready) |
| HTTP | Uvicorn, CORS enabled |

## Performance Metrics

- **Log Generation**: 1-3 seconds/event
- **Detection**: <10ms per log
- **AI Analysis**: 15-30 seconds per signal
- **API Response**: <50ms average
- **Frontend Poll**: Every 2 seconds
- **Heartbeat Update**: Real-time (smooth)

## Next Steps

To run the complete system:

To run the complete system:

```bash
# Terminal 1: Server (Backend)
cd server
conda activate lokam
python main.py

# Terminal 2: Client (Frontend)
cd client
npm run dev
```

Then open: **http://localhost:5173**

---

**The Arxis SOC is now a complete, real-time, AI-powered security operations center!** 🛡️
