"""
Synthetic Log Generator for Arceux SOC POC

Generates realistic security event logs to simulate a live SOC environment.
Emits events every 1-3 seconds with randomized but believable patterns.
"""

import random
import time
from datetime import datetime, timezone
from typing import Dict, Any
import requests

# Configuration
INGESTION_URL = "http://localhost:8000/logs"
HEALTH_URL = "http://localhost:8000/health"
EVENT_INTERVAL = (1, 3)  # seconds

# Set at module import so the 30-second graph warmup guard works even when
# wait_for_server() is never called (e.g. when launched via main.py).
_server_start_time: float = time.time()

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


def wait_for_server(
    url: str = HEALTH_URL,
    timeout: int = 30,
    interval: float = 0.5,
) -> bool:
    """Poll the health endpoint until the server responds 200 or timeout expires."""
    global _server_start_time
    print("[LOG GENERATOR] Waiting for server to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                _server_start_time = time.time()
                print("[LOG GENERATOR] Server is ready. Starting.")
                return True
        except Exception:
            pass
        time.sleep(interval)
    print(
        f"[LOG GENERATOR] WARNING: Server did not respond within {timeout}s. Starting anyway."
    )
    return False


def generate_ip() -> str:
    """Generate a random IP address."""
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


def generate_brute_force_burst() -> list:
    """
    Generate 7 rapid failed logins from one user — guaranteed to trigger BRUTE_FORCE detection.
    All from the same IP and suspicious location to make the attack realistic.
    """
    target_user = random.choice(USERS)
    attack_ip = generate_ip()
    location = random.choice(SUSPICIOUS_LOCATIONS)
    asset = random.choice(ASSETS)

    return [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": target_user,
            "event_type": "failed_login",
            "ip": attack_ip,
            "location": location,
            "asset": asset,
        }
        for _ in range(7)
    ]


def generate_insider_threat_sequence() -> list:
    """
    Generate privilege_escalation immediately followed by data_download for
    the same user — guaranteed to trigger INSIDER_THREAT detection.
    """
    target_user = random.choice(USERS)
    location = random.choice(SAFE_LOCATIONS)
    asset = random.choice(["customer-db", "employee-records", "payment-gateway"])
    ip = generate_ip()

    return [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": target_user,
            "event_type": "privilege_escalation",
            "ip": ip,
            "location": location,
            "asset": asset,
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": target_user,
            "event_type": "data_download",
            "ip": ip,
            "location": location,
            "asset": asset,
        },
    ]


def _post_log(fields: Dict[str, Any], retries: int = 2) -> bool:
    """Post a single log event. Returns True on success, False after all retries exhausted."""
    log = {"timestamp": datetime.now(timezone.utc).isoformat(), **fields}
    for attempt in range(retries):
        try:
            resp = requests.post(INGESTION_URL, json=log, timeout=5)
            if resp.status_code == 200:
                if resp.json().get("status") == "detected":
                    print(f"[DETECT] Detection: {resp.json().get('signal_type')}")
                return True
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.5)
    print(
        f"[LOG GENERATOR] WARNING: Failed to post log after {retries} attempts — server may be unavailable"
    )
    return False


def generate_lateral_movement_sequence() -> None:
    """
    Same source IP authenticates as 3 distinct users — triggers:
      • IP Reuse at the 2nd login  (threshold: 2+ users from same IP)
      • Lateral Movement at the 3rd login  (threshold: 3+ users from same IP)

    Safe location prevents Suspicious Login rule from firing first and
    discarding the graph signal.
    """
    if time.time() - _server_start_time < 30:
        return

    shared_ip = generate_ip()
    users = random.sample(USERS, 3)
    location = random.choice(SAFE_LOCATIONS)
    asset = random.choice(ASSETS)

    print(f"[GRAPH-SEQ] Lateral movement → {users[0]} + {users[1]} + {users[2]} on {asset}")

    for user in users:
        _post_log({"user": user, "event_type": "successful_login",
                   "ip": shared_ip, "location": location, "asset": asset})
        time.sleep(0.5)


def generate_coordinated_probe_sequence() -> None:
    """
    3 distinct IPs each fire a failed_login against the same user — triggers:
      • Coordinated Probe at the 3rd probe  (threshold: 3+ distinct IPs → same user)

    3 failures stay below the Brute Force threshold (>5 per user in 2 min),
    so no rule-based signal fires first.
    """
    if time.time() - _server_start_time < 30:
        return

    target_user = random.choice(USERS)
    location = random.choice(SAFE_LOCATIONS)
    asset = random.choice(ASSETS)

    print(f"[GRAPH-SEQ] Coordinated probe → 3 IPs targeting {target_user}")

    for _ in range(3):
        _post_log({"user": target_user, "event_type": "failed_login",
                   "ip": generate_ip(), "location": location, "asset": asset})
        time.sleep(0.3)


def generate_hub_asset_pressure_sequence() -> None:
    """
    4 distinct users each download from the same high-value asset — triggers:
      • Hub Asset Pressure at the 3rd download  (threshold: 3+ users → same asset)

    All downloads go to the SAME asset, so the Data Exfiltration rule (which
    fires on 3+ DIFFERENT assets for one user) never triggers.
    """
    if time.time() - _server_start_time < 30:
        return

    hub_asset = random.choice(["customer-db", "employee-records"])
    users = random.sample(USERS, 4)
    location = random.choice(SAFE_LOCATIONS)

    print(f"[GRAPH-SEQ] Hub asset pressure → 4 users on {hub_asset}")

    for user in users:
        _post_log({"user": user, "event_type": "data_download",
                   "ip": generate_ip(), "location": location, "asset": hub_asset})
        time.sleep(0.3)


def generate_ip_reuse_sequence() -> None:
    """
    Same IP address is used to log in as 3 distinct users — triggers:
      • IP Reuse at the 2nd login  (threshold: 2+ distinct users from same IP)

    Uses a fresh random IP distinct from the lateral movement sequence, and
    safe locations so no rule fires before the graph signal can surface.
    """
    if time.time() - _server_start_time < 30:
        return

    shared_ip = generate_ip()
    users = random.sample(USERS, 3)
    location = random.choice(SAFE_LOCATIONS)
    asset = random.choice(ASSETS)

    print(f"[GRAPH-SEQ] IP reuse → 3 users from {shared_ip}")

    for user in users:
        _post_log({"user": user, "event_type": "successful_login",
                   "ip": shared_ip, "location": location, "asset": asset})
        time.sleep(0.4)


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


GRAPH_SEQUENCES = [
    generate_lateral_movement_sequence,
    generate_coordinated_probe_sequence,
    generate_hub_asset_pressure_sequence,
    generate_ip_reuse_sequence,
]

# Fire a graph attack sequence roughly every N normal logs
GRAPH_SEQUENCE_INTERVAL = 25


def run_generator():
    """Main loop: generate and send logs continuously."""
    wait_for_server()

    print("🔥 Arceux Log Generator Started")
    print(f"📡 Sending logs to: {INGESTION_URL}")
    print(f"⏱️  Interval: {EVENT_INTERVAL[0]}-{EVENT_INTERVAL[1]}s\n")

    log_count = 0
    next_graph_trigger = GRAPH_SEQUENCE_INTERVAL

    while True:
        try:
            # Periodically inject a graph attack sequence
            if log_count >= next_graph_trigger:
                seq_fn = random.choice(GRAPH_SEQUENCES)
                seq_fn()
                next_graph_trigger = log_count + GRAPH_SEQUENCE_INTERVAL

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
