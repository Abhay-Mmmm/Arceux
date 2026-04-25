# Arceux SOC — Startup Guide

**Last Updated:** 2026-04-25

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Groq API key — free at [console.groq.com](https://console.groq.com) *(optional — system works without it using template fallback)*

---

## 1. Backend Setup (first time only)

```bash
cd server

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `server/.env` and fill in your Groq key:
```
GROQ_API_KEY=your-key-here
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## 2. Start the Backend

```bash
cd server
python main.py
```

This single command starts everything:
- FastAPI server on **port 8000**
- Synthetic log generator (1–3 second intervals)
- Background CrewAI 6-agent processor (polls every 5s)
- Real-time threat detection engine

You'll see output like:
```
Background signal processor started
Log generator started
Uvicorn running on http://0.0.0.0:8000
```

---

## 3. Start the Frontend

```bash
cd client
npm install   # first time only
npm run dev
```

Open: **[http://localhost:5173](http://localhost:5173)**

---

## 4. Verify Everything Is Working

```bash
# API health check
curl http://localhost:8000/health
# → {"status":"healthy","service":"arceux-soc-backend",...}

# Check alerts after ~2 minutes
curl http://localhost:8000/alerts | python -m json.tool

# Check live agent status
curl http://localhost:8000/agents/status | python -m json.tool

# Check detection signals
curl http://localhost:8000/debug/signals
```

---

## Useful URLs

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Frontend dashboard |
| http://localhost:8000/docs | Interactive API docs (Swagger UI) |
| http://localhost:8000/alerts | All AI-analyzed alerts (JSON) |
| http://localhost:8000/agents/status | Live agent pipeline state |
| http://localhost:8000/metrics | System metrics summary |
| http://localhost:8000/metrics/realtime | Component health + latency history |
| http://localhost:8000/debug/signals | Detection signals (debug) |
| http://localhost:8000/debug/logs | Recent ingested logs (debug) |

---

## What to Expect

| Time from startup | Event |
|-------------------|-------|
| 0–30s | Logs start appearing in backend terminal |
| 1–2 min | First detection signal fires (brute force or suspicious login) |
| +5–30s | Agent pipeline runs; alert created and visible in frontend |
| Ongoing | New alerts every few minutes as patterns repeat |

Detection patterns that trigger alerts:
- **Brute Force**: Same user logs 6+ failed logins within 2 minutes
- **Suspicious Login**: Login from Russia, North Korea, Iran, Tor Exit Node, etc.
- **Insider Threat**: Same user does PRIVILEGE_ESCALATION then FILE_TRANSFER/DATA_ACCESS

---

## Stopping

Press `Ctrl+C` in the backend terminal. All threads (API server + log generator) shut down gracefully.

---

## Troubleshooting

**"No module named crewai" or similar**
```bash
pip install -r requirements.txt
```

**No alerts appearing after 3+ minutes**
```bash
# Check if signals are being detected
curl http://localhost:8000/debug/signals
# If "pending" count is > 0, agents are still processing (wait 30s)
# If 0, wait longer for detection patterns to form
```

**Frontend shows blank / can't reach backend**
```bash
curl http://localhost:8000/health
# If this fails, the backend isn't running — start it first
```

**Groq API errors in backend logs**
System falls back to template responses automatically. AI features still work — just without live LLM reasoning. Check `GROQ_API_KEY` in `server/.env`.

**To clear all data and start fresh:**
```bash
curl -X POST http://localhost:8000/debug/clear
```

---

## Demo Tips

1. **Watch the backend terminal** — detections print in real time
2. **Agent Insights page** — click "Run on Latest Alert" to manually trigger the pipeline and watch agents go idle → running → completed
3. **Alerts page** — click any alert to see the full 6-agent reasoning trace
4. **Dashboard chat** — ask "What's the latest threat?" or click quick-action buttons
