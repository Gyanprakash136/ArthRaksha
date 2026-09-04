"""
ArthRaksha — Failure Classifier
=================================
Hybrid classifier: XGBoost (fast first-pass) + rule-based confidence gate.

How it works:
  1. RULE LAYER  — deterministic signals from error taxonomy
                   (source, stop_immediately, retry_recommended)
                   → handles HIGH-confidence cases instantly
  2. XGBOOST     — trained on behavioral + contextual features
                   → handles the rest with a confidence score
  3. LLM GATE    — if XGBoost confidence < threshold, flag for LLM
                   (handled by classifier/classifier.py, not here)

Classes:
  TECHNICAL      → auto_retry
  UNINTENTIONAL  → payment_link
  INTENTIONAL    → exit_survey_then_stop
  AMBIGUOUS      → llm_classify_then_act

Usage:
    classifier = FailureClassifier()
    classifier.train(batch_path)                   # one-time training
    result = classifier.predict(event)             # single event
    results = classifier.predict_batch(events)     # full batch
"""

import json
import pickle
import numpy as np
from pathlib import Path
from typing import Any

# ── lazy imports (only needed at runtime, not parse time) ──────────────────────
try:
    import xgboost as xgb
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent
DATA_DIR      = BASE_DIR / "data"
TAXONOMY_PATH = DATA_DIR / "error_taxonomy.json"
BATCH_PATH    = DATA_DIR / "payment_failures_batch.json"
MODEL_DIR     = BASE_DIR / "models"
MODEL_PATH    = MODEL_DIR / "xgb_classifier.pkl"
ENCODER_PATH  = MODEL_DIR / "label_encoders.pkl"

MODEL_DIR.mkdir(exist_ok=True)

# ── label mapping ──────────────────────────────────────────────────────────────
LABEL_TO_INT = {
    "TECHNICAL":    0,
    "UNINTENTIONAL": 1,
    "INTENTIONAL":  2,
    "AMBIGUOUS":    3,
}
INT_TO_LABEL = {v: k for k, v in LABEL_TO_INT.items()}

# ── rule-based certainty rules (applied BEFORE XGBoost) ───────────────────────
# These are deterministic — no ML needed.
HARD_RULES = {
    # source=gateway/razorpay + retry_recommended → definitely TECHNICAL
    "technical_sources": {"gateway", "razorpay", "issuer_bank"},
    # stop_immediately=True → definitely INTENTIONAL (fraud/chargeback)
    "stop_codes": {"payment_risk_check_failed"},
    # source=customer + these reasons → definitely UNINTENTIONAL
    "unintentional_reasons": {
        "insufficient_funds", "card_expired", "card_number_invalid",
        "incorrect_cvv", "incorrect_otp", "otp_expired", "otp_attempts_exceeded",
        "transaction_daily_limit_exceeded", "transaction_limit_exceeded",
        "transaction_frequency_limit_exceeded", "invalid_vpa",
        "authentication_failed", "payment_timed_out", "mandate_creation_expired",
        "bank_account_invalid", "payment_session_expired",
        "incorrect_atm_pin", "pin_attempts_exceeded",
    },
    # These always need LLM
    "always_ambiguous": {
        "payment_cancelled", "payment_declined",
        "mandate_creation_failed", "debit_instrument_blocked",
        "transaction_on_vpa_restricted", "authorisation_declined_by_psp",
    },
}

# ── confidence thresholds ──────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.70   # below this → flag for LLM review
RULE_CONFIDENCE      = 0.98   # rule-based decisions get this confidence


# ══════════════════════════════════════════════════════════════════════════════
#  Feature engineering
# ══════════════════════════════════════════════════════════════════════════════

# Categorical feature vocabularies
_SOURCE_MAP  = {"customer": 0, "gateway": 1, "razorpay": 2,
                "issuer_bank": 3, "beneficiary_bank": 4, "business": 5}
_CODE_MAP    = {"BAD_REQUEST_ERROR": 0, "GATEWAY_ERROR": 1, "SERVER_ERROR": 2}
_METHOD_MAP  = {"card": 0, "upi": 1, "netbanking": 2,
                "emandate": 3, "nach": 4, "wallet": 5}
_BANK_MAP    = {"SBI": 0, "HDFC": 1, "ICICI": 2, "Axis": 3, "Kotak": 4,
                "PNB": 5, "BOB": 6, "Canara": 7, "IndusInd": 8,
                "Yes": 9, "UNKNOWN": 10}


def _encode(val: str, mapping: dict, default: int = -1) -> int:
    return mapping.get(val, default)


def extract_features(event: dict) -> np.ndarray:
    """
    Convert one event dict → fixed-length feature vector for XGBoost.

    Feature index reference:
    0  error_source_encoded
    1  razorpay_code_encoded
    2  payment_method_encoded
    3  bank_encoded
    4  retry_recommended (0/1)
    5  stop_immediately (0/1)
    6  needs_llm (0/1)
    7  amount_rupees (log-scaled)
    8  tenure_months
    9  prior_failures
    10 engagement_score
    11 days_since_login
    12 churn_probability
    13 has_open_ticket (0/1)
    14 billing_cycle_count
    15 is_subscription_method (emandate/nach = 1)
    """
    err      = event.get("error", {})
    customer = event.get("customer", {})
    signals  = event.get("signals", {})

    source  = err.get("source", "gateway")
    code    = err.get("code", "BAD_REQUEST_ERROR")
    method  = event.get("payment_method", "card")
    bank    = event.get("bank", "UNKNOWN")

    amount  = event.get("amount_rupees", 0)
    log_amt = float(np.log1p(amount))

    is_sub_method = 1 if method in ("emandate", "nach") else 0

    features = [
        _encode(source, _SOURCE_MAP),
        _encode(code,   _CODE_MAP),
        _encode(method, _METHOD_MAP),
        _encode(bank,   _BANK_MAP),
        int(event.get("retry_recommended", False)),
        int(event.get("stop_immediately",  False)),
        int(event.get("needs_llm",         False)),
        log_amt,
        float(customer.get("tenure_months",    0)),
        float(customer.get("prior_failures",   0)),
        float(customer.get("engagement_score", 0.5)),
        float(customer.get("days_since_login", 7)),
        float(signals.get("churn_probability", 0.3)),
        int(customer.get("has_open_ticket",    False)),
        float(event.get("billing_cycle_count", 1)),
        float(is_sub_method),
    ]
    return np.array(features, dtype=np.float32)


def extract_batch_features(events: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Extract features and labels from a batch of events."""
    X, y = [], []
    for e in events:
        cat = e.get("error_category", "AMBIGUOUS")
        if cat not in LABEL_TO_INT:
            continue
        X.append(extract_features(e))
        y.append(LABEL_TO_INT[cat])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


# ══════════════════════════════════════════════════════════════════════════════
#  Rule layer
# ══════════════════════════════════════════════════════════════════════════════

def apply_hard_rules(event: dict) -> dict | None:
    """
    Apply deterministic rules before calling XGBoost.
    Returns a classification result dict if rule fires, else None.
    """
    err    = event.get("error", {})
    reason = event.get("error_reason", "")
    source = err.get("source", "")
    stop   = event.get("stop_immediately", False)
    retry  = event.get("retry_recommended", False)

    # Rule 1: stop_immediately flag → INTENTIONAL (fraud/risk)
    if stop or reason in HARD_RULES["stop_codes"]:
        return _make_result("INTENTIONAL", RULE_CONFIDENCE, "rule:stop_immediately", event)

    # Rule 2: gateway/razorpay source + retry → TECHNICAL
    if source in HARD_RULES["technical_sources"] and retry:
        return _make_result("TECHNICAL", RULE_CONFIDENCE, "rule:technical_source+retry", event)

    # Rule 3: known unintentional reason codes
    if reason in HARD_RULES["unintentional_reasons"]:
        return _make_result("UNINTENTIONAL", RULE_CONFIDENCE, "rule:known_unintentional_reason", event)

    # Rule 4: known ambiguous codes → skip XGBoost, send to LLM
    if reason in HARD_RULES["always_ambiguous"]:
        return _make_result("AMBIGUOUS", 0.50, "rule:always_ambiguous→llm", event)

    return None   # no rule fired → pass to XGBoost


def _make_result(
    label: str,
    confidence: float,
    method: str,
    event: dict,
) -> dict:
    """Build a standardised classification result dict."""
    signals = event.get("signals", {})
    return {
        "event_id":          event.get("event_id"),
        "subscription_id":   event.get("subscription_id"),
        "payment_id":        event.get("payment_id"),
        "error_reason":      event.get("error_reason"),
        "predicted_category": label,
        "confidence":        round(confidence, 4),
        "classification_method": method,
        "needs_llm_review":  label == "AMBIGUOUS" or confidence < CONFIDENCE_THRESHOLD,
        "recovery_path":     _category_to_recovery(label),
        "retry_recommended": event.get("retry_recommended", False),
        "stop_immediately":  event.get("stop_immediately",  False),
        "churn_probability": signals.get("churn_probability", 0.0),
        "recovery_ev_rupees": signals.get("recovery_ev_rupees", 0),
        "intervention_priority": signals.get("intervention_priority", "LOW"),
    }


def _category_to_recovery(category: str) -> str:
    mapping = {
        "TECHNICAL":    "auto_retry",
        "UNINTENTIONAL": "payment_link",
        "INTENTIONAL":  "exit_survey_then_stop",
        "AMBIGUOUS":    "llm_classify_then_act",
    }
    return mapping.get(category, "llm_classify_then_act")


# ══════════════════════════════════════════════════════════════════════════════
#  XGBoost classifier
# ══════════════════════════════════════════════════════════════════════════════

class FailureClassifier:
    """
    Hybrid payment failure classifier.

    Architecture:
        Rule layer → instant decisions for deterministic cases
        XGBoost    → probabilistic classification for grey areas
        LLM gate   → AMBIGUOUS or low-confidence cases flagged for LLM
    """

    def __init__(self):
        self.model: Any = None
        self.is_trained = False
        self._feature_names = [
            "error_source", "razorpay_code", "payment_method", "bank",
            "retry_recommended", "stop_immediately", "needs_llm",
            "log_amount", "tenure_months", "prior_failures",
            "engagement_score", "days_since_login", "churn_probability",
            "has_open_ticket", "billing_cycle_count", "is_subscription_method",
        ]

    # ── training ───────────────────────────────────────────────────────────────

    def train(self, batch_path: Path | str | None = None, verbose: bool = True) -> dict:
        """
        Train XGBoost on the generated batch.
        Returns training metrics dict.
        """
        if not XGB_AVAILABLE:
            raise ImportError("xgboost and scikit-learn are required. Run: pip install xgboost scikit-learn")

        batch_path = Path(batch_path or BATCH_PATH)
        if not batch_path.exists():
            raise FileNotFoundError(f"Batch not found: {batch_path}. Run data_generator.py first.")

        with open(batch_path) as f:
            batch = json.load(f)

        events = batch["events"]
        X, y   = extract_batch_features(events)

        if verbose:
            print(f"🏋️  Training on {len(X)} events, {X.shape[1]} features")
            for label, idx in LABEL_TO_INT.items():
                count = int((y == idx).sum())
                print(f"   {label:<15} {count:>3} samples")

        # Split — small dataset so we keep 90% for training
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )

        # XGBoost params — tuned for small imbalanced dataset
        params = {
            "objective":        "multi:softprob",
            "num_class":        len(LABEL_TO_INT),
            "n_estimators":     200,
            "max_depth":        4,
            "learning_rate":    0.1,
            "subsample":        0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 2,
            "gamma":            0.1,
            "reg_alpha":        0.1,
            "reg_lambda":       1.0,
            "random_state":     42,
            "eval_metric":      "mlogloss",
            "verbosity":        0,
        }

        self.model = xgb.XGBClassifier(**params)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )
        self.is_trained = True

        # ── evaluate ──
        y_pred     = self.model.predict(X_test)
        accuracy   = accuracy_score(y_test, y_pred)
        report     = classification_report(
            y_test, y_pred,
            target_names=list(LABEL_TO_INT.keys()),
            output_dict=True,
            zero_division=0,
        )

        if verbose:
            print(f"\n✅ Training complete — Accuracy: {accuracy:.2%}")
            print(classification_report(
                y_test, y_pred,
                target_names=list(LABEL_TO_INT.keys()),
                zero_division=0,
            ))
            self._print_feature_importance()

        # Save model
        self._save()

        return {
            "accuracy": accuracy,
            "report":   report,
            "n_train":  len(X_train),
            "n_test":   len(X_test),
        }

    def _print_feature_importance(self):
        if self.model is None:
            return
        importances = self.model.feature_importances_
        pairs = sorted(zip(self._feature_names, importances), key=lambda x: -x[1])
        print("\n📊 Feature Importances:")
        for name, imp in pairs[:8]:
            bar = "█" * int(imp * 40)
            print(f"   {name:<25} {bar} {imp:.4f}")

    # ── inference ──────────────────────────────────────────────────────────────

    def predict(self, event: dict) -> dict:
        """
        Classify one event.

        Pipeline:
            1. Apply hard rules (deterministic)
            2. If no rule fires → XGBoost
            3. If confidence < threshold → flag AMBIGUOUS for LLM
        """
        # Step 1: rule layer
        rule_result = apply_hard_rules(event)
        if rule_result is not None:
            return rule_result

        # Step 2: XGBoost
        if not self.is_trained:
            # try loading saved model
            loaded = self._load()
            if not loaded:
                # fallback: taxonomy-based rule only
                return self._taxonomy_fallback(event)

        features = extract_features(event).reshape(1, -1)
        proba    = self.model.predict_proba(features)[0]   # shape (4,)
        pred_idx = int(proba.argmax())
        confidence = float(proba[pred_idx])
        label    = INT_TO_LABEL[pred_idx]

        # Step 3: confidence gate
        if confidence < CONFIDENCE_THRESHOLD:
            label = "AMBIGUOUS"

        result = _make_result(label, confidence, "xgboost", event)
        result["xgb_probabilities"] = {
            INT_TO_LABEL[i]: round(float(p), 4) for i, p in enumerate(proba)
        }
        return result

    def predict_batch(self, events: list[dict]) -> list[dict]:
        """Classify a full batch. Returns list of result dicts."""
        return [self.predict(e) for e in events]

    def _taxonomy_fallback(self, event: dict) -> dict:
        """Last resort: use error_category from the event itself (pre-labeled data)."""
        cat = event.get("error_category", "AMBIGUOUS")
        return _make_result(cat, 0.60, "taxonomy_fallback", event)

    # ── persistence ────────────────────────────────────────────────────────────

    def _save(self):
        """Persist trained model to disk."""
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        print(f"💾 Model saved → {MODEL_PATH}")

    def _load(self) -> bool:
        """Load persisted model. Returns True if successful."""
        if not MODEL_PATH.exists():
            return False
        try:
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            self.is_trained = True
            return True
        except Exception:
            return False


# ══════════════════════════════════════════════════════════════════════════════
#  Batch scoring helper (used by the recovery agent)
# ══════════════════════════════════════════════════════════════════════════════

def classify_batch(batch_path: Path | str | None = None) -> dict:
    """
    Convenience function: load batch → train → classify all events.
    Returns full results dict with summary.
    """
    batch_path = Path(batch_path or BATCH_PATH)
    with open(batch_path) as f:
        batch = json.load(f)

    classifier = FailureClassifier()
    classifier.train(batch_path=batch_path, verbose=True)

    events  = batch["events"]
    results = classifier.predict_batch(events)

    # ── summary ──
    by_predicted = {}
    by_recovery  = {}
    needs_llm    = 0

    for r in results:
        cat = r["predicted_category"]
        rec = r["recovery_path"]
        by_predicted[cat] = by_predicted.get(cat, 0) + 1
        by_recovery[rec]  = by_recovery.get(rec, 0) + 1
        if r["needs_llm_review"]:
            needs_llm += 1

    print("\n── Classification Summary ──")
    for cat, cnt in by_predicted.items():
        print(f"   {cat:<15} {cnt:>3} → {_category_to_recovery(cat)}")
    print(f"\n   🤖 Needs LLM review: {needs_llm}")

    return {
        "batch_id":       batch["batch_id"],
        "total_events":   len(results),
        "classifications": results,
        "summary": {
            "by_predicted_category": by_predicted,
            "by_recovery_path":      by_recovery,
            "needs_llm_review":      needs_llm,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ArthRaksha — Failure Classifier")
    parser.add_argument("--train",  action="store_true", help="Train model on batch")
    parser.add_argument("--run",    action="store_true", help="Train + classify full batch")
    parser.add_argument("--batch",  type=str, default=None, help="Path to batch JSON")
    args = parser.parse_args()

    if args.train or args.run:
        if args.run:
            results = classify_batch(args.batch)
            print(f"\nDone. {results['total_events']} events classified.")
        else:
            c = FailureClassifier()
            c.train(args.batch, verbose=True)
    else:
        parser.print_help()
