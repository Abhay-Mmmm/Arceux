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
import warnings
from datetime import datetime, timezone
from typing import Optional
import uvicorn
import random

# litellm serializes Groq responses against OpenAI Pydantic models — field-count
# mismatches produce harmless UserWarnings that flood the console. Suppress them.
warnings.filterwarnings(
    "ignore",
    message="Pydantic serializer warnings",
    category=UserWarning,
    module="pydantic",
)

# Import all components
from models import SecurityLog
from log_generator import (
    generate_log,
    generate_brute_force_burst,
    generate_insider_threat_sequence,
    generate_lateral_movement_sequence,
    generate_coordinated_probe_sequence,
    generate_hub_asset_pressure_sequence,
    generate_ip_reuse_sequence,
    wait_for_server,
    _post_log,
    INGESTION_URL,
)

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

    # Wait for API to be ready before sending any logs
    wait_for_server()

    while not shutdown_event.is_set():
        try:
            # Attack sequence probabilities:
            #   15% → brute_force_burst        (7 rapid failed logins, same user)
            #   10% → insider_threat_sequence  (escalation → download, same user)
            #    8% → lateral_movement         (same IP → 3 users → IP_REUSE + LATERAL_MOVEMENT)
            #    7% → coordinated_probe        (3 IPs → same user → COORDINATED_PROBE)
            #    5% → hub_asset_pressure       (4 users → same asset → HUB_ASSET_PRESSURE)
            #    5% → ip_reuse                 (same IP → 3 users → IP_REUSE)
            #   50% → normal random log
            r = random.random()
            if r < 0.15:
                burst = generate_brute_force_burst()
                print(f"[BURST] Brute-force → {burst[0]['user']} from {burst[0]['location']}")
                for b_log in burst:
                    if shutdown_event.is_set():
                        break
                    if _post_log(b_log):
                        log_count += 1
                    time.sleep(0.4)
            elif r < 0.25:
                seq = generate_insider_threat_sequence()
                print(f"[SEQ] Insider threat → {seq[0]['user']} escalation + download")
                for s_log in seq:
                    if shutdown_event.is_set():
                        break
                    if _post_log(s_log):
                        log_count += 1
                    time.sleep(1.0)  # slight gap so timestamps are ordered
            elif r < 0.33:
                threading.Thread(
                    target=generate_lateral_movement_sequence, daemon=True
                ).start()
            elif r < 0.40:
                threading.Thread(
                    target=generate_coordinated_probe_sequence, daemon=True
                ).start()
            elif r < 0.45:
                threading.Thread(
                    target=generate_hub_asset_pressure_sequence, daemon=True
                ).start()
            elif r < 0.50:
                threading.Thread(
                    target=generate_ip_reuse_sequence, daemon=True
                ).start()
            else:
                log = generate_log()
                print(f"[LOG] [{log_count + 1:04d}] {log['event_type']:20s} | {log['user']:30s} | {log['location']}")
                if _post_log(log):
                    log_count += 1

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
=                                                  =
=          ARCEUX SOC  -  UNIFIED SYSTEM           =
=                                                  =
=  AI-Native Security Operations Center            =
=  Powered by CrewAI + FastAPI + Groq              =
=                                                  =
=  Components:                                     =
=    - FastAPI Backend (with agent processing)     =
=    - Synthetic Log Generator                     =
=    - Real-time Detection Engine                  =
=    - Multi-Agent AI Analysis                     =
=                                                  =
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
