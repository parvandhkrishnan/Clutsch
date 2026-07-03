import uuid
from datetime import datetime
from typing import List, Optional
from .base import BaseAdapter, NormalizedCommunication

class WhatsAppAdapter(BaseAdapter):
    def get_provider_name(self) -> str:
        return "whatsapp"

    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        # Mocking WhatsApp message data
        mock_whatsapp_messages = [
            {
                "id": "wa-msg-1",
                "phone_number": "+1234567890",
                "sender_name": "Alice",
                "text": "Hey, are we still meeting at 5?",
                "timestamp": (datetime.now()).isoformat(),
                "chat_type": "personal",
                "is_business": False
            },
            {
                "id": "wa-msg-2",
                "phone_number": "+0987654321",
                "sender_name": "Project Alpha Group",
                "text": "Bob: I've uploaded the latest designs to the drive.",
                "timestamp": (datetime.now()).isoformat(),
                "chat_type": "group",
                "is_business": False,
                "group_name": "Project Alpha"
            },
            {
                "id": "wa-msg-3",
                "phone_number": "+1122334455",
                "sender_name": "Bank Notification",
                "text": "Your account statement for May is now available.",
                "timestamp": (datetime.now()).isoformat(),
                "chat_type": "business",
                "is_business": True
            }
        ]

        normalized_items = []
        for msg in mock_whatsapp_messages:
            normalized_items.append(NormalizedCommunication(
                id=str(uuid.uuid4()),
                source="whatsapp",
                external_id=msg["id"],
                sender={"name": msg["sender_name"], "handle": msg["phone_number"]},
                recipient="me",
                content=msg["text"],
                timestamp=msg["timestamp"],
                metadata=msg
            ))
            
        return normalized_items
