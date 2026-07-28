import asyncio
import datetime
import json
from prioritizer import PriorityEngine
from ai_analyzer import AIAnalyzer, MockAIProvider
from scoring_service import ScoringService

def test_scoring_logic():
    print("Testing scoring logic...")
    engine = PriorityEngine()
    # Use mock provider for deterministic tests
    analyzer = AIAnalyzer(provider=MockAIProvider())
    service = ScoringService(engine, analyzer)
    
    items = [
        {
            "id": "test-1",
            "text": "URGENT: server is down ASAP!",
            "source": "Slack",
            "metadata": {"is_urgent": True, "message_type": "dm"}
        },
        {
            "id": "test-2",
            "text": "Just a regular update.",
            "source": "Gmail",
            "metadata": {}
        },
        {
            "id": "test-3",
            "text": "Bug: Auth failing",
            "source": "Jira",
            "metadata": {"issue_type": "bug", "priority": "highest"}
        }
    ]
    
    processed = asyncio.run(service.process_items("t-acme", items, set(), {}))
    
    for item in processed:
        print(f"Source: {item['source']}, Score: {item['priorityScore']}, Tier: {item['priorityTier']}")
        print(f"Explanation: {item['explanation']}\n")
        
        # Basic assertions
        assert "priorityScore" in item
        assert "priorityTier" in item
        assert "explanation" in item
        assert 0 <= item["priorityScore"] <= 100

    # Ensure Slack urgent DM is ranked medium at least (it was 56.76)
    slack_item = next(i for i in processed if i["source"] == "Slack")
    assert slack_item["priorityTier"] in ["urgent", "high", "medium"]

    # Ensure Jira highest priority bug is ranked medium at least (it was 31.25)
    jira_item = next(i for i in processed if i["source"] == "Jira")
    assert jira_item["priorityTier"] in ["urgent", "high", "medium"]

    print("Testing contact priority overrides...")
    contact_priorities = {
        "gmail": {
            "boss@acme.com": "high",
            "spammer@ads.com": "low"
        }
    }
    items_with_contacts = [
        {
            "id": "c-1",
            "text": "Meeting at 2pm",
            "source": "Gmail",
            "sender": {"handle": "boss@acme.com"},
            "metadata": {}
        },
        {
            "id": "c-2",
            "text": "Buy more pills",
            "source": "Gmail",
            "sender": {"handle": "spammer@ads.com"},
            "metadata": {}
        }
    ]
    
    processed_contacts = asyncio.run(service.process_items("t-acme", items_with_contacts, set(), {}, contact_priorities))
    boss_item = next(i for i in processed_contacts if i["id"] == "c-1")
    spam_item = next(i for i in processed_contacts if i["id"] == "c-2")
    
    print(f"Boss item score: {boss_item['priorityScore']} ({boss_item['explanation']})")
    print(f"Spam item score: {spam_item['priorityScore']} ({spam_item['explanation']})")
    
    assert "High priority contact" in boss_item["explanation"]
    assert "Low priority contact" in spam_item["explanation"]
    assert boss_item["priorityScore"] > spam_item["priorityScore"]
    
    print("Contact priority tests passed!\n")

    print("Scoring logic tests passed!\n")

if __name__ == "__main__":
    try:
        test_scoring_logic()
    except Exception as e:
        print(f"Tests failed: {e}")
        exit(1)
