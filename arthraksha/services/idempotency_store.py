"""
ArthRaksha — Idempotency Store
=================================
Implements IIdempotencyStore.
Prevents duplicate actions across retries/failures.
"""
import logging
import sqlite3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IIdempotencyStore
from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

class SQLiteIdempotencyStore(IIdempotencyStore):
    """
    SQLite-backed idempotency store.
    Key format: RC_{event_id}:{action_type}:{attempt_number}
    """
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(BASE_DIR.parent / "idempotency.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS idempotency (
                    idem_key TEXT PRIMARY KEY,
                    result JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def is_duplicate(self, key: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM idempotency WHERE idem_key = ?", (key,))
            return cursor.fetchone() is not None

    def mark_executed(self, key: str, result: dict) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO idempotency (idem_key, result) VALUES (?, ?)",
                    (key, json.dumps(result))
                )
        except sqlite3.IntegrityError:
            logger.warning(f"Idempotency key already exists: {key}")

    def get_result(self, key: str) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT result FROM idempotency WHERE idem_key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

# Global instance
idempotency_store = SQLiteIdempotencyStore()
