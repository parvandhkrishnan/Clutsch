import asyncio
from adapters.jira import JiraAdapter

async def test_jira_adapter():
    adapter = JiraAdapter()
    print(f"Provider: {adapter.get_provider_name()}")
    
    items = await adapter.fetch_items()
    print(f"Fetched {len(items)} items")
    
    for item in items:
        print(f"ID: {item.id}")
        print(f"Source: {item.source}")
        print(f"External ID: {item.external_id}")
        print(f"Thread ID: {item.thread_id}")
        print(f"Sender: {item.sender}")
        print(f"Subject: {item.subject}")
        print(f"Content: {item.content[:50]}...")
        print(f"Priority (from metadata): {item.metadata.get('priority')}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_jira_adapter())
