"""
ArthRaksha — Priority Scorer
==============================
Scores each failed payment by its EXPECTED RECOVERY VALUE (EV).

Formula:
    EV = ARPU × remaining_lifetime × (1 - churn_prob) × recovery_rate(path)

This score drives the intervention queue order — highest EV first.

Also computes:
  - Urgency score (time-decayed: older failures get deprioritised)
  - Composite score (EV × urgency)
  - Priority tier: CRITICAL / HIGH / MEDIUM / LOW
"""

from datetime import datetime, timezone
import math


# ── recovery rate estimates by path (from rbi_stats.json) ─────────────────────
RECOVERY_RATES = {
    "auto_retry":           0.65,
    "payment_link":         0.42,
    "exit_survey_then_stop": 0.05,
    "llm_classify_then_act": 0.48,
    "escalate_to_human":    0.30,
}

# ── plan ARPU + lifetime (rupees, months) ──────────────────────────────────────
PLAN_PROFILE = {
    "BASIC":      {"arpu": 299,  "lifetime": 8},
    "PRO":        {"arpu": 799,  "lifetime": 14},
    "PREMIUM":    {"arpu": 1999, "lifetime": 22},
    "ENTERPRISE": {"arpu": 9999, "lifetime": 36},
}

# ── priority tier thresholds (₹ EV) ───────────────────────────────────────────
PRIORITY_TIERS = [
    ("CRITICAL", 50_000),
    ("HIGH",     15_000),
    ("MEDIUM",    5_000),
    ("LOW",           0),
]

# ── urgency decay: value halves every N hours of delay ────────────────────────
URGENCY_HALF_LIFE_HOURS = 48.0


def _hours_since(iso_timestamp: str) -> float:
    """Return hours elapsed since an ISO-format UTC timestamp."""
    try:
        if iso_timestamp.endswith("Z"):
            iso_timestamp = iso_timestamp[:-1] + "+00:00"
        failed_at = datetime.fromisoformat(iso_timestamp)
        now       = datetime.now(timezone.utc)
        return max(0.0, (now - failed_at).total_seconds() / 3600)
    except Exception:
        return 0.0


def urgency_multiplier(failed_at: str) -> float:
    """
    Exponential time-decay urgency: 1.0 at failure, 0.5 at 48h, 0.25 at 96h.
    Score degrades — act quickly for maximum recovery.
    """
    hours = _hours_since(failed_at)
    return math.exp(-math.log(2) * hours / URGENCY_HALF_LIFE_HOURS)


def expected_value(
    plan_tier:        str,
    churn_probability: float,
    recovery_path:    str,
    tenure_months:    int = 0,
) -> int:
    """
    Compute expected recovery value in rupees.

    Args:
        plan_tier:         BASIC / PRO / PREMIUM / ENTERPRISE
        churn_probability: 0.0–1.0 estimated churn likelihood
        recovery_path:     auto_retry / payment_link / etc.
        tenure_months:     used to estimate remaining lifetime

    Returns:
        Expected rupee value of recovery (integer)
    """
    profile  = PLAN_PROFILE.get(plan_tier, PLAN_PROFILE["BASIC"])
    arpu     = profile["arpu"]
    lifetime = profile["lifetime"]

    # Remaining lifetime: full lifetime if new, decays as tenure grows
    remaining = max(1, lifetime - int(tenure_months * 0.5))

    # Probability of payment succeeding given recovery path
    rec_rate = RECOVERY_RATES.get(recovery_path, 0.30)

    # EV = ARPU × remaining months × P(stay) × P(recover)
    ev = arpu * remaining * (1 - churn_probability) * rec_rate
    return int(ev)


def priority_tier(ev_rupees: int) -> str:
    """Map an EV in rupees to a priority tier string."""
    for tier, threshold in PRIORITY_TIERS:
        if ev_rupees >= threshold:
            return tier
    return "LOW"


def composite_score(ev_rupees: int, failed_at: str) -> float:
    """
    Composite score for queue ordering:
        composite = EV × urgency_multiplier
    Higher score = more urgent to act on.
    """
    urgency = urgency_multiplier(failed_at)
    return round(ev_rupees * urgency, 2)


def score_event(event: dict, recovery_path: str | None = None) -> dict:
    """
    Score a single event. Returns a scoring dict to attach to the event.

    Args:
        event:         The payment failure event dict
        recovery_path: Override recovery path (if classifier has run)

    Returns:
        {ev_rupees, urgency, composite_score, priority, queue_rank_hint}
    """
    customer  = event.get("customer", {})
    signals   = event.get("signals", {})

    plan      = event.get("plan_tier", "BASIC")
    churn     = signals.get("churn_probability", 0.3)
    failed_at = event.get("failed_at", datetime.now(timezone.utc).isoformat())
    tenure    = customer.get("tenure_months", 0)
    path      = recovery_path or signals.get("recovery_path", "llm_classify_then_act")

    ev       = expected_value(plan, churn, path, tenure)
    urgency  = urgency_multiplier(failed_at)
    comp     = composite_score(ev, failed_at)
    tier     = priority_tier(ev)

    return {
        "ev_rupees":       ev,
        "urgency":         round(urgency, 4),
        "composite_score": comp,
        "priority":        tier,
        "hours_since_failure": round(_hours_since(failed_at), 1),
    }


def score_and_rank_batch(
    events: list[dict],
    recovery_paths: dict[str, str] | None = None,
) -> list[dict]:
    """
    Score and rank all events by composite score (highest first).

    Args:
        events:         List of event dicts
        recovery_paths: Optional {event_id: recovery_path} override map

    Returns:
        List of dicts: {event_id, rank, score, priority, ev_rupees, ...}
    """
    recovery_paths = recovery_paths or {}
    scored = []

    for event in events:
        eid  = event.get("event_id", "")
        path = recovery_paths.get(eid)
        s    = score_event(event, path)
        scored.append({
            "event_id":          eid,
            "subscription_id":   event.get("subscription_id"),
            "merchant_id":       event.get("merchant_id"),
            "plan_tier":         event.get("plan_tier"),
            "amount_rupees":     event.get("amount_rupees", 0),
            **s,
        })

    # Sort by composite score descending
    scored.sort(key=lambda x: x["composite_score"], reverse=True)

    # Add rank
    for i, s in enumerate(scored, start=1):
        s["rank"] = i

    return scored


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from pathlib import Path

    batch_path = Path(__file__).parent.parent / "data" / "payment_failures_batch.json"
    with open(batch_path) as f:
        batch = json.load(f)

    ranked = score_and_rank_batch(batch["events"])

    print("\n🎯 Priority Queue (Top 10)")
    print(f"{'Rank':<5} {'Event':<18} {'Plan':<10} {'EV ₹':<10} {'Priority':<10} {'Score':<12} {'Urgency'}")
    print("─" * 75)
    for r in ranked[:10]:
        print(
            f"{r['rank']:<5} {r['event_id']:<18} {r['plan_tier']:<10} "
            f"₹{r['ev_rupees']:<9,} {r['priority']:<10} "
            f"{r['composite_score']:<12.1f} {r['urgency']:.3f}"
        )

    tiers = {}
    for r in ranked:
        tiers[r["priority"]] = tiers.get(r["priority"], 0) + 1
    print(f"\n   Priority breakdown: {tiers}")
