"""
ArthRaksha — Abstractions / Interfaces
========================================
All protocols and abstract types live here.
Every module IMPORTS FROM here, never from each other's concrete classes.

SOLID compliance:
  D — All high-level modules depend on these abstractions, not concretions.
  I — Each interface is narrow and focused on one consumer's needs.
  O — New implementations (e.g. swap XGBoost → neural net) don't touch call sites.
  L — All implementations honour the contracts defined here.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from enum import Enum


# ══════════════════════════════════════════════════════════════════════════════
#  Domain Value Objects
# ══════════════════════════════════════════════════════════════════════════════

class FailureCategory(str, Enum):
    TECHNICAL    = "TECHNICAL"
    UNINTENTIONAL = "UNINTENTIONAL"
    INTENTIONAL  = "INTENTIONAL"
    AMBIGUOUS    = "AMBIGUOUS"


class RecoveryPath(str, Enum):
    AUTO_RETRY             = "auto_retry"
    PAYMENT_LINK           = "payment_link"
    EXIT_SURVEY_THEN_STOP  = "exit_survey_then_stop"
    LLM_CLASSIFY_THEN_ACT  = "llm_classify_then_act"
    ESCALATE_TO_HUMAN      = "escalate_to_human"
    WRITE_OFF              = "write_off"


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class RoutingTier(str, Enum):
    T1_DETERMINISTIC = "T1"   # no LLM, pure tool chain
    T2_BOUNDED_LLM   = "T2"   # 1 LLM call, bounded options
    T3_REACT         = "T3"   # full bounded ReAct
    HITL             = "HITL" # unsafe → human immediately


class RecoveryCaseStatus(str, Enum):
    PENDING          = "PENDING"
    IN_PROGRESS      = "IN_PROGRESS"
    WAITING_PAYMENT  = "WAITING_PAYMENT"
    RECOVERED        = "RECOVERED"
    WRITTEN_OFF      = "WRITTEN_OFF"
    ESCALATED        = "ESCALATED"
    CHURNED          = "CHURNED"


class EventType(str, Enum):
    PAYMENT_FAILED       = "PAYMENT_FAILED"
    CHECKOUT_ABANDONED   = "CHECKOUT_ABANDONED"
    PROMISE_DUE          = "PROMISE_DUE"
    PROMISE_BROKEN       = "PROMISE_BROKEN"
    PAYMENT_SUCCESS      = "PAYMENT_SUCCESS"
    CUSTOMER_DISPUTED    = "CUSTOMER_DISPUTED"
    HITL_REQUIRED        = "HITL_REQUIRED"
    RECOVERY_COMPLETED   = "RECOVERY_COMPLETED"
    RECOVERY_FAILED      = "RECOVERY_FAILED"


class AgentDecision(str, Enum):
    PROCEED    = "PROCEED"
    STOP       = "STOP"
    ESCALATE   = "ESCALATE"
    NEEDS_LLM  = "NEEDS_LLM"


class AuditAction(str, Enum):
    CLASSIFIED         = "CLASSIFIED"
    STOPPING_CHECK     = "STOPPING_CHECK"
    RETRY_TRIGGERED    = "RETRY_TRIGGERED"
    PAYMENT_LINK_SENT  = "PAYMENT_LINK_SENT"
    SURVEY_SENT        = "SURVEY_SENT"
    ESCALATED          = "ESCALATED"
    RECOVERED          = "RECOVERED"
    WRITTEN_OFF        = "WRITTEN_OFF"
    LLM_CLASSIFIED     = "LLM_CLASSIFIED"
    PROMISE_LOGGED     = "PROMISE_LOGGED"
    PROMISE_BROKEN     = "PROMISE_BROKEN"
    EMAIL_SENT         = "EMAIL_SENT"


class AuditOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED  = "FAILED"
    PENDING = "PENDING"
    SKIPPED = "SKIPPED"


# ══════════════════════════════════════════════════════════════════════════════
#  Result Data Classes
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassificationResult:
    """Output of IClassifier.predict()"""
    event_id:              str
    subscription_id:       str
    payment_id:            str
    error_reason:          str
    predicted_category:    FailureCategory
    confidence:            float
    classification_method: str                # "rule" | "xgboost" | "llm" | "fallback"
    needs_llm_review:      bool
    recovery_path:         RecoveryPath
    retry_recommended:     bool
    stop_immediately:      bool
    churn_probability:     float
    recovery_ev_rupees:    int
    intervention_priority: Priority
    xgb_probabilities:     dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id":              self.event_id,
            "subscription_id":       self.subscription_id,
            "payment_id":            self.payment_id,
            "error_reason":          self.error_reason,
            "predicted_category":    self.predicted_category.value,
            "confidence":            round(self.confidence, 4),
            "classification_method": self.classification_method,
            "needs_llm_review":      self.needs_llm_review,
            "recovery_path":         self.recovery_path.value,
            "retry_recommended":     self.retry_recommended,
            "stop_immediately":      self.stop_immediately,
            "churn_probability":     self.churn_probability,
            "recovery_ev_rupees":    self.recovery_ev_rupees,
            "intervention_priority": self.intervention_priority.value,
            "xgb_probabilities":     self.xgb_probabilities,
        }


@dataclass
class StoppingDecision:
    """Output of IStoppingRule.evaluate()"""
    should_stop:  bool
    reason:       str | None = None
    is_hard_stop: bool = False
    message:      str  = ""
    escalate:     bool = False

    def to_dict(self) -> dict:
        from datetime import datetime, timezone
        return {
            "should_stop":  self.should_stop,
            "reason":       self.reason,
            "is_hard_stop": self.is_hard_stop,
            "message":      self.message,
            "escalate":     self.escalate,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }


@dataclass
class ScoringResult:
    """Output of IScorer.score()"""
    ev_rupees:         int
    urgency:           float
    composite_score:   float
    priority:          Priority
    hours_since_failure: float

    def to_dict(self) -> dict:
        return {
            "ev_rupees":          self.ev_rupees,
            "urgency":            round(self.urgency, 4),
            "composite_score":    self.composite_score,
            "priority":           self.priority.value,
            "hours_since_failure": round(self.hours_since_failure, 1),
        }


@dataclass
class AuditEntry:
    """Immutable audit record written to storage."""
    audit_id:        str
    event_id:        str
    action:          AuditAction
    outcome:         AuditOutcome
    created_at:      str
    subscription_id: str   = ""
    payment_id:      str   = ""
    merchant_id:     str   = ""
    batch_id:        str   = ""
    category:        str   = ""
    recovery_path:   str   = ""
    amount_rupees:   float = 0.0
    ev_rupees:       int   = 0
    attempt_number:  int   = 1
    stop_reason:     str   = ""
    escalated:       bool  = False
    agent_note:      str   = ""
    metadata:        dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        import json
        return {
            "audit_id":        self.audit_id,
            "event_id":        self.event_id,
            "action":          self.action.value,
            "outcome":         self.outcome.value,
            "created_at":      self.created_at,
            "subscription_id": self.subscription_id,
            "payment_id":      self.payment_id,
            "merchant_id":     self.merchant_id,
            "batch_id":        self.batch_id,
            "category":        self.category,
            "recovery_path":   self.recovery_path,
            "amount_rupees":   self.amount_rupees,
            "ev_rupees":       self.ev_rupees,
            "attempt_number":  self.attempt_number,
            "stop_reason":     self.stop_reason,
            "escalated":       self.escalated,
            "agent_note":      self.agent_note,
            "metadata":        json.dumps(self.metadata),
        }


@dataclass
class RoutingDecision:
    """Output of IRouter.route()"""
    tier:             RoutingTier
    complexity_score: float
    reason:           str
    ambiguity:        float = 0.0
    financial_risk:   float = 0.0
    policy_complexity: float = 0.0
    context_complexity: float = 0.0
    historical_failure: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tier":              self.tier.value,
            "complexity_score":  round(self.complexity_score, 4),
            "reason":            self.reason,
            "components": {
                "ambiguity":          round(self.ambiguity, 4),
                "financial_risk":     round(self.financial_risk, 4),
                "policy_complexity":  round(self.policy_complexity, 4),
                "context_complexity": round(self.context_complexity, 4),
                "historical_failure": round(self.historical_failure, 4),
            }
        }


@dataclass
class GroundingResult:
    """Output of IGroundingValidator.validate()"""
    is_grounded:  bool
    issues:       list[str] = field(default_factory=list)
    evidence:     list[str] = field(default_factory=list)
    action:       str = ""   # "continue" | "reject" | "hitl"

    def to_dict(self) -> dict:
        return {
            "is_grounded": self.is_grounded,
            "issues":      self.issues,
            "evidence":    self.evidence,
            "action":      self.action,
        }


@dataclass
class PolicyDecision:
    """Output of IPolicyEngine.authorize()"""
    authorized:     bool
    reason:         str  = ""
    violated_rules: list[str] = field(default_factory=list)
    override_ev:    int  = 0   # if EV justifies exception → HITL

    def to_dict(self) -> dict:
        return {
            "authorized":     self.authorized,
            "reason":         self.reason,
            "violated_rules": self.violated_rules,
            "override_ev":    self.override_ev,
        }


@dataclass
class DomainEvent:
    """A system event published to the event bus."""
    event_type:  EventType
    payload:     dict
    source:      str        # which component published it
    event_id:    str = ""
    created_at:  str = ""
    idempotency_key: str = ""

    def __post_init__(self):
        import uuid
        from datetime import datetime, timezone
        if not self.event_id:
            self.event_id = f"evt_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class RecoveryCase:
    """Business state of one recovery effort — separate from audit."""
    case_id:          str
    event_id:         str
    subscription_id:  str
    merchant_id:      str
    amount_at_risk:   float
    status:           RecoveryCaseStatus = RecoveryCaseStatus.PENDING
    amount_recovered: float = 0.0
    recovery_time_h:  float = 0.0
    strategy_used:    str   = ""
    tier_used:        str   = ""
    attempts:         int   = 0
    opened_at:        str   = ""
    closed_at:        str   = ""

    def to_dict(self) -> dict:
        return {
            "case_id":          self.case_id,
            "event_id":         self.event_id,
            "subscription_id":  self.subscription_id,
            "merchant_id":      self.merchant_id,
            "amount_at_risk":   self.amount_at_risk,
            "status":           self.status.value,
            "amount_recovered": self.amount_recovered,
            "recovery_time_h":  round(self.recovery_time_h, 2),
            "strategy_used":    self.strategy_used,
            "tier_used":        self.tier_used,
            "attempts":         self.attempts,
            "opened_at":        self.opened_at,
            "closed_at":        self.closed_at,
        }


@dataclass
class GatewayResponse:
    """Standard response from any IPaymentGateway operation."""
    success:    bool
    mode:       str          # "live" | "simulation"
    message:    str = ""
    data:       dict = field(default_factory=dict)
    error:      str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "mode":    self.mode,
            "message": self.message,
            "data":    self.data,
            "error":   self.error,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Protocols (I — narrow, focused, one consumer per interface)
# ══════════════════════════════════════════════════════════════════════════════

@runtime_checkable
class IClassifier(Protocol):
    """
    I — Only exposes predict(). Training is a separate concern.
    Consumer: mcp/tools.py, agents/recovery_agent.py
    """
    def predict(self, event: dict) -> ClassificationResult: ...
    def predict_batch(self, events: list[dict]) -> list[ClassificationResult]: ...


@runtime_checkable
class IClassifierTrainer(Protocol):
    """
    I — Separate from IClassifier. Only training code depends on this.
    Consumer: scripts, CLI, setup pipelines
    """
    def train(self, batch_path: str, verbose: bool = True) -> dict: ...
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...


@runtime_checkable
class IStoppingRule(Protocol):
    """
    O + I — Each rule is isolated. Add new rules without modifying existing ones.
    Consumer: StoppingRuleChecker
    """
    @property
    def name(self) -> str: ...
    def evaluate(
        self,
        event:          dict,
        attempt_number: int,
        context:        dict,
    ) -> StoppingDecision | None:
        """Return a decision to stop, or None to pass to next rule."""
        ...


@runtime_checkable
class IScorer(Protocol):
    """
    I — Only scoring. No classification, no stopping rules.
    Consumer: mcp/tools.py, agents/recovery_agent.py
    """
    def score(self, event: dict, recovery_path: str | None = None) -> ScoringResult: ...
    def rank(self, events: list[dict]) -> list[dict]: ...


@runtime_checkable
class IDetector(Protocol):
    """
    O — New detectors plug in without touching existing ones.
    Consumer: AnomalyDetector (now a registry, not a monolith)
    """
    @property
    def name(self) -> str: ...
    def detect(self, events: list[dict]) -> list[dict]: ...  # list of insight dicts


@runtime_checkable
class IAuditWriter(Protocol):
    """
    I — Separated from IAuditReader. Agent only needs to WRITE.
    Consumer: mcp/audit_tool.py write path, agents
    """
    def write(self, entry: AuditEntry) -> str: ...           # returns audit_id


@runtime_checkable
class IAuditReader(Protocol):
    """
    I — Separated from IAuditWriter. Dashboard only needs to READ.
    Consumer: dashboard API routes, reporting
    """
    def get_trail(self, event_id: str) -> list[AuditEntry]: ...
    def get_batch(self, batch_id: str) -> list[AuditEntry]: ...
    def get_summary(self, batch_id: str) -> dict: ...


@runtime_checkable
class IAuditStorage(IAuditWriter, IAuditReader, Protocol):
    """
    Full storage interface (writer + reader).
    Consumer: CompositeStorage
    """
    ...


@runtime_checkable
class IPaymentGateway(Protocol):
    """
    D — tools.py depends on this abstraction, not on Razorpay directly.
    Swap RazorpayGateway ↔ SimulatedGateway without changing call sites.
    Consumer: mcp/razorpay_tool.py, agents/executor
    """
    def trigger_retry(
        self, subscription_id: str, payment_id: str, merchant_id: str
    ) -> GatewayResponse: ...

    def send_payment_link(
        self,
        subscription_id: str,
        customer_email:  str,
        customer_phone:  str,
        customer_name:   str,
        amount_paise:    int,
        merchant_id:     str,
        expire_hours:    int = 48,
        preferred_lang:  str = "en",
    ) -> GatewayResponse: ...

    def cancel_subscription(
        self, subscription_id: str, merchant_id: str, reason: str
    ) -> GatewayResponse: ...

    def fetch_subscription(self, subscription_id: str) -> GatewayResponse: ...


@runtime_checkable
class INotifier(Protocol):
    """
    D — Email / SMS / WhatsApp are interchangeable notifiers.
    Consumer: mcp/email_tool.py, services/executor
    """
    def send_recovery_notification(
        self,
        customer_email:  str,
        customer_phone:  str,
        customer_name:   str,
        payment_link:    str,
        amount_rupees:   float,
        preferred_lang:  str = "en",
    ) -> bool: ...

    def send_survey_notification(
        self,
        customer_email: str,
        customer_name:  str,
        reason:         str,
    ) -> bool: ...


@runtime_checkable
class ILLMClient(Protocol):
    """
    D — LLM provider is swappable (HuggingFace, OpenAI, local).
    Consumer: models/llm.py, agents/recovery_agent.py
    """
    def classify_ambiguous(self, event: dict, history: list[dict]) -> ClassificationResult: ...
    def generate_hinglish_response(self, context: dict) -> str: ...
    def extract_promise(self, conversation_text: str) -> dict | None: ...


# ── New protocols from architecture v2 ────────────────────────────────────────

@runtime_checkable
class IRouter(Protocol):
    """
    Complexity/risk score router.
    Decides T1 / T2 / T3 / HITL based on event characteristics.
    NOT based on LLM confidence.
    Consumer: agents/risk_router.py, agents/graph.py
    """
    def route(self, event: dict) -> RoutingDecision: ...
    def compute_score(self, event: dict) -> float: ...


@runtime_checkable
class IRuntimeMonitor(Protocol):
    """
    Tracks ONLY observable execution properties.
    Does NOT judge semantic correctness (that's IGroundingValidator).
    Consumer: agents/supervisor.py
    """
    def check(self, agent_state: dict) -> dict:
        """
        Returns: {ok: bool, action: 'continue'|'stop'|'warn', reason: str}
        agent_state must contain:
          iteration_count, token_count, elapsed_ms,
          tool_call_count, same_action_count
        """
        ...


@runtime_checkable
class IGroundingValidator(Protocol):
    """
    Validates semantic correctness of agent's proposed action.
    Does NOT track execution metrics (that's IRuntimeMonitor).
    Consumer: agents/grounding_validator.py
    """
    def validate(
        self,
        proposed_action: str,
        evidence:        list[str],
        observations:    list[dict],
        policy_context:  dict,
    ) -> GroundingResult: ...


@runtime_checkable
class IPolicyEngine(Protocol):
    """
    Business authorization. Agents propose, policy authorizes.
    Consumer: agents/policy_engine.py, agents/graph.py
    """
    def authorize(self, action: str, event: dict, context: dict) -> PolicyDecision: ...
    def check_cooldown(self, event_id: str, action: str) -> bool: ...
    def check_contact_frequency(self, customer_id: str) -> bool: ...


@runtime_checkable
class IEventBus(Protocol):
    """
    Decoupled event pub/sub. Everything important is an event.
    Consumer: all components
    """
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: EventType, handler) -> None: ...


@runtime_checkable
class IRecoveryLedger(Protocol):
    """
    Business state of recovery cases. Separate from audit trail.
    Audit = history. Ledger = current state.
    Consumer: services/recovery_ledger.py, dashboard
    """
    def open_case(self, event: dict) -> RecoveryCase: ...
    def update_case(self, case_id: str, updates: dict) -> RecoveryCase: ...
    def close_case(self, case_id: str, outcome: RecoveryCaseStatus) -> None: ...
    def get_case(self, case_id: str) -> RecoveryCase | None: ...
    def get_summary(self) -> dict: ...


@runtime_checkable
class IOutcomeVerifier(Protocol):
    """
    Independently verifies payment/action outcomes.
    Don't trust action response alone — confirm externally.
    Consumer: services/outcome_verifier.py
    """
    def verify_payment(self, payment_id: str) -> dict: ...
    def verify_subscription(self, subscription_id: str) -> dict: ...


@runtime_checkable
class IIdempotencyStore(Protocol):
    """
    Prevents duplicate actions across retries/failures.
    Key format: RC_{event_id}:{action_type}:{attempt_number}
    Consumer: services/idempotency_store.py, all MCP tools
    """
    def is_duplicate(self, key: str) -> bool: ...
    def mark_executed(self, key: str, result: dict) -> None: ...
    def get_result(self, key: str) -> dict | None: ...


@runtime_checkable
class IPromiseTracker(Protocol):
    """
    Consumer: services/promise_tracker, agents
    """
    def log_promise(
        self, event_id: str, customer_id: str, promise_date: str, amount: float
    ) -> str: ...

    def check_broken_promises(self) -> list[dict]: ...
    def mark_fulfilled(self, promise_id: str) -> None: ...
