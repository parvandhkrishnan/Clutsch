import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from .base import BaseAdapter, NormalizedCommunication

class GmailAdapter(BaseAdapter):
    def get_provider_name(self) -> str:
        return "gmail"

    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        # Mocking Gmail API response
        mock_gmail_messages = [
            {
                "id": "gm-123",
                "threadId": "th-456",
                "snippet": "Urgent: Project Deadline approaching",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "John Doe <john@example.com>"},
                        {"name": "Subject", "value": "Project Deadline approaching"},
                        {"name": "Date", "value": "Sun, 24 May 2026 10:00:00 +0000"}
                    ],
                    "body": {"data": "Hi, just a reminder that the project is due by end of day today."}
                }
            },
            {
                "id": "gm-789",
                "threadId": "th-012",
                "snippet": "Lunch tomorrow?",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "Jane Smith <jane@example.com>"},
                        {"name": "Subject", "value": "Lunch tomorrow?"},
                        {"name": "Date", "value": "Sun, 24 May 2026 11:30:00 +0000"}
                    ],
                    "body": {"data": "Are you free for lunch tomorrow at 12?"}
                }
            },
            {
                "id": "gm-101",
                "threadId": "th-101",
                "snippet": "Security Alert: New login",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "Security Team <security@acme.com>"},
                        {"name": "Subject", "value": "Security Alert: New login"},
                        {"name": "Date", "value": "Sun, 24 May 2026 12:45:00 +0000"}
                    ],
                    "body": {"data": "We detected a new login to your account from a new device."}
                }
            }
        ]

        normalized_items = []
        for msg in mock_gmail_messages:
            normalized_items.append(self.normalize(msg))
            
        return normalized_items

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedCommunication:
        headers = {h["name"]: h["value"] for h in raw_data["payload"]["headers"]}
        
        # Simple sender parsing
        sender_raw = headers.get("From", "Unknown")
        name = sender_raw.split("<")[0].strip() if "<" in sender_raw else sender_raw
        handle = sender_raw.split("<")[1].replace(">", "").strip() if "<" in sender_raw else sender_raw

        return NormalizedCommunication(
            id=str(uuid.uuid4()),
            source="gmail",
            external_id=raw_data["id"],
            thread_id=raw_data["threadId"],
            sender={"name": name, "handle": handle},
            recipient="me@priorityflow.com",
            subject=headers.get("Subject"),
            content=raw_data["payload"]["body"]["data"],
            timestamp=datetime.now().isoformat(), # Using now for mock
            metadata=raw_data
        )
