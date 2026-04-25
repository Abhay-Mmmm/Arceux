"""
Arceux SOC - Unified Entry Point

This script orchestrates the entire Arceux SOC system:
1. Starts the FastAPI server with agent processing
2. Launches the synthetic log generator
3. Manages graceful shutdown

Run this single file to start the complete SOC simulation.
"""

import asyncio
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Optional
import uvicorn
import random
import requests

# Import all components
from models import SecurityLog
from log_generator import generate_log, INGESTION_URL

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global state
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

shutdown_event = threading.Event()
log_generator_thread: Optional[threading.Thread] = None
api_server_thread: Optional[threading.Thread] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Log Generator (Background Thread)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_log_generator():
    """
    Continuously generate and send synthetic logs.
    Runs in a background thread.
    """
    print("\n[LOG GENERATOR] Starting...")
    print(f"[TARGET] [LOG GENERATOR] Target: {INGESTION_URL}")
    print(f"[INTERVAL] [LOG GENERATOR] Interval: 1-3 seconds\n")
    
    log_count = 0
    
    # Wait for API to be ready
    time.sleep(3)
    
    while not shutdown_event.is_set():
        try:
            log = generate_log()
            
            # Print condensed log info
            print(f"[LOG] [{log_count + 1:04d}] {log['event_type']:20s} | {log['user']:30s} | {log['location']}")
            
            # Send to ingestion API
            try:
                response = requests.post(
                    INGESTION_URL,
                    json=log,
                    timeout=2
                )
                if response.status_code == 200:
                    log_count += 1
                    # Show if detection occurred
                    data = response.json()
                    if data.get("status") == "detected":
                        print(f"[DETECT] Detection: {data.get('signal_type')}")
            except requests.exceptions.RequestException:
                # API busy, minimal noise
                pass
            
            # Random interval
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            if not shutdown_event.is_set():
                print(f"[ERROR] [LOG GENERATOR] Error: {e}")
                time.sleep(1)
    
    print(f"\n[STOPPED] [LOG GENERATOR] Stopped. Total logs sent: {log_count}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Server (Background Thread)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_api_server():
    """
    Run the FastAPI server with uvicorn.
    Runs in a background thread.
    """
    print("\n[API SERVER] Starting on http://0.0.0.0:8000...")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=False  # Reduce noise
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shutdown Handler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n[SHUTDOWN] Shutdown signal received...")
    print("[WAITING] Stopping all components...\n")
    
    shutdown_event.set()
    
    # Give threads time to clean up
    time.sleep(2)
    
    print("[OK] All components stopped.")
    print("Bye! Arceux SOC shutdown complete.\n")
    sys.exit(0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Orchestrator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """
    Main entry point - starts all components.
    """
    global log_generator_thread, api_server_thread
    
    # Register signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
# Print banner
    print("""
    ====================================================
    =                                                   =
    =            [SHIELD] ARCEUX SOC - UNIFIED SYSTEM [SHIELD]   =
    =                                                   =
    =  AI-Native Security Operations Center            =
    =  Powered by CrewAI + FastAPI                     =
    =                                                   =
    =  Components:                                       =
    =    - FastAPI Backend (with agent processing)       =
    =    - Synthetic Log Generator                       =
    =    - Real-time Detection Engine                =
    =    - Multi-Agent AI Analysis                   =
    =                                                   =
    ====================================================
    """)
    
    print(f"[*] Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    
    # Start API server in background thread
    print("============================================================")
    print("[1] Launching API Server...")
    print("============================================================")
    
    api_server_thread = threading.Thread(target=run_api_server, daemon=True)
    api_server_thread.start()
    
    # Wait for API to initialize
    time.sleep(4)
    
    # Start log generator in background thread
    print("\n============================================================")
    print("[2] Launching Log Generator...")
    print("============================================================")
    
    log_generator_thread = threading.Thread(target=run_log_generator, daemon=True)
    log_generator_thread.start()
    
    # Print status
    print("\n============================================================")
    print("[OK] Arceux SOC is now running!")
    print("============================================================")
    print("\nAPI Endpoints:")
    print("   - Base:         http://localhost:8000")
    print("   - Alerts:       http://localhost:8000/alerts")
    print("   - Metrics:      http://localhost:8000/metrics")
    print("   - Real-time:    http://localhost:8000/metrics/realtime")
    print("   - Health:       http://localhost:8000/health")
    print("   - Docs:         http://localhost:8000/docs")
    print("   - Agents:       http://localhost:8000/agents/status")
    print("\nAI Agents:")
    print("   - Background processing active")
    print("   - Signals analyzed automatically")
    print("   - Check /alerts for AI-generated insights")
    print("\nTip: Open http://localhost:5173 for the frontend dashboard")
    print("\nPress Ctrl+C to stop all services")
    print("============================================================\n")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
