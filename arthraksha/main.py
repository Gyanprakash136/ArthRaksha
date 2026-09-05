import asyncio
import json
import uvicorn
import time
from pathlib import Path
from config.database import init_db
from models.llm import HuggingFaceLLM
from agents.graph import app
from agents.base import AgentState
from agents.insight_agent import InsightAgent
import os

async def run_batch_and_scorecard():
    # 1. Init DB
    init_db()
    
    # 2. Load events
    batch_path = Path(__file__).parent / "data" / "payment_failures_batch.json"
    with open(batch_path, "r") as f:
        events = json.load(f)
        
    # 3. Check LLM Health
    llm = HuggingFaceLLM()
    is_healthy = await llm.health_check()
    if not is_healthy:
        print("[WARNING] LLM API is unreachable! Continuing with taxonomy fallbacks.")
        
    # 4. Process all 100 events concurrently
    print(f"Processing {len(events)} events...")
    
    start_time = time.time()
    
    tasks = []
    for event in events:
        tasks.append(asyncio.create_task(app.route_event(event)))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    elapsed = time.time() - start_time
    
    # 5. Run Insight Agent and Collect Scorecard Metrics
    insight_agent = InsightAgent()
    
    total_at_risk = sum(e["amount"] for e in events)
    recovered = [r for r in results if not isinstance(r, Exception) and r.outcome == "recovered"]
    escalated = [r for r in results if not isinstance(r, Exception) and r.outcome == "escalated"]
    written_off = [r for r in results if not isinstance(r, Exception) and r.outcome == "written_off"]
    
    # Metrics
    rec_amt = sum(r.event["amount"] for r in recovered)
    esc_amt = sum(r.event["amount"] for r in escalated)
    woff_amt = sum(r.event["amount"] for r in written_off)
    
    t1_cases = [r for r in results if not isinstance(r, Exception) and r.current_tier == "T1"]
    t2_cases = [r for r in results if not isinstance(r, Exception) and r.current_tier == "T2"]
    t3_cases = [r for r in results if not isinstance(r, Exception) and r.current_tier == "T3"]
    
    hits = sum(1 for r in t2_cases if r.cache_hit)
    hit_rate = (hits / len(t2_cases) * 100) if t2_cases else 0.0
    misses = len(t2_cases) - hits
    tokens_saved = misses * 450
    cost_saved = tokens_saved * 0.0001
    
    # Just run the insight_agent's standard process_batch_outcomes to generate report
    insight_agent.process_batch_outcomes()
    
    top_insight = "No insights found."
    report_file = Path(__file__).parent / "docs" / "insights_report.md"
    if report_file.exists():
        with open(report_file, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("- "):
                    top_insight = line.strip()
                    break
    
    # 6. Print Scorecard
    print("\n══════════════════════════════════════════")
    print("ArthRaksha — Batch Complete")
    print("══════════════════════════════════════════")
    print(f"Total processed:     {len(events)} events")
    print(f"Total at risk:       ₹{total_at_risk:,}")
    print("\nOUTCOMES:")
    print(f"  Recovered:         {len(recovered):02d} cases   ₹{rec_amt:,} ({(len(recovered)/len(events)*100):.0f}%)")
    print(f"  Escalated:         {len(escalated):02d} cases   ₹{esc_amt:,} ({(len(escalated)/len(events)*100):.0f}%)")
    print(f"  Written off:       {len(written_off):02d} cases   ₹{woff_amt:,} ({(len(written_off)/len(events)*100):.0f}%)")
    print("\nAGENT PERFORMANCE:")
    print(f"  T1 auto-retry:     {len(t1_cases):02d} cases   avg {elapsed/len(events):.2f}s/case")
    print(f"  T2 LLM reasoning:  {len(t2_cases):02d} cases   avg {elapsed/len(events):.2f}s/case")
    print(f"  T3 escalated:      {len(t3_cases):02d} cases   avg {elapsed/len(events):.2f}s/case")
    print("\nLEARNING METRICS:")
    print(f"  Cache hit rate:    {hit_rate:.1f}%")
    print(f"  Tokens saved:      {tokens_saved:,}")
    print(f"  Est. cost saved:   ₹{cost_saved:.2f}")
    print("\nTOP INSIGHT:")
    print(f"  {top_insight}")
    print("══════════════════════════════════════════")
    print("Dashboard: http://localhost:8000/dashboard")
    print("══════════════════════════════════════════\n")

if __name__ == "__main__":
    # Ensure current dir is added to path to avoid import errors when running directly
    import sys
    sys.path.append(os.path.dirname(__file__))
    
    # Run the batch concurrently
    asyncio.run(run_batch_and_scorecard())
    
    # 7. Keep FastAPI running for the dashboard
    print("Starting FastAPI server...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
