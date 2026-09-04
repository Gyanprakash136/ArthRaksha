import json
import random
import uuid
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from faker import Faker

# Paths
BASE_DIR = Path(__file__).parent
TAXONOMY_PATH = BASE_DIR / "error_taxonomy.json"
OUTPUT_PATH = BASE_DIR / "payment_failures_batch.json"

# Load taxonomy
with open(TAXONOMY_PATH, "r") as f:
    TAXONOMY = json.load(f)

# Constants
AMOUNTS = [499, 999, 1499, 1999, 2999, 4999, 9999]
BANK_CHOICES = ["HDFC", "SBI", "ICICI", "AXIS", "KOTAK", "YES", "OTHER"]
BANK_WEIGHTS = [22, 20, 18, 12, 10, 5, 13]

FREQUENCY_WEIGHTS = {
    "very_common": 5,
    "common": 3,
    "uncommon": 1,
    "rare": 0.3
}

def get_error_distribution():
    error_keys = []
    error_weights = []
    
    for code, details in TAXONOMY.get("error_codes", {}).items():
        freq = details.get("frequency", "uncommon")
        weight = FREQUENCY_WEIGHTS.get(freq, 1)
        error_keys.append(code)
        error_weights.append(weight)
        
    return error_keys, error_weights

def calculate_complexity_score(recovery_prob, ltv, months_subscribed, last_login_days_ago, missed_payments):
    base = 1.0 - recovery_prob
    if ltv > 20000:
        base -= 0.05
    if months_subscribed > 12:
        base -= 0.03
    if last_login_days_ago > 14:
        base += 0.08
    if missed_payments > 2:
        base += 0.05
        
    return max(0.1, min(0.95, base))

def generate_event(fake, error_keys, error_weights):
    error_code = random.choices(error_keys, weights=error_weights, k=1)[0]
    error_meta = TAXONOMY["error_codes"][error_code]
    
    amount = random.choice(AMOUNTS)
    months_subscribed = random.randint(1, 36)
    ltv = amount * months_subscribed
    
    on_time = random.randint(0, months_subscribed)
    missed = random.randint(0, min(5, months_subscribed - on_time))
    
    last_login_days_ago = random.choice([0, 1, 2, 3, 7, 14, 30])
    
    bank = random.choices(BANK_CHOICES, weights=BANK_WEIGHTS, k=1)[0]
    
    # Defaults in case fields are missing in old entries
    recovery_prob = error_meta.get("recovery_probability", 0.5)
    agent_tier = error_meta.get("agent_tier", "T2")
    category = error_meta.get("category", "AMBIGUOUS")
    
    complexity = calculate_complexity_score(
        recovery_prob=recovery_prob,
        ltv=ltv,
        months_subscribed=months_subscribed,
        last_login_days_ago=last_login_days_ago,
        missed_payments=missed
    )
    
    payment_methods = error_meta.get("applicable_methods", ["card", "upi", "netbanking"])
    method = random.choice(payment_methods) if payment_methods else "card"
    
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": "payment.failed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payment_id": f"pay_{uuid.uuid4().hex[:10]}",
        "merchant_id": f"merch_{uuid.uuid4().hex[:6]}",
        "amount": amount,
        "currency": "INR",
        "payment_method": method,
        "error_code": error_code,
        "error_category": category,
        "agent_tier": agent_tier,
        "recovery_probability": recovery_prob,
        "customer": {
            "customer_id": f"cust_{uuid.uuid4().hex[:8]}",
            "name": fake.name(),
            "email": fake.email(),
            "phone": f"+91{random.randint(7000000000, 9999999999)}",
            "months_subscribed": months_subscribed,
            "on_time_payments": on_time,
            "missed_payments": missed,
            "last_login_days_ago": last_login_days_ago,
            "ltv_estimate": ltv,
            "bank_issuer": bank
        },
        "complexity_score": round(complexity, 3),
        "recovery_action": None,
        "outcome": "pending",
        "attempts": 0
    }

def main():
    parser = argparse.ArgumentParser(description="ArthRaksha Data Generator")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--output", type=str, default=str(BASE_DIR / "payment_failures_10k.json"))
    args = parser.parse_args()
    
    random.seed(args.seed)
    fake = Faker("en_IN")
    Faker.seed(args.seed)
    
    error_keys, error_weights = get_error_distribution()
    
    events = [generate_event(fake, error_keys, error_weights) for _ in range(args.count)]
    
    # Guarantee at least 5 T3 cases
    t3_count = sum(1 for e in events if e["agent_tier"] == "T3")
    if t3_count < 5:
        needed = 5 - t3_count
        non_t3_indices = [i for i, e in enumerate(events) if e["agent_tier"] != "T3"]
        replace_indices = random.sample(non_t3_indices, needed)
        
        for idx in replace_indices:
            # Overwrite with payment_risk_check_failed
            events[idx]["error_code"] = "payment_risk_check_failed"
            events[idx]["error_category"] = "INTENTIONAL"
            events[idx]["agent_tier"] = "T3"
            events[idx]["recovery_probability"] = 0.08
            # Recompute complexity just in case
            events[idx]["complexity_score"] = calculate_complexity_score(
                0.08,
                events[idx]["customer"]["ltv_estimate"],
                events[idx]["customer"]["months_subscribed"],
                events[idx]["customer"]["last_login_days_ago"],
                events[idx]["customer"]["missed_payments"]
            )
            

    with open(args.output, "w") as f:
        json.dump(events, f, indent=2)
        
    # Calculate stats for summary
    total_at_risk = sum(e["amount"] for e in events)
    
    tier_stats = defaultdict(lambda: {"count": 0, "amount": 0})
    category_counts = defaultdict(int)
    error_counts = defaultdict(int)
    
    for e in events:
        t = e["agent_tier"]
        tier_stats[t]["count"] += 1
        tier_stats[t]["amount"] += e["amount"]
        
        category_counts[e["error_category"]] += 1
        error_counts[e["error_code"]] += 1
        
    top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    print("═══════════════════════════════")
    print("ArthRaksha — Batch Generated")
    print("═══════════════════════════════")
    print(f"Total events:     {args.count}")
    print(f"Total at risk:    ₹{total_at_risk:,}")
    print("\nBy Agent Tier:")
    
    t1_c = tier_stats.get("T1", {}).get("count", 0)
    t1_a = tier_stats.get("T1", {}).get("amount", 0)
    print(f"  T1 (auto retry):    {t1_c} cases  ₹{t1_a:,}")
    
    t2_c = tier_stats.get("T2", {}).get("count", 0)
    t2_a = tier_stats.get("T2", {}).get("amount", 0)
    print(f"  T2 (LLM):           {t2_c} cases  ₹{t2_a:,}")
    
    t3_c = tier_stats.get("T3", {}).get("count", 0)
    t3_a = tier_stats.get("T3", {}).get("amount", 0)
    print(f"  T3 (escalate):      {t3_c} cases  ₹{t3_a:,}")
    
    print("\nBy Category:")
    for cat in ["TECHNICAL", "UNINTENTIONAL", "AMBIGUOUS", "INTENTIONAL", "MERCHANT_FIX"]:
        cnt = category_counts.get(cat, 0)
        print(f"  {cat.ljust(18)}: {cnt} cases")
            
    print("\nTop 3 Error Codes:")
    for i, (err, cnt) in enumerate(top_errors, 1):
        print(f"  {i}. {err}: {cnt} cases")
    print("═══════════════════════════════")

if __name__ == "__main__":
    main()
