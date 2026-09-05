#!/usr/bin/env python3

import argparse
import asyncio
import json
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
import sqlite3

import httpx

# ── Indian name / data pools ──────────────────────────────────────────────────

FIRST_NAMES = [
    "Aarav", "Aditi", "Aditya", "Akash", "Amit", "Amrita",
    "Ananya", "Anjali", "Arjun", "Aryan", "Deepa", "Deepak",
    "Divya", "Gaurav", "Ishaan", "Karan", "Kavya", "Meera",
    "Mohit", "Nisha", "Pooja", "Priya", "Rahul", "Rajesh",
    "Rakesh", "Ravi", "Rohit", "Sakshi", "Shruti", "Sunita",
    "Suresh", "Tanvi", "Vikram", "Vishal", "Vivek", "Swati",
    "Neha", "Manish", "Sanjay", "Preeti",
]

LAST_NAMES = [
    "Agarwal", "Bhatt", "Chauhan", "Chowdhury", "Desai", "Dubey",
    "Gupta", "Iyer", "Jain", "Joshi", "Kapoor", "Khanna",
    "Kumar", "Mehta", "Mishra", "Nair", "Pandey", "Patel",
    "Rao", "Reddy", "Saxena", "Sharma", "Shukla", "Singh",
    "Srivastava", "Tiwari", "Varma", "Verma", "Yadav", "Shah",
]

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.co.in", "hotmail.com", "rediffmail.com",
    "outlook.com", "ymail.com",
]

# Razorpay error codes — exact matches from arthraksha/data/error_taxonomy.json
ERROR_CODES = {
    # TECHNICAL (30%) — auto-retry (T1)
    "gateway_technical_error":              "TECHNICAL",
    "bank_technical_error":                 "TECHNICAL",
    "bank_not_available":                   "TECHNICAL",
    "server_error":                         "TECHNICAL",
    "request_timed_out":                    "TECHNICAL",
    "upi_app_technical_error":              "TECHNICAL",
    "payment_declined_due_to_high_traffic": "TECHNICAL",

    # UNINTENTIONAL (56%) — LLM T2
    "insufficient_funds":                   "UNINTENTIONAL",
    "card_expired":                         "UNINTENTIONAL",
    "card_number_invalid":                  "UNINTENTIONAL",
    "incorrect_cvv":                        "UNINTENTIONAL",
    "incorrect_otp":                        "UNINTENTIONAL",
    "otp_attempts_exceeded":                "UNINTENTIONAL",
    "transaction_daily_limit_exceeded":     "UNINTENTIONAL",
    "authentication_failed":                "UNINTENTIONAL",
    "bank_account_invalid":                 "UNINTENTIONAL",
    "payment_session_expired":              "UNINTENTIONAL",
    "payment_timed_out":                    "UNINTENTIONAL",

    # INTENTIONAL (14%) — T3 escalate
    "payment_risk_check_failed":            "INTENTIONAL",
}

TECHNICAL_CODES     = [k for k, v in ERROR_CODES.items() if v == "TECHNICAL"]
UNINTENTIONAL_CODES = [k for k, v in ERROR_CODES.items() if v == "UNINTENTIONAL"]
INTENTIONAL_CODES   = [k for k, v in ERROR_CODES.items() if v == "INTENTIONAL"]

# ₹ amount pools by merchant type
AMOUNT_POOLS = {
    "saas":   [199, 299, 499, 699, 999, 1499, 1999, 2999, 4999],
    "d2c":    [349, 599, 799, 1199, 1599, 2199, 3499, 5999, 8999],
    "emi":    [2500, 5000, 7500, 10000, 15000, 20000, 25000],
    "edu":    [1000, 2000, 3000, 5000, 7500, 12000, 18000],
}

MERCHANT_TYPES = list(AMOUNT_POOLS.keys())

LTV_RANGES = {
    "high": (30000, 120000),   # High-value, T2 agent will be aggressive
    "mid":  (8000,  30000),
    "low":  (500,   8000),
}


def random_indian_name() -> tuple[str, str]:
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def random_phone() -> str:
    # Indian mobile: +91 9/8/7 XXXXXXXXX
    prefix = random.choice(["9", "8", "7"])
    digits = "".join([str(random.randint(0, 9)) for _ in range(9)])
    return f"+91 {prefix}{digits}"


def random_email(first: str, last: str) -> str:
    patterns = [
        f"{first.lower()}.{last.lower()}@{random.choice(EMAIL_DOMAINS)}",
        f"{first.lower()}{random.randint(1, 99)}@{random.choice(EMAIL_DOMAINS)}",
        f"{first[0].lower()}{last.lower()}@{random.choice(EMAIL_DOMAINS)}",
    ]
    return random.choice(patterns)


def random_ltv() -> int:
    tier = random.choices(["high", "mid", "low"], weights=[20, 50, 30])[0]
    lo, hi = LTV_RANGES[tier]
    return random.randint(lo, hi)


def make_event(index: int, error_distribution: list) -> dict:
    first, last = random_indian_name()
    merchant_type = random.choice(MERCHANT_TYPES)
    amount = random.choice(AMOUNT_POOLS[merchant_type])
    error_code = error_distribution[index]
    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    event_id = f"evt_{uuid.uuid4().hex[:14]}"

    return {
        "event_id":   event_id,
        "payment_id": payment_id,
        "amount":     amount,
        "error_code": error_code,
        "timestamp":  datetime.now().isoformat() + "Z",
        "customer": {
            "id":                 f"cust_{uuid.uuid4().hex[:8]}",
            "name":               f"{first} {last}",
            "contact":            random_phone(),
            "email":              random_email(first, last),
            "ltv_estimate":       random_ltv(),
            "opted_out_of_comms": random.random() < 0.05,  # 5% opted out
            "bank_issuer":        random.choice(["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak"]),
            "months_subscribed":  random.randint(1, 36),
        },
        "_meta": {
            "merchant_type": merchant_type,
            "sim_index":     index,
        },
    }


def build_distribution(n: int) -> list:
    """Build error code list matching 30/56/14 distribution."""
    n_tech  = round(n * 0.30)
    n_unint = round(n * 0.56)
    n_int   = n - n_tech - n_unint

    codes = (
        [random.choice(TECHNICAL_CODES)     for _ in range(n_tech)]  +
        [random.choice(UNINTENTIONAL_CODES) for _ in range(n_unint)] +
        [random.choice(INTENTIONAL_CODES)   for _ in range(n_int)]
    )
    random.shuffle(codes)
    return codes


# ── HTTP sender ───────────────────────────────────────────────────────────────

async def send_event(client: httpx.AsyncClient, host: str, event: dict, idx: int, total: int):
    """POST one event, print result."""
    try:
        db_path = Path(__file__).parent / "data" / "arthraksha.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO customers
            (customer_id, payment_id, name, email, phone, bank_issuer, months_subscribed, ltv_estimate, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["customer"]["id"],
            event["payment_id"],
            event["customer"]["name"],
            event["customer"]["email"],
            event["customer"]["contact"],
            event["customer"]["bank_issuer"],
            event["customer"]["months_subscribed"],
            event["customer"]["ltv_estimate"],
            event["timestamp"]
        ))
        conn.commit()
        conn.close()

        resp = await client.post(
            f"{host}/webhook/razorpay",
            json=event,
            timeout=45.0,      # Ollama can take 10-20s on first call
        )
        status = resp.status_code
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

        tier_hint = ""
        cat = ERROR_CODES.get(event["error_code"], "?")
        if cat == "TECHNICAL":    tier_hint = "T1·AUTO"
        elif cat == "UNINTENTIONAL": tier_hint = "T2·LLM "
        else:                     tier_hint = "T3·ESC "

        name = event["customer"]["name"]
        amt  = f"₹{event['amount']:,}"
        code = event["error_code"]
        msg  = body.get("message", "error" if status >= 400 else "ok")

        marker = "✓" if status == 200 else "✗"
        print(f"  {marker} [{idx+1:02d}/{total}] {tier_hint} | {name:<22} | {amt:>10} | {code:<30} | {msg}")
        return status == 200

    except httpx.TimeoutException:
        print(f"  ✗ [{idx+1:02d}/{total}] TIMEOUT — Ollama may be slow, retrying in 5s...")
        await asyncio.sleep(5)
        return False
    except Exception as e:
        print(f"  ✗ [{idx+1:02d}/{total}] ERROR: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="ArthRaksha Scenario Simulator")
    parser.add_argument("--events", type=int, default=80,
                        help="Number of events to simulate (default: 80)")
    parser.add_argument("--host", default="http://localhost:8000",
                        help="ArthRaksha backend URL (default: http://localhost:8000)")
    parser.add_argument("--concurrency", type=int, default=3,
                        help="Concurrent requests (default: 3, keep low for Ollama)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    n = args.events

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║            ArthRaksha Revenue Recovery — Scenario Simulator         ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Events:      {n:<55}║")
    print(f"║  Host:        {args.host:<55}║")
    print(f"║  LLM:         Ollama (llama3.2) via {args.host.split('//')[1]:<30}║")
    print(f"║  Concurrency: {args.concurrency:<55}║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    # Health check
    print("── Health check ────────────────────────────────────────────────────────")
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{args.host}/dashboard/metrics", timeout=5.0)
            r.raise_for_status()
        print("  ✓ ArthRaksha backend is up")
    except Exception as e:
        print(f"  ✗ Cannot reach {args.host}: {e}")
        print("    Start the backend first:")
        print("      cd /Users/gyanprakash09/Developer/ArthRaksha && source venv/bin/activate")
        print("      python -m uvicorn arthraksha.api.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    print()
    print(f"── Generating {n} events ({'~'+str(round(n*0.30))} T1 / {'~'+str(round(n*0.56))} T2 / {'~'+str(round(n*0.14))} T3) ────────")
    distribution = build_distribution(n)
    events = [make_event(i, distribution) for i in range(n)]

    print()
    print("── Firing events (T1·AUTO=auto-retry, T2·LLM=Ollama, T3·ESC=escalate) ─")
    start = time.time()
    success = 0
    failed  = 0

    # Process in small concurrent batches to avoid overwhelming Ollama
    semaphore = asyncio.Semaphore(args.concurrency)

    async def _bounded(client, event, i):
        async with semaphore:
            return await send_event(client, args.host, event, i, n)

    async with httpx.AsyncClient() as client:
        tasks = [_bounded(client, ev, i) for i, ev in enumerate(events)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if r is True:
            success += 1
        else:
            failed += 1

    elapsed = time.time() - start

    print()
    print("── Results ─────────────────────────────────────────────────────────────")
    print(f"  Sent:     {n}")
    print(f"  Success:  {success}")
    print(f"  Failed:   {failed}")
    print(f"  Duration: {elapsed:.1f}s  ({elapsed/n:.1f}s/event avg)")
    print()
    print("── Next steps ──────────────────────────────────────────────────────────")
    print(f"  Dashboard: http://localhost:8000")
    print(f"  Cases:     http://localhost:8000/dashboard/cases")
    print(f"  Emails:    cat arthraksha/docs/sent_emails.log")
    print()

asyncio.run(main())
