"""
ArthRaksha — MCP Tool Definitions (Core Algorithms)
=====================================================
Wraps all algorithm modules as FastMCP tools so the LangGraph agent
can call them via the MCP protocol.

Tools exposed:
  classify_event          → XGBoost + rule-based classification
  check_stopping_rules    → compliance gate before any recovery action
  score_event             → EV + urgency scoring for one event
  rank_batch              → priority queue for full batch
  analyze_batch_anomalies → Isolation Forest + pattern detection
  get_recovery_path       → full decision: classify → stop-check → score

The agent imports and calls these directly (no HTTP needed for demo).
For production: expose via FastMCP server on a port.
"""

import json
import sys
from pathlib import Path
from typing import Any

# ── make arthraksha importable ─────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from algorithms.classifier_model import FailureClassifier, apply_hard_rules
from algorithms.stopping_rules   import StoppingRuleChecker, StoppingDecision
from algorithms.priority_scorer  import score_event, score_and_rank_batch
from algorithms.anomaly_detector import AnomalyDetector

try:
    from fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Fallback: plain functions still work, just no MCP server
    class FastMCP:
        def __init__(self, name): self.name = name
        def tool(self):
            def decorator(fn): return fn
            return decorator

# ── singletons (initialised once, reused across all tool calls) ────────────────
_classifier: FailureClassifier | None = None
_checker    = StoppingRuleChecker()
_detector   = AnomalyDetector()

mcp = FastMCP("arthraksha-algorithms")


def _get_classifier() -> FailureClassifier:
    """Lazy-load the classifier. Train if no saved model exists."""
    global _classifier
    if _classifier is None:
        _classifier = FailureClassifier()
        loaded = _classifier._load()
        if not loaded:
            # Train fresh on batch
            _classifier.train(verbose=False)
    return _classifier


# ══════════════════════════════════════════════════════════════════════════════
#  Tool 1: classify_event
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def classify_event(event: dict) -> dict:
    """
    Classify a single payment failure event into one of four categories:
      TECHNICAL / UNINTENTIONAL / INTENTIONAL / AMBIGUOUS

    Returns the classification result with:
      - predicted_category
      - confidence (0-1)
      - classification_method (rule / xgboost / taxonomy_fallback)
      - recovery_path (what the agent should do next)
      - needs_llm_review (True if confidence is low or category is AMBIGUOUS)
      - churn_probability
      - recovery_ev_rupees (expected value of recovering this payment)
      - intervention_priority (CRITICAL / HIGH / MEDIUM / LOW)

    Args:
        event: A payment failure event dict (from the batch or webhook)

    Example:
        result = classify_event(event)
        # result["recovery_path"] → "auto_retry" | "payment_link" | ...
    """
    clf = _get_classifier()
    return clf.predict(event)


# ══════════════════════════════════════════════════════════════════════════════
#  Tool 2: check_stopping_rules
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def check_stopping_rules(
    event:          dict,
    attempt_number: int,
    context:        dict | None = None,
) -> dict:
    """
    Check whether recovery should STOP before executing the next action.

    This is the compliance gate. Call this BEFORE every recovery action.

    Returns:
      - should_stop (bool)         — True = do NOT proceed
      - reason                     — why it was stopped
      - is_hard_stop (bool)        — True = no override possible (fraud/dispute)
      - escalate (bool)            — True = route to human agent
      - message                    — human-readable explanation

    Args:
        event:          The payment failure event dict
        attempt_number: Current attempt count (1-indexed)
        context:        Optional dict with:
                          recovery_path     (str)
                          retry_count       (int)
                          link_count        (int)
                          classification    (str)
                          survey_sent       (bool)
                          promise_broken_count (int)
                          merchant_recovery_enabled (bool)

    Example:
        decision = check_stopping_rules(event, attempt_number=2, context={
            "recovery_path": "auto_retry",
            "retry_count": 2,
            "classification": "TECHNICAL"
        })
        if decision["should_stop"]:
            # halt recovery, log reason
    """
    decision: StoppingDecision = _checker.evaluate(event, attempt_number, context)
    return decision.to_dict()


# ══════════════════════════════════════════════════════════════════════════════
#  Tool 3: score_event
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def score_single_event(event: dict, recovery_path: str | None = None) -> dict:
    """
    Score a single event for priority queue placement.

    Returns:
      - ev_rupees            — expected rupee value of successful recovery
      - urgency              — time-decay factor (1.0 = just failed, 0.5 = 48h old)
      - composite_score      — ev × urgency (use this for queue ordering)
      - priority             — CRITICAL / HIGH / MEDIUM / LOW
      - hours_since_failure  — how long ago the payment failed

    Args:
        event:         The payment failure event dict
        recovery_path: Override path (auto_retry / payment_link / etc.)

    Example:
        score = score_single_event(event, recovery_path="auto_retry")
        queue.insert_by(score["composite_score"])
    """
    return score_event(event, recovery_path)


# ══════════════════════════════════════════════════════════════════════════════
#  Tool 4: rank_batch
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def rank_batch(
    events:         list[dict],
    recovery_paths: dict | None = None,
) -> list[dict]:
    """
    Rank a full batch of events by composite priority score (highest first).

    Returns a list of ranking dicts, each containing:
      - rank (1 = most urgent)
      - event_id
      - composite_score
      - ev_rupees
      - priority
      - urgency
      - plan_tier
      - amount_rupees

    Args:
        events:         List of payment failure event dicts
        recovery_paths: Optional {event_id: recovery_path} override map

    Example:
        ranked = rank_batch(events)
        for item in ranked[:10]:
            print(f"#{item['rank']} {item['event_id']} — {item['priority']} — ₹{item['ev_rupees']}")
    """
    return score_and_rank_batch(events, recovery_paths)


# ══════════════════════════════════════════════════════════════════════════════
#  Tool 5: analyze_batch_anomalies
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def analyze_batch_anomalies(events: list[dict]) -> dict:
    """
    Run anomaly detection on a full batch.

    Detects:
      - Error concentration (one reason dominating the batch)
      - Merchant spikes (one merchant with abnormal failure volume)
      - Time bursts (30%+ failures in a 2-hour window)
      - High-value cluster anomalies (PREMIUM/ENTERPRISE plan spike)
      - Bank-specific technical pattern (one bank causing all TECHNICAL failures)
      - Per-event outliers (Isolation Forest, 5% contamination)

    Returns:
      - total_insights
      - by_severity (CRITICAL/HIGH/MEDIUM/INFO counts)
      - top_insight
      - all_insights (list of insight dicts with type, severity, title, detail, action)

    Args:
        events: List of payment failure event dicts

    Example:
        insights = analyze_batch_anomalies(events)
        if insights["by_severity"].get("CRITICAL"):
            alert_team(insights["top_insight"])
    """
    return _detector.summary(events)


# ══════════════════════════════════════════════════════════════════════════════
#  Tool 6: get_recovery_plan  (COMPOSITE — the main agent entry point)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_recovery_plan(event: dict, attempt_number: int = 1) -> dict:
    """
    Full decision pipeline for one event. The agent calls this first.

    Pipeline:
      1. classify_event        → predicted_category + recovery_path
      2. check_stopping_rules  → is this safe to attempt?
      3. score_single_event    → what priority is this?

    Returns a combined plan dict:
      {
        classification:   {...},   # from classify_event
        stopping:         {...},   # from check_stopping_rules
        scoring:          {...},   # from score_single_event
        decision:         str,     # "PROCEED" | "STOP" | "ESCALATE" | "NEEDS_LLM"
        next_action:      str,     # what the agent should do next
        agent_instruction: str,    # plain-English instruction for the LLM agent
      }

    Args:
        event:          The payment failure event dict
        attempt_number: Current attempt (1-indexed)

    Example:
        plan = get_recovery_plan(event)
        if plan["decision"] == "PROCEED":
            execute_action(plan["next_action"], event)
        elif plan["decision"] == "ESCALATE":
            escalate_to_human(event)
    """
    # Step 1: classify
    classification = classify_event(event)
    recovery_path  = classification["recovery_path"]

    # Step 2: stopping rules
    context = {
        "recovery_path":   recovery_path,
        "classification":  classification["predicted_category"],
        "retry_count":     max(0, attempt_number - 1),
        "link_count":      0,
        "survey_sent":     False,
        "promise_broken_count": 0,
        "merchant_recovery_enabled": True,
    }
    stopping = check_stopping_rules(event, attempt_number, context)

    # Step 3: score
    scoring = score_single_event(event, recovery_path)

    # Step 4: synthesise decision
    if stopping["should_stop"]:
        if stopping["escalate"]:
            decision       = "ESCALATE"
            next_action    = "escalate_to_human"
            instruction    = (
                f"STOP and escalate. Reason: {stopping['reason']}. "
                f"Hard stop: {stopping['is_hard_stop']}. "
                f"Do not retry. Create a human escalation ticket."
            )
        else:
            decision       = "STOP"
            next_action    = "write_off"
            instruction    = (
                f"STOP recovery. Reason: {stopping['reason']}. "
                f"Mark this event as written off in the audit trail."
            )
    elif classification["needs_llm_review"]:
        decision       = "NEEDS_LLM"
        next_action    = "llm_classify_then_act"
        instruction    = (
            f"Classification confidence is low ({classification['confidence']:.0%}) "
            f"or category is AMBIGUOUS. Use LLM to reason about this case. "
            f"Error: {event.get('error_reason')}. "
            f"Customer tenure: {event.get('customer', {}).get('tenure_months')} months. "
            f"Churn probability: {classification['churn_probability']:.0%}."
        )
    else:
        decision    = "PROCEED"
        next_action = recovery_path
        instruction = _build_proceed_instruction(classification, scoring, event)

    return {
        "event_id":           event.get("event_id"),
        "classification":     classification,
        "stopping":           stopping,
        "scoring":            scoring,
        "decision":           decision,
        "next_action":        next_action,
        "agent_instruction":  instruction,
    }


def _build_proceed_instruction(
    classification: dict,
    scoring:        dict,
    event:          dict,
) -> str:
    """Build a plain-English instruction for the LLM agent to follow."""
    cat      = classification["predicted_category"]
    path     = classification["recovery_path"]
    ev       = scoring["ev_rupees"]
    priority = scoring["priority"]
    customer = event.get("customer", {})
    reason   = event.get("error_reason", "unknown")
    lang     = customer.get("preferred_lang", "en")

    lang_note = " Use Hinglish (Hindi + English mix) in communications." if lang == "hi" else ""

    instructions = {
        "auto_retry": (
            f"[{priority}] TECHNICAL failure ({reason}). "
            f"Auto-retry this payment in {event.get('signals', {}).get('retry_delay_hours', 2)} hours. "
            f"No customer notification needed. Expected recovery value: ₹{ev:,}."
            f"{lang_note}"
        ),
        "payment_link": (
            f"[{priority}] UNINTENTIONAL failure ({reason}). "
            f"Generate a payment link and send to {customer.get('email')} / {customer.get('phone')}. "
            f"Expected recovery value: ₹{ev:,}. Link expires in 48 hours."
            f"{lang_note}"
        ),
        "exit_survey_then_stop": (
            f"[{priority}] INTENTIONAL churn suspected ({reason}). "
            f"Send exit survey to {customer.get('email')}. "
            f"Do NOT retry payment. Mark subscription for cancellation review. "
            f"Expected value if recovered: ₹{ev:,} — but recovery unlikely."
            f"{lang_note}"
        ),
    }
    return instructions.get(path, f"Execute {path} recovery for {reason}. EV: ₹{ev:,}.{lang_note}")


# ══════════════════════════════════════════════════════════════════════════════
#  Tool 7: process_full_batch  (batch processing entry point)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def process_full_batch(events: list[dict]) -> dict:
    """
    Process an entire batch: rank → classify → stop-check → build recovery plans.

    This is what the recovery agent calls at the start of a batch run.

    Returns:
      {
        total:          int,
        ranked:         list,      # full ranked event list
        plans:          list,      # recovery plan per event
        summary:        {
          by_decision:  dict,      # PROCEED/STOP/ESCALATE/NEEDS_LLM counts
          by_path:      dict,      # auto_retry/payment_link/etc. counts
          total_ev:     int,       # total expected value in rupees
          immediate_stops: int,
        },
        anomalies:      dict,      # batch-level anomaly insights
      }

    Args:
        events: List of payment failure event dicts
    """
    # 1. rank all events
    ranked = rank_batch(events)

    # 2. build recovery plans in priority order
    plans      = []
    by_decision = {}
    by_path    = {}
    total_ev   = 0

    # Process in priority order
    event_map = {e["event_id"]: e for e in events}
    for ranked_item in ranked:
        eid   = ranked_item["event_id"]
        event = event_map.get(eid)
        if not event:
            continue

        plan = get_recovery_plan(event, attempt_number=1)
        plans.append(plan)

        d = plan["decision"]
        p = plan["next_action"]
        by_decision[d] = by_decision.get(d, 0) + 1
        by_path[p]     = by_path.get(p, 0) + 1
        total_ev      += plan["scoring"].get("ev_rupees", 0)

    # 3. batch anomaly detection
    anomalies = analyze_batch_anomalies(events)

    return {
        "total":   len(events),
        "ranked":  ranked[:20],   # top 20 for display
        "plans":   plans,
        "summary": {
            "by_decision":     by_decision,
            "by_path":         by_path,
            "total_ev_rupees": total_ev,
            "immediate_stops": by_decision.get("STOP", 0),
            "needs_human":     by_decision.get("ESCALATE", 0),
            "needs_llm":       by_decision.get("NEEDS_LLM", 0),
            "auto_proceed":    by_decision.get("PROCEED", 0),
        },
        "anomalies": anomalies,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CLI: quick test of all tools
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    from pathlib import Path

    batch_path = ROOT / "data" / "payment_failures_batch.json"
    with open(batch_path) as f:
        batch = json.load(f)

    events = batch["events"]

    print("\n🔧 Testing all MCP tools...\n")

    # Test 1: classify_event
    result = classify_event(events[0])
    print(f"✅ classify_event:  {result['predicted_category']} "
          f"({result['confidence']:.0%} confidence, {result['classification_method']})")

    # Test 2: check_stopping_rules
    stop = check_stopping_rules(events[0], attempt_number=1)
    print(f"✅ check_stopping:  should_stop={stop['should_stop']}, reason={stop['reason']}")

    # Test 3: score_single_event
    score = score_single_event(events[0])
    print(f"✅ score_event:     EV=₹{score['ev_rupees']:,}, priority={score['priority']}, "
          f"urgency={score['urgency']:.3f}")

    # Test 4: get_recovery_plan (composite)
    plan = get_recovery_plan(events[0])
    print(f"✅ get_recovery_plan: decision={plan['decision']}, next={plan['next_action']}")
    print(f"   → {plan['agent_instruction'][:100]}...")

    # Test 5: process_full_batch
    print(f"\n⚙️  Running full batch ({len(events)} events)...")
    batch_result = process_full_batch(events)
    s = batch_result["summary"]
    print(f"\n✅ process_full_batch complete:")
    print(f"   PROCEED:    {s['auto_proceed']} events")
    print(f"   STOP:       {s['immediate_stops']} events")
    print(f"   ESCALATE:   {s['needs_human']} events")
    print(f"   NEEDS_LLM:  {s['needs_llm']} events")
    print(f"   Total EV:   ₹{s['total_ev_rupees']:,}")
    print(f"\n   Anomalies:  {batch_result['anomalies']['total_insights']} insights")
