"""
ArthRaksha — Anomaly Detector
================================
Uses Isolation Forest to detect unusual payment failure patterns at BATCH level.

What it finds:
  1. Merchant-level anomalies (one merchant having 3× normal failure rate)
  2. Time-burst anomalies (spike of failures in a 1-hour window)
  3. Error-code concentration (one error dominating the batch unexpectedly)
  4. High-value cluster anomalies (premium plans failing in unusual patterns)

These insights are shown on the dashboard as "Batch Intelligence" cards
and can alert the merchant to infrastructure or fraud issues.

Usage:
    detector = AnomalyDetector()
    insights = detector.analyze_batch(events)
    for insight in insights:
        print(insight)
"""

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ── insight severity levels ────────────────────────────────────────────────────

class Severity:
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    INFO     = "INFO"


# ══════════════════════════════════════════════════════════════════════════════
#  Statistical helpers
# ══════════════════════════════════════════════════════════════════════════════

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def _zscore(value: float, mean: float, std: float) -> float:
    return (value - mean) / std if std > 0 else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  Rule-based pattern detectors (no ML needed for these)
# ══════════════════════════════════════════════════════════════════════════════

def detect_error_concentration(events: list[dict]) -> list[dict]:
    """
    Detect if one error reason dominates the batch (>40% share).
    Signals a systemic issue vs. random individual failures.
    """
    reasons = [e.get("error_reason", "unknown") for e in events]
    total   = len(reasons)
    counts  = Counter(reasons)
    insights = []

    for reason, count in counts.most_common(3):
        share = count / total
        if share > 0.40:
            insights.append({
                "type":     "error_concentration",
                "severity": Severity.HIGH if share > 0.60 else Severity.MEDIUM,
                "title":    f"Error spike: {reason}",
                "detail":   f"{count}/{total} failures ({share:.0%}) are '{reason}'. "
                            f"This may indicate a systemic bank or gateway issue — not individual customer problems.",
                "metric":   {"reason": reason, "count": count, "share": round(share, 3)},
                "action":   "Check gateway/bank status page. Consider pausing retries temporarily.",
            })

    return insights


def detect_merchant_concentration(events: list[dict]) -> list[dict]:
    """
    Detect if one merchant has a disproportionate share of failures.
    """
    merchants = [e.get("merchant_id", "unknown") for e in events]
    total     = len(merchants)
    counts    = Counter(merchants)
    insights  = []

    for mid, count in counts.most_common():
        share = count / total
        expected = 1 / max(len(counts), 1)  # equal share
        if share > expected * 2.5 and count > 5:
            insights.append({
                "type":     "merchant_concentration",
                "severity": Severity.HIGH,
                "title":    f"Merchant {mid}: abnormal failure volume",
                "detail":   f"Merchant {mid} accounts for {share:.0%} of all failures "
                            f"({count}/{total}). Expected ~{expected:.0%}. "
                            f"Possible integration issue or fraud vector.",
                "metric":   {"merchant_id": mid, "count": count, "share": round(share, 3)},
                "action":   "Review merchant integration logs. Contact merchant if issue persists.",
            })

    return insights


def detect_time_burst(events: list[dict]) -> list[dict]:
    """
    Detect if failures are concentrated in a short time window (burst pattern).
    Burst = >30% of failures in a 2-hour window.
    """
    # Parse timestamps
    times = []
    for e in events:
        ts = e.get("failed_at", "")
        try:
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            times.append(datetime.fromisoformat(ts))
        except Exception:
            pass

    if len(times) < 10:
        return []

    times.sort()
    total    = len(times)
    insights = []

    # Sliding 2-hour window
    for i, start in enumerate(times):
        window_end   = start.timestamp() + 7200  # 2 hours
        window_count = sum(1 for t in times if start.timestamp() <= t.timestamp() <= window_end)
        share        = window_count / total

        if share > 0.35 and window_count > 10:
            insights.append({
                "type":     "time_burst",
                "severity": Severity.HIGH if share > 0.5 else Severity.MEDIUM,
                "title":    "Failure burst detected",
                "detail":   f"{window_count} failures ({share:.0%} of batch) occurred "
                            f"in a 2-hour window around {start.strftime('%Y-%m-%d %H:%M UTC')}. "
                            f"This looks like a gateway outage rather than individual failures.",
                "metric":   {"burst_count": window_count, "window_start": str(start), "share": round(share, 3)},
                "action":   "Cross-check with gateway status. Consider bulk-retrying technical failures from this window.",
            })
            break   # report first burst only

    return insights


def detect_high_value_cluster(events: list[dict]) -> list[dict]:
    """
    Detect if PREMIUM/ENTERPRISE plan failures are spiking — higher business impact.
    """
    by_plan = Counter(e.get("plan_tier", "BASIC") for e in events)
    total   = len(events)
    insights = []

    premium_count = by_plan.get("PREMIUM", 0) + by_plan.get("ENTERPRISE", 0)
    premium_share = premium_count / total if total > 0 else 0

    # Expected premium share ~20% (15% PREMIUM + 5% ENTERPRISE)
    if premium_share > 0.35 and premium_count > 5:
        total_ev = sum(
            e.get("signals", {}).get("recovery_ev_rupees", 0)
            for e in events
            if e.get("plan_tier") in ("PREMIUM", "ENTERPRISE")
        )
        insights.append({
            "type":     "high_value_cluster",
            "severity": Severity.CRITICAL if premium_share > 0.50 else Severity.HIGH,
            "title":    "Premium plan failures elevated",
            "detail":   f"{premium_count} PREMIUM/ENTERPRISE failures ({premium_share:.0%} of batch). "
                        f"Combined recovery EV: ₹{total_ev:,}. Prioritise these immediately.",
            "metric":   {"count": premium_count, "share": round(premium_share, 3), "ev_rupees": total_ev},
            "action":   "Escalate premium failures to senior support. Consider proactive outreach.",
        })

    return insights


def detect_bank_pattern(events: list[dict]) -> list[dict]:
    """
    Detect if one bank is responsible for a disproportionate share of TECHNICAL failures.
    """
    technical = [e for e in events if e.get("error_category") == "TECHNICAL"]
    if len(technical) < 5:
        return []

    banks    = [e.get("bank", "UNKNOWN") for e in technical]
    counts   = Counter(banks)
    total    = len(technical)
    insights = []

    for bank, count in counts.most_common(2):
        share = count / total
        if share > 0.45 and count > 4:
            insights.append({
                "type":     "bank_technical_pattern",
                "severity": Severity.MEDIUM,
                "title":    f"{bank} Bank: elevated technical failures",
                "detail":   f"{count}/{total} technical failures ({share:.0%}) involve {bank} Bank. "
                            f"May indicate a CBS outage or maintenance window.",
                "metric":   {"bank": bank, "count": count, "share": round(share, 3)},
                "action":   f"Check {bank} Bank status. Delay retries for {bank} accounts by 4 hours.",
            })

    return insights


# ══════════════════════════════════════════════════════════════════════════════
#  Isolation Forest (ML anomaly per-event)
# ══════════════════════════════════════════════════════════════════════════════

def detect_event_level_anomalies(events: list[dict]) -> list[dict]:
    """
    Use Isolation Forest to find individual events that are statistically unusual
    compared to the rest of the batch.

    Features used:
      - amount_rupees (log)
      - churn_probability
      - engagement_score
      - tenure_months
      - prior_failures
      - days_since_login
    """
    if not SKLEARN_AVAILABLE or len(events) < 20:
        return []

    import numpy as np

    rows = []
    for e in events:
        cust    = e.get("customer", {})
        signals = e.get("signals", {})
        rows.append([
            math.log1p(e.get("amount_rupees", 0)),
            signals.get("churn_probability", 0.3),
            cust.get("engagement_score", 0.5),
            cust.get("tenure_months", 6),
            cust.get("prior_failures", 0),
            cust.get("days_since_login", 7),
        ])

    X = np.array(rows)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = IsolationForest(
        n_estimators=100,
        contamination=0.05,   # expect ~5% anomalies
        random_state=42,
    )
    preds  = clf.fit_predict(X_scaled)   # -1 = anomaly, 1 = normal
    scores = clf.score_samples(X_scaled) # lower = more anomalous

    anomalies = []
    for i, (pred, score) in enumerate(zip(preds, scores)):
        if pred == -1:
            e = events[i]
            anomalies.append({
                "type":     "event_anomaly",
                "severity": Severity.MEDIUM,
                "title":    f"Unusual event: {e.get('event_id')}",
                "detail":   f"Event {e.get('event_id')} ({e.get('error_reason')}) is statistically "
                            f"unusual compared to batch. Anomaly score: {score:.3f}. "
                            f"Plan: {e.get('plan_tier')}, Amount: ₹{e.get('amount_rupees')}.",
                "metric":   {
                    "event_id":      e.get("event_id"),
                    "anomaly_score": round(float(score), 4),
                    "error_reason":  e.get("error_reason"),
                    "plan_tier":     e.get("plan_tier"),
                },
                "action":   "Review manually before automated recovery.",
            })

    return anomalies


# ══════════════════════════════════════════════════════════════════════════════
#  Main detector class
# ══════════════════════════════════════════════════════════════════════════════

class AnomalyDetector:
    """Runs all anomaly detectors on a batch and returns structured insights."""

    def analyze_batch(self, events: list[dict]) -> list[dict]:
        """
        Run all detectors. Returns list of insight dicts sorted by severity.
        """
        insights = []
        insights += detect_error_concentration(events)
        insights += detect_merchant_concentration(events)
        insights += detect_time_burst(events)
        insights += detect_high_value_cluster(events)
        insights += detect_bank_pattern(events)
        insights += detect_event_level_anomalies(events)

        # Sort by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH:     1,
            Severity.MEDIUM:   2,
            Severity.INFO:     3,
        }
        insights.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return insights

    def summary(self, events: list[dict]) -> dict:
        """Returns a compact summary dict for dashboard cards."""
        insights = self.analyze_batch(events)

        by_severity = Counter(i["severity"] for i in insights)
        return {
            "total_insights": len(insights),
            "by_severity":    dict(by_severity),
            "top_insight":    insights[0] if insights else None,
            "all_insights":   insights,
        }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    batch_path = Path(__file__).parent.parent / "data" / "payment_failures_batch.json"
    with open(batch_path) as f:
        batch = json.load(f)

    detector = AnomalyDetector()
    summary  = detector.summary(batch["events"])

    print(f"\n🔍 Batch Anomaly Analysis")
    print(f"   Total insights: {summary['total_insights']}")
    print(f"   By severity:    {summary['by_severity']}")
    print()

    for insight in summary["all_insights"]:
        icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "INFO": "🔵"}.get(insight["severity"], "⚪")
        print(f"   {icon} [{insight['severity']}] {insight['title']}")
        print(f"      {insight['detail'][:120]}...")
        print(f"      → {insight['action']}\n")
