import json
from datetime import datetime
from config.database import get_connection

class VoiceSessionStore:
    """
    Handles DB operations for Hinglish Voice Agent sessions.
    Adheres to SRP: keeps DB logic out of the voice agent.
    """
    
    def load(self, session_id: str) -> dict | None:
        """Loads a session by session_id (which is usually payment_id)."""
        conn = get_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voice_sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            if row.get("transcript"):
                row["transcript"] = json.loads(row["transcript"])
            return row
        return None

    def save(self, session_id: str, session_data: dict) -> bool:
        """Creates or updates a session."""
        conn = get_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        transcript_json = "[]"
        if "transcript" in session_data:
            transcript_json = json.dumps(session_data["transcript"])
            
        cursor.execute("""
            INSERT INTO voice_sessions (
                session_id, payment_id, turn_count, last_intent, last_promised_date,
                promise_kept, churn_signal, status, chat_state, detected_language, last_updated, transcript
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                turn_count = excluded.turn_count,
                last_intent = excluded.last_intent,
                last_promised_date = excluded.last_promised_date,
                promise_kept = excluded.promise_kept,
                churn_signal = excluded.churn_signal,
                status = excluded.status,
                chat_state = excluded.chat_state,
                detected_language = excluded.detected_language,
                last_updated = excluded.last_updated,
                transcript = excluded.transcript
        """, (
            session_id,
            session_data.get("payment_id", session_id),
            session_data.get("turn_count", 0),
            session_data.get("last_intent", ""),
            session_data.get("last_promised_date", ""),
            session_data.get("promise_kept", 0),
            session_data.get("churn_signal", 0),
            session_data.get("status", "active"),
            session_data.get("chat_state", "AI_ACTIVE"),
            session_data.get("detected_language", "hinglish"),
            now,
            transcript_json
        ))
        
        conn.commit()
        conn.close()
        return True

    def get_all_transcripts(self) -> list:
        """Retrieves all sessions (for dashboard UI)."""
        conn = get_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voice_sessions ORDER BY last_updated DESC")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            if row.get("transcript"):
                row["transcript"] = json.loads(row["transcript"])
        return rows

    def clear(self, session_id: str) -> bool:
        """Removes a session from active tracking."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM voice_sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        return True

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
