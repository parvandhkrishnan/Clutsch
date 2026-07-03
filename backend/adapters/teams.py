import uuid
from datetime import datetime
from typing import List, Optional
from .base import BaseAdapter, NormalizedCommunication

class TeamsAdapter(BaseAdapter):
    def get_provider_name(self) -> str:
        return "teams"

    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        # Mocking Teams message data
        mock_teams_messages = [
            {
                "id": "teams-msg-1",
                "team_id": "team-alpha",
                "team_name": "Engineering",
                "channel_id": "chan-dev",
                "channel_name": "Development",
                "from": {"user": {"displayName": "Dave", "id": "user-dave"}},
                "body": {"content": "Can someone review my PR? It's blocking the release."},
                "createdDateTime": (datetime.now()).isoformat(),
                "message_type": "post"
            },
            {
                "id": "teams-msg-2",
                "from": {"user": {"displayName": "Manager", "id": "user-mgr"}},
                "body": {"content": "Do you have a minute for a quick call?"},
                "createdDateTime": (datetime.now()).isoformat(),
                "message_type": "chat"
            },
            {
                "id": "teams-msg-3",
                "team_name": "General",
                "channel_name": "Announcements",
                "from": {"user": {"displayName": "Bot", "id": "bot-1"}},
                "body": {"content": "Meeting 'Weekly Sync' is starting now. You were mentioned."},
                "createdDateTime": (datetime.now()).isoformat(),
                "message_type": "mention"
            }
        ]

        normalized_items = []
        for msg in mock_teams_messages:
            normalized_items.append(NormalizedCommunication(
                id=str(uuid.uuid4()),
                source="teams",
                external_id=msg["id"],
                sender={"name": msg["from"]["user"]["displayName"], "handle": msg["from"]["user"]["id"]},
                recipient="me",
                content=msg["body"]["content"],
                timestamp=msg["createdDateTime"],
                metadata=msg
            ))
            
        return normalized_items
