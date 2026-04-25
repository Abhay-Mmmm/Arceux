#!/bin/bash

# Arxis SOC - Complete System Startup

echo "╔═══════════════════════════════════════════╗"
echo "║                                           ║"
echo "║          🛡️  ARXIS SOC SYSTEM 🛡️           ║"
echo "║                                           ║"
echo "║  Starting all components...               ║"
echo "║                                           ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Launch API server in background
echo "1️⃣  Starting API Server..."
python api.py &
API_PID=$!
echo "   ✅ API Server started (PID: $API_PID)"
sleep 3

# Launch log generator
echo ""
echo "2️⃣  Starting Log Generator..."
python log_generator.py &
GEN_PID=$!
echo "   ✅ Log Generator started (PID: $GEN_PID)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Arxis SOC is running!"
echo ""
echo "📡 API Server:     http://localhost:8000"
echo "📊 Metrics:        http://localhost:8000/metrics"
echo "🚨 Alerts:         http://localhost:8000/alerts"
echo "💚 Health:         http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop all services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Wait for interrupt
wait
