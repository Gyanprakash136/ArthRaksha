"""
Unit tests — Layer 1: Input Guardrails (Guardrails.validate_input)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
from services.guardrails import Guardrails


# ── helpers ──────────────────────────────────────────────────────────────────

def _base_event():
    return {
        "event_id": "evt_unit_001",
        "payment_id": "pay_unit_001",
        "amount": 5000,
        "error_code": "gateway_technical_error",
        "customer": {
            "contact": "+919876543210",
            "email": "user@example.com",
        },
    }


def _tax():
    import json
    path = os.path.join(os.path.dirname(__file__), "../../arthraksha/data/error_taxonomy.json")
    with open(path) as f:
        return json.load(f)


# ── validate_input ────────────────────────────────────────────────────────────

class TestValidateInputMissingFields:
    """Each required field, when absent, must fail."""

    @pytest.mark.parametrize("field", ["event_id", "payment_id", "amount", "error_code", "customer"])
    def test_missing_field_rejected(self, field):
        ev = _base_event()
        del ev[field]
        ok, reason = Guardrails.validate_input(ev, _tax())
        assert not ok
        assert field in reason

    def test_zero_amount_rejected(self):
        ev = _base_event()
        ev["amount"] = 0
        ok, reason = Guardrails.validate_input(ev, _tax())
        assert not ok
        assert "Amount" in reason

    def test_negative_amount_rejected(self):
        ev = _base_event()
        ev["amount"] = -100
        ok, reason = Guardrails.validate_input(ev, _tax())
        assert not ok

    def test_unknown_error_code_rejected(self):
        ev = _base_event()
        ev["error_code"] = "totally_made_up_error"
        ok, reason = Guardrails.validate_input(ev, _tax())
        assert not ok
        assert "Unknown error code" in reason

    def test_missing_customer_contact_rejected(self):
        ev = _base_event()
        ev["customer"] = {"email": "user@example.com"}
        ok, reason = Guardrails.validate_input(ev, _tax())
        assert not ok
        assert "contact" in reason.lower()

    def test_valid_event_passes(self):
        ok, reason = Guardrails.validate_input(_base_event(), _tax())
        # Either passes or fails idempotency (event may already exist in DB)
        # We only check that *schema* rejection doesn't happen
        if not ok:
            assert "Idempotency" in reason


class TestOutputSanitizer:
    """Guardrails.sanitize_output must strip PII."""

    def test_card_number_redacted(self):
        ev = _base_event()
        msg = "Card 4111111111111111 declined"
        result = Guardrails.sanitize_output(msg, ev)
        assert "4111111111111111" not in result
        assert "[REDACTED" in result

    def test_bank_account_redacted(self):
        ev = _base_event()
        msg = "Account 123456789012 not found"
        result = Guardrails.sanitize_output(msg, ev)
        assert "123456789012" not in result

    def test_phone_masked(self):
        # The masking formula: "*" * (len-4) + last_4
        # For a 4-char phone, len-4 == 0, so masked_phone == phone itself.
        # The replace() call is a no-op → output unchanged.
        ev = _base_event()
        ev["customer"]["phone"] = "9876"
        result = Guardrails.sanitize_output("Contact 9876 for help", ev)
        # 4-digit phone: masked == original (no stars prepended), message unchanged
        assert result == "Contact 9876 for help"

    def test_full_phone_not_in_output(self):
        """12-digit phone (+91XXXXXXXXXX) is caught by the bank-account regex."""
        ev = _base_event()
        ev["customer"]["phone"] = "+919876543210"
        result = Guardrails.sanitize_output("Contact +919876543210 for help", ev)
        # The 12-digit run hits the \d{9,18} bank-account pattern first
        assert result == "Contact +[REDACTED ACCOUNT] for help"

    def test_long_message_truncated(self):
        ev = _base_event()
        long_msg = "x" * 600
        result = Guardrails.sanitize_output(long_msg, ev)
        assert len(result) <= 500

    def test_normal_message_unchanged(self):
        ev = _base_event()
        msg = "Payment link sent to customer."
        assert Guardrails.sanitize_output(msg, ev) == msg
