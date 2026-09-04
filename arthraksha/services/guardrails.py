import re
from config.database import get_connection

class Guardrails:
    
    @staticmethod
    def validate_input(event: dict, taxonomy: dict) -> tuple[bool, str]:
        """LAYER 1 - Input Guardrails"""
        required_fields = ["event_id", "payment_id", "amount", "error_code", "customer"]
        for field in required_fields:
            if field not in event:
                return False, f"Missing required field: {field}"
                
        if event.get("amount", 0) <= 0:
            return False, "Amount must be greater than 0"
            
        error_code = event.get("error_code")
        if error_code not in taxonomy.get("error_codes", {}):
            return False, f"Unknown error code: {error_code}"
            
        customer = event.get("customer", {})
        if not customer.get("contact"):
            return False, "Customer contact is missing"
            
        # Check idempotency table in SQLite
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT event_id FROM idempotency_store WHERE event_id = ?", (event["event_id"],))
        if cursor.fetchone():
            conn.close()
            return False, "Event already processed (Idempotency check failed)"
        conn.close()
            
        return True, ""

    @staticmethod
    def validate_action(state, proposed_action: str, taxonomy: dict) -> tuple[bool, str]:
        """LAYER 2 - Agent Guardrails"""
        if state.stopping_rule_triggered:
            return False, "Stopping rule previously triggered"
            
        error_code = state.event.get("error_code")
        error_meta = taxonomy.get("error_codes", {}).get(error_code, {})
        max_attempts = error_meta.get("max_attempts", 3)  # default fallback
        
        if state.attempt_number >= max_attempts:
            return False, f"Attempt {state.attempt_number} exceeds max allowed ({max_attempts})"
            
        # Optional: check if action is in allowed list (taxonomy recovery_paths)
        # Assuming taxonomy might have specific allowed actions, if not, skip strict enforcement
        allowed_actions = error_meta.get("recovery_paths", ["auto_retry", "payment_link", "email_reminder"])
        if proposed_action not in allowed_actions and proposed_action != "human_review":
            return False, f"Action '{proposed_action}' not allowed for {error_code}"
            
        if error_code == "payment_risk_check_failed":
            return False, "Cannot contact customer flagged as fraud"
            
        if state.confidence_score < 0.20:
            return False, f"Confidence score ({state.confidence_score}) below 0.20 threshold"
            
        return True, ""

    @staticmethod
    def sanitize_output(message: str, event: dict) -> str:
        """LAYER 3 - Output Guardrails"""
        sanitized = message
        
        # Strip potential card numbers (13-19 continuous or space-separated digits)
        sanitized = re.sub(r'\b(?:\d[ -]*?){13,19}\b', '[REDACTED CARD]', sanitized)
        
        # Strip potential bank account numbers (assuming 9-18 digits)
        sanitized = re.sub(r'\b\d{9,18}\b', '[REDACTED ACCOUNT]', sanitized)
        
        # Mask customer phone (leave only last 4)
        phone = event.get("customer", {}).get("phone", "")
        if phone and len(phone) >= 4:
            masked_phone = "*" * (len(phone) - 4) + phone[-4:]
            sanitized = sanitized.replace(phone, masked_phone)
            
        # Enforce length limit
        if len(sanitized) > 500:
            sanitized = sanitized[:497] + "..."
            
        return sanitized
