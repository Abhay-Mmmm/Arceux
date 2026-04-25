# 🔗 Arxis Frontend-Backend Integration Guide

## ✅ Integration Complete

The frontend and backend are now fully connected with:
- Real-time data flow
- Automatic polling for updates
- Graceful fallback to mock data
- CORS properly configured

---

## 📡 Connection Details

### Backend API
- **URL**: `http://localhost:8000`
- **Port**: 8000
- **CORS**: Enabled for all origins (POC mode)

### Frontend
- **URL**: `http://localhost:5173` (Vite default)
- **Port**: 5173
- **Environment**: Configured via `.env.local`

---

## 🔌 Endpoints Connected

### 1. GET /alerts
**Frontend Usage**: Alerts page, Dashboard
**Poll Interval**:
- Alerts page: 10 seconds
- Dashboard: 15 seconds

**Response Transformation**:
```typescript
Backend → Frontend
{
  alert_id → id
  severity (CAPS) → severity (lowercase)
  threat_type → title (formatted)
  explanation → description
  agent_trace → trace (with timestamps)
}
```

### 2. GET /metrics
**Frontend Usage**: Dashboard (severity chart)
**Poll Interval**: 15 seconds

**Data Mapping**:
```typescript
alerts_by_severity.CRITICAL → Severity chart
alerts_by_severity.HIGH → Severity chart
alerts_by_severity.MEDIUM → Severity chart
alerts_by_severity.LOW → Severity chart
total_alerts → Total count
```

### 3. GET /health
**Frontend Usage**: Available via API service
**Purpose**: Health check, connection status

---

## 🎨 Features Implemented

### Alerts Page (`/alerts`)
✅ Real-time alert fetching
✅ Auto-refresh every 10 seconds
✅ Manual refresh button
✅ Backend connection indicator:
   - 🟢 "Live data from backend" (connected)
   - ⚠️ "Using demo data" (fallback)
✅ Last refresh timestamp
✅ Loading state during refresh
✅ Full alert detail view with agent trace

### Dashboard (`/`)
✅ Real-time metrics
✅ Dynamic severity chart
✅ Live high-priority alerts
✅ Auto-refresh every 15 seconds
✅ Graceful degradation to mock data

---

## 🚀 How to Run

### Option 1: Run Both Together

1. **Start Backend**:
```bash
cd backend
conda activate lokam
python api.py
```

2. **Start Frontend** (in new terminal):
```bash
# Frontend is already running via npm run dev
# Or restart: npm run dev
```

3. **Start Log Generator** (optional, for live data):
```bash
cd backend
conda activate lokam
python log_generator.py
```

### Option 2: One-Click Backend

```bash
cd backend
./start_all.sh  # Starts both API and log generator
```

---

## 🧪 Testing the Connection

### 1. Check Backend is Running
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}
```

### 2. Check Frontend Can Reach Backend
Open browser console on frontend:
```javascript
// Should show successful API calls
// Look for: "🟢 Live data from backend"
```

### 3. Trigger an Alert
Wait for log generator to create patterns that match detection rules:
- **Brute Force**: 6+ failed logins
- **Suspicious Location**: Login from Russia/North Korea
- **Insider Threat**: Privilege escalation + data download

### 4. Verify Data Flow
1. Backend console shows: `🚨 Detection: SUSPICIOUS_LOGIN for john.doe@company.com`
2. Agents process (20-30 seconds): `🤖 Processing signal...`
3. Alert created: `✅ Alert {id} created`
4. Frontend updates (within 10-15 seconds)

---

## 🔄 Data Flow Diagram

```
┌─────────────────────┐
│   Log Generator     │
│  (Synthetic Events) │
└──────────┬──────────┘
           │ POST /logs
           ▼
┌─────────────────────┐
│   Backend API       │
│  (Detection Engine) │
└──────────┬──────────┘
           │ CrewAI Agents
           │ Process Signal
           ▼
┌─────────────────────┐
│   Alert Store       │
│  (JSON + Memory)    │
└──────────┬──────────┘
           │ GET /alerts
           │ GET /metrics
           ▼
┌─────────────────────┐
│  Frontend Service   │
│  (Transform Data)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   React Components  │
│ (Dashboard, Alerts) │
└─────────────────────┘
```

---

## 🎯 API Service Features

### Automatic Transformation
The `services/api.ts` layer handles:
- **Case conversion**: `CRITICAL` → `critical`
- **Field mapping**: `alert_id` → `id`
- **Timestamp formatting**: ISO → "5 min ago"
- **Type safety**: Full TypeScript support

### Error Handling
- Failed backend requests fall back to mock data
- Console warnings for debugging
- No crashes, graceful degradation

### React Hooks (Optional)
```typescript
import { useAlerts } from '../services/api';

// Auto-polling with React hook
const { alerts, loading, error } = useAlerts({ 
  pollInterval: 5000 
});
```

---

## 📊 Current Configuration

### Environment Variables

**Frontend** (`.env.local`):
```env
VITE_API_URL=http://localhost:8000
```

**Backend** (`.env`):
```env
OPENAI_API_KEY=your-key-here
API_HOST=0.0.0.0
API_PORT=8000
```

### CORS Settings (Backend)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # All origins allowed (POC)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🐛 Troubleshooting

### "Using demo data (backend not connected)"

**Possible Causes**:
1. Backend not running
2. Wrong API URL
3. CORS blocked (unlikely with current config)
4. Network issue

**Solutions**:
```bash
# 1. Verify backend is running
curl http://localhost:8000/health

# 2. Check frontend env
cat .env.local
# Should show: VITE_API_URL=http://localhost:8000

# 3. Restart frontend if .env changed
npm run dev

# 4. Check browser console for errors
```

### No Alerts Appearing

**Possible Causes**:
1. No alerts in backend yet
2. Log generator not running
3. Detection rules not triggered

**Solutions**:
```bash
# Check if backend has alerts
curl http://localhost:8000/alerts

# If empty, start log generator
cd backend
python log_generator.py

# Wait 2-3 minutes for patterns to form
```

### Alerts Not Updating

**Possible Causes**:
1. Polling disabled
2. Browser tab inactive (some browsers throttle)

**Solutions**:
- Click manual refresh button
- Check browser console for errors
- Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)

---

## 🎨 Visual Indicators

### Connection Status
Frontend shows current data source:

**Connected**:
```
🟢 Live data from backend
Last refresh: 2:45:32 PM
```

**Fallback**:
```
⚠️ Using demo data (backend not connected)
Last refresh: 2:45:32 PM
```

---

## 🔐 Security Notes (POC)

⚠️ **Current configuration is for POC/demo only**:
- CORS allows all origins
- No authentication
- No rate limiting
- Plain HTTP (no HTTPS)

**For Production**, implement:
- Specific CORS origins
- JWT or OAuth authentication
- API rate limiting
- HTTPS/TLS
- Input validation
- SQL injection protection (if using DB)

---

## 📈 Performance

### Expected Latency
- **API calls**: 10-100ms (local)
- **Alert creation**: 10-30 seconds (AI agents)
- **UI updates**: 10-15 seconds (polling interval)

### Polling Configuration
- **Alerts page**: 10s (fast updates for active monitoring)
- **Dashboard**: 15s (balanced for overview)
- **Customizable** in component `useEffect`

---

## ✅ Integration Checklist

- [x] API service layer created (`services/api.ts`)
- [x] Backend endpoints tested
- [x] CORS configured
- [x] Alerts page connected
- [x] Dashboard connected
- [x] Data transformations working
- [x] Error handling implemented
- [x] Fallback to mock data
- [x] Real-time polling
- [x] Connection indicators
- [x] Manual refresh buttons
- [x] TypeScript types aligned

---

## 🎯 Next Steps

### Immediate
1. ✅ Start backend
2. ✅ Verify frontend connects
3. ✅ Generate some alerts
4. ✅ Watch data flow

### Optional Enhancements
- [ ] WebSocket for real-time push (instead of polling)
- [ ] Agent processing progress bar
- [ ] Toast notifications for new alerts
- [ ] Detailed error messages
- [ ] Retry logic with exponential backoff
- [ ] Service worker for offline support

---

## 📝 Files Modified/Created

### Frontend
```
src/
├── services/
│   └── api.ts               ← NEW: API service layer
├── pages/
│   ├── Alerts.tsx           ← MODIFIED: Real data
│   └── Dashboard.tsx        ← MODIFIED: Real data
.env.local                    ← NEW: API URL config
```

### Backend
```
backend/
├── api.py                    ← Already has CORS
├── models.py                 ← Data models
└── storage.py                ← Alert storage
```

---

## 🎉 Summary

Your frontend and backend are now **perfectly connected**!

- ✅ Data flows seamlessly
- ✅ Real-time updates every 10-15 seconds
- ✅ Graceful fallback when backend unavailable
- ✅ Visual indicators for connection status
- ✅ Type-safe API layer
- ✅ CORS properly configured

**The system is production-ready for POC/demo purposes!**

---

*Last Updated: 2026-01-20*
