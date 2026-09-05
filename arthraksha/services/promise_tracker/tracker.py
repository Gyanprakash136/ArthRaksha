from config.database import get_connection
import uuid
from datetime import datetime, timedelta

class PromiseTracker:
    def __init__(self):
        pass

    def create_promise(self, payment_id: str, customer_id: str, amount: int, promised_date: str) -> str:
        """Insert a new promise into the tracker."""
        promise_id = str(uuid.uuid4())
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # In a real system promised_date would be a valid datetime string,
        # for demo we might receive "tomorrow". We map it roughly.
        target_date = datetime.now()
        if promised_date == "tomorrow":
            target_date += timedelta(days=1)
        elif promised_date == "friday":
            target_date += timedelta(days=3)
        elif promised_date == "monday":
            target_date += timedelta(days=5)
            
        cursor.execute("""
            INSERT INTO promise_tracker (id, payment_id, customer_name, promised_amount, promised_date, status, reminder_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            promise_id, 
            payment_id, 
            customer_id, 
            amount, 
            target_date.strftime("%Y-%m-%d %H:%M:%S"), 
            "pending", 
            0
        ))
        
        conn.commit()
        conn.close()
        return promise_id

    def check_due_promises(self) -> list:
        """Find promises that are overdue and haven't been reminded."""
        conn = get_connection()
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = conn.cursor()
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            SELECT * FROM promise_tracker 
            WHERE promised_date <= ? AND status = 'pending' AND reminder_sent = 0
        """, (now_str,))
        
        due_promises = cursor.fetchall()
        conn.close()
        return due_promises

    def send_reminder(self, promise_id: str) -> bool:
        """Sends a reminder via email_tool and updates DB."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Mark reminder sent
        cursor.execute("UPDATE promise_tracker SET reminder_sent = 1 WHERE id = ?", (promise_id,))
        
        # Log to audit
        cursor.execute("SELECT payment_id FROM promise_tracker WHERE id = ?", (promise_id,))
        row = cursor.fetchone()
        if row:
            payment_id = row[0]
            cursor.execute("""
                INSERT INTO audit_log (payment_id, action, agent_tier, confidence, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (payment_id, "promise_reminder_sent", "T2", 1.0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), '{"tool": "email_tool"}'))
            
        conn.commit()
        conn.close()
        return True

    def escalate_broken_promise(self, promise_id: str):
        """
        Deterministic decision fork for expired promises (T+24 hours):
        - If Amount >= ₹2,500 OR Customer LTV >= ₹10,000: Fork to Tier 3 Human Ops Escalation
        - If Amount < ₹2,500: Fork to Permanent Write-Off (ops review cost exceeds recovery value)
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pt.payment_id, pt.promised_amount, rl.complexity_score, c.ltv_estimate 
            FROM promise_tracker pt 
            LEFT JOIN recovery_ledger rl ON pt.payment_id = rl.payment_id 
            LEFT JOIN customers c ON pt.payment_id = c.payment_id 
            WHERE pt.promise_id = ? OR pt.id = ?
        """, (promise_id, promise_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return

        payment_id = row[0]
        amount = row[1] or 0
        risk_score = row[2] or 0.5
        ltv = row[3] or 0
        
        # Deterministic Fork
        if amount >= 2500 or ltv >= 10000:
            outcome = "escalated"
            action = "broken_promise_t3_escalation"
            tier = "T3"
            reason = f"Broken promise (T+24h) on high-value transaction (₹{amount:,}, LTV: ₹{ltv:,}) → Fork to T3 Human Review."
        else:
            outcome = "written_off"
            action = "broken_promise_written_off"
            tier = "T2"
            reason = f"Broken promise (T+24h) below ops threshold (₹{amount:,} < ₹2,500) → Fork to Auto-Write-Off (protects merchant ROI)."

        cursor.execute("UPDATE promise_tracker SET status = ? WHERE promise_id = ? OR id = ?", (outcome, promise_id, promise_id))
        cursor.execute("UPDATE recovery_ledger SET outcome = ?, updated_at = datetime('now') WHERE payment_id = ?", (outcome, payment_id))
        
        log_id = str(uuid.uuid4())
        try:
            cursor.execute("""
                INSERT INTO audit_log (log_id, payment_id, action_taken, action_reason, llm_reasoning, outcome, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (log_id, payment_id, action, reason, f'{{"reason": "{reason}"}}', outcome))
        except Exception:
            pass
            
        conn.commit()
        conn.close()
