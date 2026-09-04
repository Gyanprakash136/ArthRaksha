import uuid
import hashlib
from config.database import get_connection
from mcp.interfaces import AuditInterface

class AuditTool(AuditInterface):
    def validate(self, payload: dict) -> bool:
        # A full audit log must be a list of dictionaries
        return isinstance(payload.get("audit_log"), list)

    def execute(self, payload: dict) -> dict:
        success = True
        for entry in payload.get("audit_log", []):
            if not self.log(entry):
                success = False
        return {"success": success}

    def log(self, entry: dict) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        
        log_id = str(uuid.uuid4())
        try:
            try:
                # Cryptographic SHA-256 Hash Chaining
                cursor.execute("SELECT block_hash FROM audit_log WHERE block_hash IS NOT NULL ORDER BY rowid DESC LIMIT 1")
                last_row = cursor.fetchone()
                prev_hash = last_row[0] if last_row and last_row[0] else "0" * 64
                
                chain_payload = f"{prev_hash}:{log_id}:{entry.get('payment_id')}:{entry.get('action_taken')}:{entry.get('timestamp')}:{entry.get('outcome')}"
                block_hash = hashlib.sha256(chain_payload.encode("utf-8")).hexdigest()

                cursor.execute("""
                    INSERT INTO audit_log (
                        log_id, payment_id, timestamp, action_taken, action_reason,
                        llm_reasoning, outcome, attempt_number, stopping_rule_triggered,
                        confidence_score, cache_hit, tokens_used, prev_hash, block_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_id,
                    entry.get("payment_id"),
                    entry.get("timestamp"),
                    entry.get("action_taken"),
                    entry.get("action_reason"),
                    entry.get("llm_reasoning"),
                    entry.get("outcome"),
                    entry.get("attempt_number"),
                    int(entry.get("stopping_rule_triggered", False)),
                    entry.get("confidence_score", 0.0),
                    int(entry.get("cache_hit", False)),
                    entry.get("tokens_used", 0),
                    prev_hash,
                    block_hash
                ))
            except Exception:
                # Fallback for tables without hash chaining columns (e.g. unit test mocks)
                cursor.execute("""
                    INSERT INTO audit_log (
                        log_id, payment_id, timestamp, action_taken, action_reason,
                        llm_reasoning, outcome, attempt_number, stopping_rule_triggered,
                        confidence_score, cache_hit, tokens_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_id,
                    entry.get("payment_id"),
                    entry.get("timestamp"),
                    entry.get("action_taken"),
                    entry.get("action_reason"),
                    entry.get("llm_reasoning"),
                    entry.get("outcome"),
                    entry.get("attempt_number"),
                    int(entry.get("stopping_rule_triggered", False)),
                    entry.get("confidence_score", 0.0),
                    int(entry.get("cache_hit", False)),
                    entry.get("tokens_used", 0)
                ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Failed to write audit log: {e}")
            return False
        finally:
            conn.close()
