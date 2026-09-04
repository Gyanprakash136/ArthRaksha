from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
from services.guardrails import Guardrails
from agents.graph import app
from config.database import get_connection
import json
from pathlib import Path

router = APIRouter(prefix="/webhook", tags=["Webhook"])

# Queue to handle incoming webhooks asynchronously without blocking Razorpay
webhook_queue = asyncio.Queue()

async def process_queue_worker():
    """Background worker that continuously processes the queue."""
    # Load taxonomy for guardrails
    taxonomy_path = Path(__file__).parent.parent.parent / "data" / "error_taxonomy.json"
    with open(taxonomy_path, "r") as f:
        taxonomy = json.load(f)
        
    while True:
        event = await webhook_queue.get()
        try:
            # 5. Process through agent graph
            state = await app.route_event(event)
            
            # Write result to recovery_ledger
            conn = get_connection()
            cursor = conn.cursor()
            
            # Record outcome
            cursor.execute("""
                INSERT OR REPLACE INTO recovery_ledger 
                (payment_id, amount, error_code, agent_tier, complexity_score, outcome, attempts, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                event["payment_id"],
                event["amount"],
                event["error_code"],
                state.current_tier,
                state.complexity_score,
                state.outcome,
                state.attempt_number
            ))
            
            # Mark event processed in idempotency_store
            cursor.execute("""
                INSERT OR REPLACE INTO idempotency_store (event_id, processed_at, outcome)
                VALUES (?, datetime('now'), ?)
            """, (event["event_id"], state.outcome))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error processing queued event {event.get('event_id')}: {e}")
        finally:
            webhook_queue.task_done()

@router.on_event("startup")
async def startup_event():
    # Start the background worker when FastAPI starts
    asyncio.create_task(process_queue_worker())

@router.post("/razorpay")
async def razorpay_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    taxonomy_path = Path(__file__).parent.parent.parent / "data" / "error_taxonomy.json"
    with open(taxonomy_path, "r") as f:
        taxonomy = json.load(f)
        
    # Layer 1 Guardrails (Schema + Idempotency)
    is_valid, reason = Guardrails.validate_input(payload, taxonomy)
    
    if not is_valid:
        if "Idempotency" in reason:
            # Duplicate -> Return 200 immediately
            return {"status": "success", "message": "duplicate_skipped"}
        else:
            # Invalid schema/data -> Return 400
            print(f"[Webhook Error] Invalid payload: {reason}")
            raise HTTPException(status_code=400, detail=reason)
            
    # Valid -> Push to queue
    await webhook_queue.put(payload)
    
    # Return 200 immediately
    return {"status": "success", "message": "queued_for_processing"}

@router.post("/test")
async def test_webhook(event: Dict[Any, Any]):
    """Accepts a single test event, runs full pipeline, records in DB, and returns audit trail."""
    try:
        state = await app.route_event(event)

        conn = get_connection()
        cursor = conn.cursor()

        # Save customer details if provided
        cust = event.get("customer", {})
        if cust and isinstance(cust, dict):
            cursor.execute("""
                INSERT OR REPLACE INTO customers (
                    payment_id, customer_id, name, email, phone,
                    bank_issuer, months_subscribed, ltv_estimate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.get("payment_id"),
                cust.get("customer_id") or f"cust_{str(event.get('payment_id', ''))[-6:]}",
                cust.get("name") or "Customer",
                cust.get("email") or "customer@example.com",
                cust.get("phone") or cust.get("contact") or "+919999999999",
                cust.get("bank_issuer") or "HDFC",
                cust.get("months_subscribed") or 6,
                cust.get("ltv_estimate") or event.get("amount", 0) * 6
            ))

        # Record into recovery_ledger
        cursor.execute("""
            INSERT OR REPLACE INTO recovery_ledger 
            (payment_id, amount, error_code, agent_tier, complexity_score, outcome, attempts, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            event["payment_id"],
            event["amount"],
            event["error_code"],
            state.current_tier,
            state.complexity_score,
            state.outcome,
            state.attempt_number
        ))
        conn.commit()
        conn.close()

        return {
            "payment_id": event.get("payment_id"),
            "final_outcome": state.outcome,
            "agent_tier": state.current_tier,
            "audit_trail": state.audit_log
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

