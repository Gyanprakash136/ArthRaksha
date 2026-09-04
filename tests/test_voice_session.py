import sys
import os
from pathlib import Path

# Add the project root to sys.path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent / "arthraksha"))

from services.hinglish_voice.voice_agent import HinglishVoiceAgent
from services.hinglish_voice.session_store import VoiceSessionStore
from config.database import init_db

def test_followup_memory():
    # Ensure tables exist
    init_db()
    
    agent = HinglishVoiceAgent()
    store = VoiceSessionStore()
    
    # Clean state
    store.clear("pay_test_001")

    # Turn 1
    response1 = agent.run_conversation(
        event={"payment_id": "pay_test_001"},
        customer_message="kal deta hun"
    )
    
    session = store.load("pay_test_001")
    assert session is not None
    assert session["last_intent"] == "delay"
    assert session["turn_count"] == 1
    print("✅ Turn 1 passed")

    # Turn 2
    response2 = agent.run_conversation(
        event={"payment_id": "pay_test_001"},
        customer_message="kal nahi, parso dunga"
    )
    
    session = store.load("pay_test_001")
    assert session is not None
    assert session["turn_count"] == 2
    assert "pichli baar" in response2["agent_response"].lower()
    print("✅ Turn 2 passed (Memory verified)")
    
    # Clean up
    store.clear("pay_test_001")

if __name__ == "__main__":
    test_followup_memory()
    print("✅ All tests passed!")
