import asyncio
import uuid
from adapters.jira import JiraAdapter

async def test_jira_adapter():
    adapter = JiraAdapter()
    print(f"Provider: {adapter.get_provider_name()}")
    
    # Test fetch_items (mocked)
    items = await adapter.fetch_items(token="mock-token")
    print(f"Fetched {len(items)} items.")
    
    for item in items:
        print(f"\nID: {item.id}")
        print(f"Source: {item.source}")
        print(f"External ID: {item.external_id}")
        print(f"Thread ID (Issue Key): {item.thread_id}")
        print(f"Sender: {item.sender['name']} ({item.sender['handle']})")
        print(f"Subject: {item.subject}")
        print(f"Content snippet: {item.content[:50]}...")
        print(f"Priority (metadata): {item.metadata.get('priority')}")
        print(f"Timestamp: {item.timestamp}")

if __name__ == "__main__":
    asyncio.run(test_jira_adapter())
