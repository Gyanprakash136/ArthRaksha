import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Thresholds
TIER_THRESHOLDS = {
    "T1_MAX": 0.35,
    "T2_MAX": 0.75,
    "T3_MAX": 0.85
}

STOPPING_RULES = {
    # Default max attempts before escalation
    "MAX_ATTEMPTS_DEFAULT": 3,
    # Tier 1: Deterministic retries hard ceiling (RBI TAT Circular DPSS.CO.PD No.629/02.01.014/2019-20)
    "T1_MAX_RETRIES": 3,
    # Tier 2: Customer engagement limits (TRAI TCCCPR 2018 Regulation compliance)
    "T2_MAX_CONTACT_ATTEMPTS": 2,          # Hard ceiling: max 2 communications per customer per 24h
    "T2_COOLDOWN_HOURS": 4,                 # Minimum 4 hours between recovery messages
    "TRAI_CALL_WINDOW_START": 9,            # 09:00 AM IST (strictly no customer outreach before)
    "TRAI_CALL_WINDOW_END": 21,             # 09:00 PM IST (strictly no customer outreach after)
    # Promise-to-Pay Expiry State Machine
    "PROMISE_EXPIRY_HOURS": 24,             # Deferred payment promises expire at T+24h
    # Fraud & Economic Thresholds
    "MIN_RECOVERY_AMOUNT": 100,             # Transactions < ₹100 written off (recovery cost > recovery value)
    "FRAUD_AUTO_HALT": True,                # 100% immediate cessation on payment_risk_check_failed
    "MIN_CONFIDENCE_SCORE": 0.20,           # Lower confidence halts execution and flags human ops
    "MAX_REASONING_STEPS": 3,
    "AGENT_TIMEOUT_SECONDS": 30,
    "LOW_CONFIDENCE_THRESHOLD": 0.15
}

RETRY_SCHEDULE_5XX = {
    "attempt_1_minutes": 1,
    "attempt_2_minutes": 2,
    "attempt_3_minutes": 5,
    "fallback_hours": 1
}

CACHE_SETTINGS = {
    "LTV_HIGH_THRESHOLD": 20000,
    "LTV_MID_THRESHOLD": 5000,
    "MIN_USE_COUNT_TO_TRUST": 3
}

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "huggingface")
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

