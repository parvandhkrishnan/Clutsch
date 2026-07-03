import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from .base import BaseAdapter, NormalizedCommunication

class OutlookAdapter(BaseAdapter):
    def get_provider_name(self) -> str:
        return "outlook"

    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        # Mocking Outlook API response
        mock_outlook_messages = [
            {
                "id": "outlook-1",
                "conversationId": "conv-123",
                "subject": "URGENT: Database Migration Error",
                "from": {"emailAddress": {"name": "Ops Team", "address": "ops@priorityflow.com"}},
                "body": {"contentType": "text", "content": "The database migration failed on production. We need immediate assistance to roll back or fix the schema mismatch."},
                "receivedDateTime": (datetime.now()).isoformat(),
                "isRead": False,
                "importance": "high",
                "categories": ["Engineering", "Urgent"]
            },
            {
                "id": "outlook-2",
                "conversationId": "conv-456",
                "subject": "Q3 Planning Session",
                "from": {"emailAddress": {"name": "Sarah Connor", "address": "sarah@priorityflow.com"}},
                "body": {"contentType": "text", "content": "Hi, I've scheduled our Q3 planning session for next Tuesday. Please review the agenda attached."},
                "receivedDateTime": (datetime.now()).isoformat(),
                "isRead": False,
                "importance": "normal",
                "categories": ["Planning"]
            },
            {
                "id": "outlook-3",
                "conversationId": "conv-789",
                "subject": "Lunch today?",
                "from": {"emailAddress": {"name": "John Doe", "address": "john@example.com"}},
                "body": {"contentType": "text", "content": "Are you down for lunch today? Thinking about that new Thai place."},
                "receivedDateTime": (datetime.now()).isoformat(),
                "isRead": True,
                "importance": "low",
                "categories": ["Social"]
            },
            {
                "id": "outlook-4",
                "conversationId": "conv-101",
                "subject": "Weekly Newsletter",
                "from": {"emailAddress": {"name": "PriorityFlow News", "address": "newsletter@priorityflow.com"}},
                "body": {"contentType": "text", "content": "Check out this week's top highlights from our company updates."},
                "receivedDateTime": (datetime.now()).isoformat(),
                "isRead": True,
                "importance": "low",
                "categories": ["Internal"]
            }
        ]

        normalized_items = []
        for msg in mock_outlook_messages:
            normalized_items.append(self.normalize(msg))
            
        return normalized_items

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedCommunication:
        return NormalizedCommunication(
            id=str(uuid.uuid4()),
            source="outlook",
            external_id=raw_data["id"],
            thread_id=raw_data["conversationId"],
            sender={
                "name": raw_data["from"]["emailAddress"]["name"], 
                "handle": raw_data["from"]["emailAddress"]["address"]
            },
            recipient="me@outlook.com",
            subject=raw_data["subject"],
            content=raw_data["body"]["content"],
            timestamp=raw_data["receivedDateTime"],
            metadata=raw_data
        )
