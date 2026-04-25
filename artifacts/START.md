# 🚀 Arxis SOC - Complete System Startup Guide

## Quick Start (2 Steps)

### 1. Start Server (Backend)

```bash
cd server
conda activate lokam  # or your Python environment
python main.py
```

This single command starts:
- ✅ FastAPI server with AI agents (port 8000)
- ✅ Synthetic log generator (1-3s intervals)
- ✅ Real-time threat detection
- ✅ Background CrewAI processing

### 2. Start Client (Frontend)

```bash
# In a new terminal, from the root directory
cd client
npm run dev
```

Open: **http://localhost:5173**

---

## What You'll See

### Backend Terminal
- 🔥 Log generation (user events, logins, etc.)
- 🚨 Real-time detections (brute force, suspicious logins)
- 🤖 AI agent analysis (when threats are detected)
- ✅ Alert creation with AI explanations

### Frontend Dashboard
- 📊 System Heartbeat (real-time metrics from backend)
- 🚨 Live alerts with AI-generated explanations
- 💬 AI Analyst chat interface
- 📈 Threat distribution charts

---

## Stopping the System

**Backend:** Press `Ctrl+C` in the backend terminal
- All components shut down gracefully

**Frontend:** Press `Ctrl+C` in the frontend terminal

---

## Endpoints

Once running, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | Main dashboard |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Alerts | http://localhost:8000/alerts | List all AI-analyzed alerts |
| Metrics | http://localhost:8000/metrics | System metrics |
| Real-time | http://localhost:8000/metrics/realtime | Live component data |
| Health | http://localhost:8000/health | API health check |

---

## Requirements

### Backend
- Python 3.11+
- OpenAI API key (set in `backend/.env`)
- Dependencies: `pip install -r backend/requirements.txt`

### Frontend
- Node.js 18+
- Dependencies: `npm install`

---

## Troubleshooting

### Backend won't start
```bash
# Check Python environment
conda activate lokam
which python

# Verify dependencies
pip install -r backend/requirements.txt

# Check OpenAI key
cat backend/.env
```

### Frontend won't connect to backend
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check CORS settings in backend/api.py
# Should allow origin: http://localhost:5173
```

### No alerts appearing
- Wait 2-3 minutes for first detection
- Logs generate every 1-3 seconds
- Detection patterns trigger randomly
- AI processing takes 15-30 seconds per alert

---

## Demo Tips

To see the system in action:

1. **Watch the backend terminal** for detection events
2. **Refresh the dashboard** to see new alerts
3. **Click on alerts** to see AI explanations and agent trace
4. **Click on services** in System Heartbeat to see diagnostics
5. **Use the "System Check"** button to verify all components
6. **Type in the AI Analyst** chat to simulate commands

The system generates realistic security events and demonstrates:
- Real-time log processing
- Multi-agent AI threat analysis
- Human-readable security explanations
- Live system monitoring

---

**You're ready to experience the Arxis SOC!** 🛡️
