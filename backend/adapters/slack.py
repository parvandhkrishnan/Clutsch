import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseAdapter, NormalizedCommunication

class SlackAdapter(BaseAdapter):
    def get_provider_name(self) -> str:
        return "slack"

    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        # Mocking Slack Web/Events API response
        mock_slack_messages = [
            {
                "client_msg_id": "sl-001",
                "type": "message",
                "text": "URGENT: The production server is down! We need everyone on the war room bridge ASAP.",
                "user": "U12345",
                "user_name": "Alice (Ops)",
                "ts": "1716712800.000100",
                "channel": "C99999",
                "channel_name": "ops-incidents",
                "metadata": {
                    "is_urgent": True,
                    "message_type": "mention"
                }
            },
            {
                "client_msg_id": "sl-002",
                "type": "message",
                "text": "Hey, did you see my comment on the PR? I think we should refactor the auth logic.",
                "user": "U67890",
                "user_name": "Bob (Dev)",
                "ts": "1716713400.000200",
                "channel": "D11111",
                "channel_name": "direct-message",
                "thread_ts": "1716713000.000050",
                "metadata": {
                    "is_urgent": False,
                    "message_type": "dm"
                }
            },
            {
                "client_msg_id": "sl-003",
                "type": "message",
                "text": "Can we move our 1:1 to tomorrow? I have a conflict.",
                "user": "U24680",
                "user_name": "Charlie (Manager)",
                "ts": "1716714000.000300",
                "channel": "D22222",
                "channel_name": "direct-message",
                "metadata": {
                    "is_urgent": False,
                    "message_type": "dm"
                }
            }
        ]

        normalized_items = []
        for msg in mock_slack_messages:
            normalized_items.append(self.normalize(msg))
        
        return normalized_items

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedCommunication:
        # Slack timestamps are strings representing unix time (e.g. "1716712800.000100")
        ts_float = float(raw_data.get("ts", datetime.now().timestamp()))
        iso_timestamp = datetime.fromtimestamp(ts_float).isoformat()

        return NormalizedCommunication(
            id=str(uuid.uuid4()),
            source="slack",
            external_id=raw_data.get("client_msg_id") or raw_data.get("ts"),
            thread_id=raw_data.get("thread_ts"),
            sender={
                "name": raw_data.get("user_name", "Unknown"),
                "handle": raw_data.get("user", "Unknown"),
            },
            recipient="me", # In a real app, this would be the current user's Slack ID
            content=raw_data.get("text", ""),
            timestamp=iso_timestamp,
            metadata=raw_data
        )
