"""
Synthetic Log Generator for Arxis SOC POC

Generates realistic security event logs to simulate a live SOC environment.
Emits events every 1-3 seconds with randomized but believable patterns.
"""

import random
import time
from datetime import datetime, timezone
from typing import Dict, Any
import requests
import json

# Configuration
INGESTION_URL = "http://localhost:8000/logs"
EVENT_INTERVAL = (1, 3)  # seconds

# Synthetic Data Pools
USERS = [
    "john.doe@company.com",
    "sarah.chen@company.com",
    "mike.johnson@company.com",
    "alice.kumar@company.com",
    "bob.smith@company.com",
    "emma.wilson@company.com",
]

ASSETS = [
    "customer-db",
    "internal-wiki",
    "payment-gateway",
    "employee-records",
    "api-gateway",
    "admin-panel",
]

SAFE_LOCATIONS = ["United States", "Canada", "United Kingdom", "Germany", "Singapore"]

SUSPICIOUS_LOCATIONS = [
    "Russia",
    "North Korea",
    "Unknown",
    "Tor Exit Node",
    "Romania",
]

EVENT_TYPES = [
    "successful_login",
    "failed_login",
    "privilege_escalation",
    "data_download",
    "new_country_login",
]


def generate_ip() -> str:
    """Generate a random IP address."""
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


def generate_log() -> Dict[str, Any]:
    """
    Generate a single synthetic security log.
    
    Returns:
        Dict containing timestamp, user, event_type, ip, location, and asset
    """
    # Weighted event distribution (most events are benign)
    event_weights = [0.5, 0.25, 0.05, 0.15, 0.05]
    event_type = random.choices(EVENT_TYPES, weights=event_weights)[0]
    
    user = random.choice(USERS)
    asset = random.choice(ASSETS)
    
    # Location logic: suspicious events more likely from suspicious locations
    if event_type in ["failed_login", "new_country_login", "privilege_escalation"]:
        location = random.choices(
            SAFE_LOCATIONS + SUSPICIOUS_LOCATIONS,
            weights=[0.3, 0.3, 0.3, 0.3, 0.3, 0.4, 0.4, 0.4, 0.3, 0.3]
        )[0]
    else:
        location = random.choice(SAFE_LOCATIONS)
    
    log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "event_type": event_type,
        "ip": generate_ip(),
        "location": location,
        "asset": asset,
    }
    
    return log


def send_log(log: Dict[str, Any]) -> bool:
    """
    Send log to ingestion API.
    
    Args:
        log: The log event to send
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            INGESTION_URL,
            json=log,
            timeout=2
        )
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Failed to send log: {e}")
        return False


def run_generator():
    """Main loop: generate and send logs continuously."""
    print("🔥 Arxis Log Generator Started")
    print(f"📡 Sending logs to: {INGESTION_URL}")
    print(f"⏱️  Interval: {EVENT_INTERVAL[0]}-{EVENT_INTERVAL[1]}s\n")
    
    log_count = 0
    
    while True:
        try:
            log = generate_log()
            
            # Print to console for visibility
            print(f"[{log_count + 1:04d}] {log['timestamp'][:19]} | {log['event_type']:20s} | {log['user']:30s} | {log['location']}")
            
            # Send to ingestion API
            if send_log(log):
                log_count += 1
            
            # Random interval between events
            time.sleep(random.uniform(*EVENT_INTERVAL))
            
        except KeyboardInterrupt:
            print(f"\n\n✅ Generator stopped. Total logs sent: {log_count}")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    run_generator()
