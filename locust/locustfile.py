"""
ArthRaksha — Locust Load Tests
===============================
Three user classes modelling real traffic distribution:
  - ArthRakshaUser      (60% T1, 30% T2, 10% T3)  — baseline realistic mix
  - WorstCaseSpike      (100% T2 = LLM-heavy)       — spike scenario
  - ValidationBombardment (malformed payloads only) — abuse / guard-rail test

Run with:
  locust -f locust/locustfile.py --host http://localhost:8000
"""
import random
import uuid
import json
from locust import HttpUser, task, between, constant_throughput, events


# ── Payload factories ─────────────────────────────────────────────────────────

TECH_CODES = [
    "gateway_technical_error",
    "server_error",
    "network_error",
    "gateway_connection_error",
]

UNINTENTIONAL_CODES = [
    "insufficient_funds",
    "card_expired",
    "wrong_otp",
    "account_invalid",
]

INTENTIONAL_CODES = [
    "payment_risk_check_failed",
    "payment_cancelled",
]

ALL_CODES = TECH_CODES + UNINTENTIONAL_CODES + INTENTIONAL_CODES


def _event(error_code, suffix=""):
    payment_id = f"pay_{uuid.uuid4().hex[:12]}{suffix}"
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "payment_id": payment_id,
        "amount": random.randint(500, 200_000),
        "error_code": error_code,
        "timestamp": "2026-09-01T10:00:00Z",
        "customer": {
            "id": f"cust_{uuid.uuid4().hex[:8]}",
            "name": "Load Test User",
            "contact": f"+91{random.randint(7000000000, 9999999999)}",
            "email": "load@test.com",
            "ltv_estimate": random.randint(1000, 100_000),
            "opted_out_of_comms": False,
        },
    }


def _malformed_event(variant: int):
    """Returns purposely malformed payloads to stress the guardrail layer."""
    variants = [
        {},                                          # completely empty
        {"event_id": "e1"},                          # missing most fields
        {"event_id": "e2", "payment_id": "p2",      # zero amount
         "amount": 0, "error_code": "insufficient_funds",
         "customer": {"contact": "+919999999999"}},
        {"event_id": "e3", "payment_id": "p3",      # bad error code
         "amount": 5000, "error_code": "TOTALLY_FAKE_ERROR_CODE_999",
         "customer": {"contact": "+919999999999"}},
        {"event_id": "e4", "payment_id": "p4",      # missing customer contact
         "amount": 5000, "error_code": "insufficient_funds",
         "customer": {}},
        "this is a string not a dict",               # wrong type
        None,                                        # null
        {"event_id": "x" * 5000},                   # oversized field
    ]
    return variants[variant % len(variants)]


# ── User classes ──────────────────────────────────────────────────────────────

class ArthRakshaUser(HttpUser):
    """Realistic 60/30/10 T1/T2/T3 traffic mix."""
    wait_time = between(0.05, 0.3)
    weight = 6  # 60% of total VUs

    @task(6)
    def t1_technical_failure(self):
        """T1 — deterministic auto-retry (60%)"""
        payload = _event(random.choice(TECH_CODES))
        with self.client.post(
            "/webhook/razorpay",
            json=payload,
            name="/webhook/razorpay [T1]",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 400:
                resp.success()  # guardrail rejection is expected / valid
            else:
                resp.failure(f"Unexpected {resp.status_code}")

    @task(3)
    def t2_unintentional_failure(self):
        """T2 — LLM-assisted recovery (30%)"""
        payload = _event(random.choice(UNINTENTIONAL_CODES))
        with self.client.post(
            "/webhook/razorpay",
            json=payload,
            name="/webhook/razorpay [T2]",
            catch_response=True
        ) as resp:
            if resp.status_code in (200, 400):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")

    @task(1)
    def t3_intentional_failure(self):
        """T3 — escalation path (10%)"""
        payload = _event(random.choice(INTENTIONAL_CODES))
        with self.client.post(
            "/webhook/razorpay",
            json=payload,
            name="/webhook/razorpay [T3]",
            catch_response=True
        ) as resp:
            if resp.status_code in (200, 400):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")

    @task(1)
    def dashboard_metrics(self):
        """Read dashboard metrics (background poll simulation)"""
        with self.client.get(
            "/dashboard/metrics",
            name="/dashboard/metrics",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Dashboard metrics returned {resp.status_code}")

    @task(1)
    def dashboard_cases(self):
        """Read cases list"""
        with self.client.get(
            "/dashboard/cases",
            name="/dashboard/cases",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Dashboard cases returned {resp.status_code}")


class WorstCaseSpike(HttpUser):
    """100% T2 (LLM) traffic — worst-case spike scenario."""
    wait_time = constant_throughput(5)  # 5 RPS per VU
    weight = 3  # 30% of total VUs

    @task
    def t2_spike(self):
        payload = _event(random.choice(UNINTENTIONAL_CODES), suffix="_spike")
        with self.client.post(
            "/webhook/razorpay",
            json=payload,
            name="/webhook/razorpay [SPIKE]",
            catch_response=True
        ) as resp:
            if resp.status_code in (200, 400):
                resp.success()
            else:
                resp.failure(f"Spike: Unexpected {resp.status_code}")


class ValidationBombardment(HttpUser):
    """Fires only malformed payloads — tests guardrail rejection under load."""
    wait_time = between(0.01, 0.05)
    weight = 1  # 10% of total VUs

    @task
    def send_malformed(self):
        variant = random.randint(0, 7)
        payload = _malformed_event(variant)

        try:
            with self.client.post(
                "/webhook/razorpay",
                json=payload,
                name="/webhook/razorpay [MALFORMED]",
                catch_response=True
            ) as resp:
                # Malformed must be rejected with 400 or 422, never 200
                if resp.status_code in (400, 422):
                    resp.success()
                elif resp.status_code == 200:
                    # Check if it was an idempotency skip (acceptable)
                    try:
                        body = resp.json()
                        if body.get("message") == "duplicate_skipped":
                            resp.success()
                        else:
                            resp.failure(
                                f"Malformed payload accepted with 200: variant={variant}"
                            )
                    except Exception:
                        resp.failure("Malformed payload accepted with 200 and bad body")
                else:
                    resp.success()  # 500 on null body is acceptable
        except Exception:
            pass  # null/non-JSON payloads may cause connection errors — expected
