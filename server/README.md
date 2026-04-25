# 🛡️ Arxis SOC Backend

**AI-Native Security Operations Center - Proof of Concept**

A demonstration backend for an intelligent SOC platform that uses multi-agent AI reasoning to analyze security threats.

## 🚀 Quick Start (Recommended)

**Run everything with a single command:**

```bash
# From the backend directory
python main.py
```

This will start:
- ✅ FastAPI API server (port 8000)
- ✅ Synthetic log generator (sending logs every 1-3s)
- ✅ Real-time detection engine
- ✅ Background AI agent processing (CrewAI)

**Then open your frontend:**
- Frontend dashboard: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Alerts endpoint: `http://localhost:8000/alerts`

Press `Ctrl+C` to stop all services gracefully.

---

## 🎯 What This Is

This is a **POC/demo backend** designed to showcase:
- Real-time security log ingestion
- Rules-based threat detection
- **Multi-agent AI reasoning using CrewAI**
- Human-readable threat explanations
- RESTful API for frontend consumption

**Not production-grade.** This is built for demonstration and learning.

---

## 🏗️ Architecture

```
Synthetic Logs → Ingestion API → Detection Engine → CrewAI Agents → Alert Store → Frontend API
```

### Components

1. **Log Generator** (`log_generator.py`)
   - Generates realistic security events every 1-3 seconds
   - Simulates login attempts, privilege escalation, data access

2. **Detection Engine** (`detection_engine.py`)
   - Rules-based threat detection
   - Detects: Brute force, suspicious logins, insider threats

3. **CrewAI Agent System** (`agents/crew_system.py`)
   - 5 specialized AI agents that collaborate:
     - **Ingestion Analyst**: Normalizes raw signals
     - **Threat Analyst**: Classifies threat types
     - **Context Enrichment**: Adds behavioral context
     - **Explanation Agent**: Writes human-readable explanations
     - **SOC Manager**: Makes final prioritization decisions

4. **FastAPI Backend** (`api.py`)
   - REST API for log ingestion and alert retrieval
   - Background processing of detection signals
   - Metrics and health check endpoints

5. **Storage** (`storage.py`)
   - In-memory storage with JSON persistence
   - Thread-safe operations
   - Automatic memory management

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (for CrewAI agents)
- Conda (recommended) or venv

### 1. Setup Environment

```bash
# Create conda environment (recommended)
conda create -n lokam python=3.11
conda activate lokam

# Or use venv
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-...
```

### 4. Start the Backend

```bash
# Start the API server
python api.py
```

The server will start on `http://localhost:8000`

### 5. Start Log Generation

In a separate terminal:

```bash
conda activate lokam  # or source venv/bin/activate
cd backend
python log_generator.py
```

---

## 📡 API Endpoints

### Ingestion

- `POST /logs` - Ingest security logs

### Frontend API

- `GET /alerts` - Get all alerts
  - Query params: `severity`, `limit`
- `GET /alerts/{id}` - Get specific alert
- `GET /metrics` - Get system metrics

### Debug (POC only)

- `GET /debug/logs` - View recent logs
- `GET /debug/signals` - View detection signals
- `POST /debug/clear` - Clear all data

### Health

- `GET /health` - Health check

---

## 🧪 Testing the Flow

1. **Start the backend**: `python api.py`
2. **Start log generator**: `python log_generator.py` (in new terminal)
3. **Watch the logs** - Generator will emit events
4. **Detection fires** - When patterns match (e.g., 5+ failed logins)
5. **Agents process** - CrewAI agents analyze the signal (~10-30s)
6. **Alert created** - Final alert available at `/alerts`

---

## 🎨 Data Models

### Security Log
```json
{
  "timestamp": "2026-01-20T12:01:22Z",
  "user": "john.doe@company.com",
  "event_type": "failed_login",
  "ip": "91.203.12.4",
  "location": "Russia",
  "asset": "customer-db"
}
```

### Alert
```json
{
  "alert_id": "uuid",
  "timestamp": "2026-01-20T12:05:00Z",
  "user": "john.doe@company.com",
  "threat_type": "SUSPICIOUS_LOGIN",
  "severity": "HIGH",
  "explanation": "User logged in from Russia for the first time...",
  "recommendation": "Verify user identity and reset credentials",
  "agent_trace": ["Ingestion Analyst", "Threat Analyst", ...],
  "raw_events": [...]
}
```

---

## 🤖 The AI Agent Workflow

When a detection signal is created:

1. **Ingestion Analyst** - Reviews and normalizes the signal
2. **Threat Analyst** - Classifies the threat type and severity
3. **Context Enrichment** - Adds behavioral context and deviations
4. **Explanation Agent** - Writes clear explanation and recommendations
5. **SOC Manager** - Makes final priority decision

Each agent has:
- A specific role and goal
- Domain expertise in its backstory
- A focused task
- Access to previous agents' analysis

---

## 📁 Project Structure

```
backend/
├── agents/
│   ├── __init__.py
│   └── crew_system.py      # CrewAI agent definitions
├── data/
│   └── alerts.json         # Persisted alerts
├── api.py                  # Main FastAPI application
├── detection_engine.py     # Rules-based detection
├── log_generator.py        # Synthetic log generator
├── models.py               # Pydantic data models
├── storage.py              # In-memory storage
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎯 Detection Rules

### 1. Brute Force
**Trigger**: >5 failed logins in 2 minutes  
**Severity**: HIGH

### 2. Suspicious Login
**Trigger**: Login from high-risk location (Russia, North Korea, Tor, etc.)  
**Severity**: HIGH

### 3. Insider Threat
**Trigger**: Privilege escalation followed by data download  
**Severity**: CRITICAL

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `OPENAI_MODEL` | Model for agent reasoning | gpt-4-turbo-preview |
| `API_HOST` | API server host | 0.0.0.0 |
| `API_PORT` | API server port | 8000 |

---

## 🐛 Debugging

### View Live Logs
```bash
curl http://localhost:8000/debug/logs
```

### View Detection Signals
```bash
curl http://localhost:8000/debug/signals
```

### Check Metrics
```bash
curl http://localhost:8000/metrics
```

### Clear All Data
```bash
curl -X POST http://localhost:8000/debug/clear
```

---

## ⚡ Performance Notes

- **Agent processing**: 10-30 seconds per alert (depends on OpenAI API latency)
- **Log throughput**: ~1-3 logs/second
- **Memory**: Stores last 1000 logs in memory
- **Persistence**: Alerts saved to `data/alerts.json`

---

## 🚫 Out of Scope (Intentionally)

- ❌ Authentication/authorization
- ❌ Production-grade scaling (Kafka, Redis, etc.)
- ❌ Real ML model training
- ❌ Cloud deployment
- ❌ Enterprise compliance

**This is a POC to demonstrate agentic reasoning, not a production SIEM.**

---

## 🎬 Demo Script

**5-Minute Demo Flow:**

1. **Show Architecture** (30s)
   - Diagram of log flow through agents

2. **Start System** (1 min)
   - Start backend
   - Start log generator
   - Show logs flowing

3. **Trigger Detection** (1 min)
   - Wait for suspicious pattern
   - Show detection signal created

4. **Show Agent Reasoning** (2 min)
   - Watch agent workflow in console
   - Explain each agent's role
   - Show collaboration

5. **Show Alert** (30s)
   - Pull alert from API
   - Highlight explanation quality
   - Show agent trace

**Key Pitch Lines:**
- "This is not alerting, this is *reasoning*"
- "Each alert is a mini SOC team"
- "Agents explain what junior analysts miss"

---

## 📝 License

MIT - This is a POC/demo project

---

## 🤝 Contributing

This is a proof-of-concept. Feel free to fork and experiment!

---

## 📧 Questions?

This backend is part of the **Arxis SOC POC** project.

**Built by**: Senior Backend Engineer  
**Stack**: Python 3.11 + FastAPI + CrewAI  
**Philosophy**: Clarity over complexity
