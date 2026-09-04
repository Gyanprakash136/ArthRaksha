import sys
import os
import asyncio
import json
from pathlib import Path

# Add arthraksha to path to fix module imports
sys.path.append(os.path.join(os.path.dirname(__file__), "arthraksha"))

from agents.graph import RecoveryGraph
from config.database import init_db

async def main():
    print("1. Initializing Database Tables...")
    init_db()
    
    print("\n2. Initializing Agent Architecture...")
    queue = asyncio.Queue()
    graph = RecoveryGraph(queue)
    
    # Load batch
    batch_path = Path(__file__).parent / "arthraksha" / "data" / "payment_failures_batch.json"
    if not batch_path.exists():
        print(f"Error: Could not find {batch_path}")
        return
        
    with open(batch_path, "r") as f:
        events = json.load(f)
        
    print(f"\n3. Loaded {len(events)} events. Testing first event through the architecture...")
    event = events[0]
    
    print(f"\n--- Processing Event: {event['event_id']} ---")
    print(f"Error Code: {event['error_code']}")
    print(f"Amount: {event['amount']}")
    
    state = graph.route_event(event)
    
    print("\n--- Execution Result ---")
    print(f"Outcome: {state.outcome}")
    print(f"Last Action: {state.last_action}")
    print(f"Tier Handled: {state.current_tier}")
    print(f"Audit Log Lines Written: {len(state.audit_log)}")
    print(f"LLM Reasoning: {state.llm_reasoning}")
    
    print("\n✅ Architecture verification successful. All components imported and executed cleanly!")

if __name__ == "__main__":
    asyncio.run(main())
