import asyncio
import json
from pathlib import Path
from config.database import get_connection
from services.cache_manager import CacheManager
from agents.graph import RecoveryGraph

class InsightAgent:
    def __init__(self):
        self.cache_manager = CacheManager()
        
    async def run_batch(self, events: list):
        """Processes a batch of events concurrently through the Agentic Graph."""
        print(f"Processing {len(events)} events concurrently...")
        
        # Instantiate local graph (to avoid global loop issues)
        queue = asyncio.Queue()
        graph = RecoveryGraph(queue)
        
        # Concurrent execution using asyncio.gather
        tasks = [graph.route_event(event) for event in events]
        results = await asyncio.gather(*tasks)
        
        # Compute learning metrics
        total_t2_events = 0
        hits = 0
        misses = 0
        
        for state in results:
            if state.current_tier == "T2":
                total_t2_events += 1
                if state.cache_hit:
                    hits += 1
                else:
                    misses += 1
                    
        # Calculate final metrics as requested
        cache_hit_rate = (hits / total_t2_events) if total_t2_events > 0 else 0.0
        # The user specifically requested: tokens_saved = misses * 450
        tokens_saved = misses * 450
        estimated_cost_saved = tokens_saved * 0.0001
        
        print("\n--- DEMO LEARNING METRICS ---")
        print(f"Total T2 Events: {total_t2_events}")
        print(f"Cache Hit Rate: {cache_hit_rate:.2%}")
        print(f"Tokens Saved: {tokens_saved}")
        print(f"Estimated Cost Saved: ${estimated_cost_saved:.4f}")
        print("-----------------------------\n")
        
        return results

    def process_batch_outcomes(self):
        """
        Runs on a cron schedule (or manually via CLI).
        1. Reads closed events from SQLite recovery_ledger
        2. Recalculates cache_manager success rates
        3. Identifies new taxonomy rules to suggest
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT payment_id, error_code, outcome, attempts FROM recovery_ledger WHERE outcome != 'pending'")
        records = cursor.fetchall()
        
        insights = []
        
        for record in records:
            recovered = (record["outcome"] == "recovered")
            
            mock_event = {
                "error_code": record["error_code"],
                "attempts": record["attempts"] - 1, 
                "customer": {"ltv_estimate": 10000}
            }
            
            key = self.cache_manager.build_key(mock_event)
            self.cache_manager.update_success_rate(key, recovered)
            
            if not recovered and record["error_code"] == "insufficient_funds":
                insights.append(f"High failure rate on {record['error_code']}. Consider shifting to T1 with longer delay.")

        conn.close()
        
        report_dir = Path(__file__).parent.parent / "docs"
        report_dir.mkdir(exist_ok=True)
        with open(report_dir / "insights_report.md", "w") as f:
            f.write("# ArthRaksha AI Insights Report\n\n")
            f.write(f"Processed {len(records)} outcomes.\n\n")
            f.write("## Recommendations\n")
            for ins in set(insights):
                f.write(f"- {ins}\n")
                
        return len(records)
