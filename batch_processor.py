#!/usr/bin/env python3
"""
ArthRaksha Dynamic Batch Processor
==================================
Streams 50 realistic events from the 10,000 dataset pool through the agentic recovery system.
Updates recovery_ledger, customers, and audit_log in real-time.
"""

import json
import random
import time
import os
import sys
import uuid
from pathlib import Path
import requests

BASE_URL = os.getenv("API_BASE", "http://localhost:8000")
DATA_PATH = Path(__file__).parent / "arthraksha" / "data" / "payment_failures_10k.json"
STATE_FILE = Path(__file__).parent / "arthraksha" / "data" / ".batch_cursor.json"

BATCH_SIZE = 50

def get_next_batch(count=BATCH_SIZE):
    """Fetches the next slice of events from the 10,000 pool."""
    if not DATA_PATH.exists():
        print(f"Dataset {DATA_PATH} not found!")
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        events_pool = json.load(f)

    # Track cursor across batch runs
    cursor = 0
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                cursor = json.load(f).get("cursor", 0)
        except Exception:
            cursor = 0

    if cursor + count > len(events_pool):
        cursor = 0  # loop around

    selected = events_pool[cursor : cursor + count]
    
    # Save next cursor
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"cursor": cursor + count}, f)
    except Exception:
        pass

    return selected

def main():
    print(f"Loading {BATCH_SIZE} events from 10K dataset pool...")
    batch_events = get_next_batch(BATCH_SIZE)
    print(f"Starting Agentic Recovery Pipeline for {len(batch_events)} failed payments...")
    print("=" * 65)

    success_count = 0
    tier_counts = {"T1": 0, "T2": 0, "T3": 0}
    outcomes = {"recovered": 0, "pending": 0, "escalated": 0, "written_off": 0}

    for idx, ev in enumerate(batch_events, 1):
        # Generate fresh unique payment_id for every run
        fresh_pid = f"pay_{uuid.uuid4().hex[:10]}"
        ev["payment_id"] = fresh_pid
        ev["event_id"] = f"evt_{uuid.uuid4().hex[:12]}"

        # Ensure realistic customer data
        cust = ev.get("customer", {})
        if not cust.get("email") or "example" in cust.get("email", ""):
            cust["email"] = os.getenv("RECEIVING_EMAIL", "jatinbadgal49@gmail.com")

        # For Loom demo proof: ensure 1 customer recovery email and 1 admin escalation email per batch
        if idx == 1:
            ev["error_code"] = "insufficient_funds"
            ev["agent_tier"] = "T2"
            ev["amount"] = 4999
        elif idx == 2:
            ev["error_code"] = "payment_risk_check_failed"
            ev["agent_tier"] = "T3"
            ev["amount"] = 150000

        payload = {
            "event_id": ev["event_id"],
            "payment_id": ev["payment_id"],
            "amount": ev["amount"],
            "currency": "INR",
            "error_code": ev["error_code"],
            "error_description": f"Payment failed due to {ev['error_code']}",
            "customer": cust,
            "complexity_score": 0.90 if idx == 2 else ev.get("complexity_score", 0.4),
            "recovery_probability": 0.05 if idx == 2 else ev.get("recovery_probability", 0.5),
            "send_email": True if idx == 1 else False,
            "preferred_channel": "email" if idx == 1 else "payment_link"
        }


        try:
            res = requests.post(f"{BASE_URL}/webhook/test", json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                tier = data.get("agent_tier", "T2")
                outcome = data.get("final_outcome", "pending")
                
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                success_count += 1
                
                cust_name = cust.get("name", "Customer")
                err = ev["error_code"][:18]
                print(f"[{idx:02d}/{BATCH_SIZE}] {fresh_pid} | ₹{ev['amount']:<6} | {err:<18} | {tier} → {outcome}")
            else:
                print(f"[{idx:02d}/{BATCH_SIZE}] ✗ HTTP {res.status_code}: {res.text[:80]}")
        except Exception as e:
            print(f"[{idx:02d}/{BATCH_SIZE}] ✗ Error: {e}")

        # Small pacing between calls for smooth streaming progress
        time.sleep(0.08)

    print("=" * 65)
    print(f"Batch Run Complete: {success_count}/{BATCH_SIZE} events processed successfully.")
    print(f"Tiers handled:  T1 (Auto-Retry): {tier_counts.get('T1', 0)} | T2 (LLM): {tier_counts.get('T2', 0)} | T3 (Escalate): {tier_counts.get('T3', 0)}")
    print(f"Outcomes:       Recovered: {outcomes.get('recovered', 0)} | Pending: {outcomes.get('pending', 0)} | Escalated: {outcomes.get('escalated', 0)}")

if __name__ == "__main__":
    main()
