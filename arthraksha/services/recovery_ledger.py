"""
ArthRaksha — Recovery Ledger
===============================
Implements IRecoveryLedger.
Maintains the business state of recovery cases (separate from audit history).
"""
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IRecoveryLedger, RecoveryCase, RecoveryCaseStatus
from config.settings import settings, BASE_DIR

logger = logging.getLogger(__name__)

class SQLiteRecoveryLedger(IRecoveryLedger):
    """
    SQLite-backed Recovery Ledger.
    """
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(BASE_DIR.parent / "ledger.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recovery_cases (
                    case_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    subscription_id TEXT NOT NULL,
                    merchant_id TEXT NOT NULL,
                    amount_at_risk REAL NOT NULL,
                    status TEXT NOT NULL,
                    amount_recovered REAL DEFAULT 0.0,
                    recovery_time_h REAL DEFAULT 0.0,
                    strategy_used TEXT,
                    tier_used TEXT,
                    attempts INTEGER DEFAULT 0,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
            """)

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def open_case(self, event: dict) -> RecoveryCase:
        case_id = f"RC_{event['event_id']}"
        now_ts = self._now()
        
        case = RecoveryCase(
            case_id=case_id,
            event_id=event['event_id'],
            subscription_id=event.get('subscription_id', ''),
            merchant_id=event.get('merchant_id', ''),
            amount_at_risk=float(event.get('amount_rupees', 0.0)),
            status=RecoveryCaseStatus.IN_PROGRESS,
            opened_at=now_ts
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO recovery_cases 
                (case_id, event_id, subscription_id, merchant_id, amount_at_risk, status, opened_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                case.case_id, case.event_id, case.subscription_id, case.merchant_id, 
                case.amount_at_risk, case.status.value, case.opened_at
            ))
            
        return case

    def update_case(self, case_id: str, updates: dict) -> RecoveryCase:
        allowed_keys = {
            "status", "amount_recovered", "recovery_time_h", 
            "strategy_used", "tier_used", "attempts"
        }
        set_clauses = []
        values = []
        
        for k, v in updates.items():
            if k in allowed_keys:
                if isinstance(v, RecoveryCaseStatus):
                    v = v.value
                set_clauses.append(f"{k} = ?")
                values.append(v)
                
        if not set_clauses:
            return self.get_case(case_id)
            
        values.append(case_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE recovery_cases SET {', '.join(set_clauses)} WHERE case_id = ?", values)
            
        return self.get_case(case_id)

    def close_case(self, case_id: str, outcome: RecoveryCaseStatus) -> None:
        now_ts = self._now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE recovery_cases SET status = ?, closed_at = ? WHERE case_id = ?", 
                (outcome.value, now_ts, case_id)
            )

    def get_case(self, case_id: str) -> RecoveryCase | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM recovery_cases WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            
            if row:
                return RecoveryCase(
                    case_id=row['case_id'],
                    event_id=row['event_id'],
                    subscription_id=row['subscription_id'],
                    merchant_id=row['merchant_id'],
                    amount_at_risk=row['amount_at_risk'],
                    status=RecoveryCaseStatus(row['status']),
                    amount_recovered=row['amount_recovered'],
                    recovery_time_h=row['recovery_time_h'],
                    strategy_used=row['strategy_used'],
                    tier_used=row['tier_used'],
                    attempts=row['attempts'],
                    opened_at=row['opened_at'],
                    closed_at=row['closed_at']
                )
            return None

    def get_summary(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    status, 
                    COUNT(*) as count, 
                    SUM(amount_at_risk) as total_at_risk,
                    SUM(amount_recovered) as total_recovered
                FROM recovery_cases 
                GROUP BY status
            """)
            stats = {row[0]: {"count": row[1], "at_risk": row[2] or 0.0, "recovered": row[3] or 0.0} for row in cursor.fetchall()}
            
            total_cases = sum(s["count"] for s in stats.values())
            total_recovered = sum(s["recovered"] for s in stats.values())
            
            return {
                "total_cases": total_cases,
                "total_recovered_rupees": total_recovered,
                "by_status": stats
            }

# Global instance
recovery_ledger = SQLiteRecoveryLedger()
