import sqlite3
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Get DB path from env, fallback to default (with Vercel serverless /tmp support)
if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/arthraksha.db")
    seed_db = Path(__file__).parent.parent / "data" / "arthraksha.db"
    if seed_db.exists() and not DB_PATH.exists():
        try:
            import shutil
            shutil.copy2(seed_db, DB_PATH)
        except Exception:
            pass
else:
    db_path_str = os.getenv("DATABASE_PATH", "data/arthraksha.db")
    if os.path.isabs(db_path_str):
        DB_PATH = Path(db_path_str)
    else:
        DB_PATH = Path(__file__).parent.parent / db_path_str


def get_connection():
    """Returns a connection to the SQLite database."""
    # Ensure parent dir exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the necessary tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id   TEXT PRIMARY KEY,
            payment_id    TEXT,
            name          TEXT,
            email         TEXT,
            phone         TEXT,
            bank_issuer   TEXT,
            months_subscribed INTEGER,
            ltv_estimate  INTEGER,
            created_at    TEXT
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_payment_id ON customers(payment_id)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS idempotency_store (
            event_id TEXT PRIMARY KEY,
            processed_at TEXT,
            outcome TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery_ledger (
            payment_id TEXT PRIMARY KEY,
            amount INTEGER,
            error_code TEXT,
            agent_tier TEXT,
            complexity_score REAL,
            outcome TEXT,
            amount_recovered INTEGER,
            attempts INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id TEXT PRIMARY KEY,
            payment_id TEXT,
            timestamp TEXT,
            action_taken TEXT,
            action_reason TEXT,
            llm_reasoning TEXT,
            outcome TEXT,
            attempt_number INTEGER,
            stopping_rule_triggered INTEGER,
            confidence_score REAL,
            cache_hit INTEGER,
            tokens_used INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promise_tracker (
            promise_id TEXT PRIMARY KEY,
            payment_id TEXT,
            customer_id TEXT,
            promised_amount INTEGER,
            promised_date TEXT,
            status TEXT,
            created_at TEXT,
            reminder_sent INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_sessions (
            session_id TEXT PRIMARY KEY,
            payment_id TEXT,
            turn_count INTEGER DEFAULT 0,
            last_intent TEXT,
            last_promised_date TEXT,
            promise_kept INTEGER DEFAULT 0,
            churn_signal INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            chat_state TEXT DEFAULT 'AI_ACTIVE',
            detected_language TEXT DEFAULT 'hinglish',
            last_updated TEXT,
            transcript TEXT
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_voice_payment ON voice_sessions(payment_id)")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized successfully.")
