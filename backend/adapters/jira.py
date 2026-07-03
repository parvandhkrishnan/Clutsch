import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from .base import BaseAdapter, NormalizedCommunication

class JiraAdapter(BaseAdapter):
    def get_provider_name(self) -> str:
        return "jira"

    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        # Mocking Jira issue/comment data with varied priorities
        mock_jira_items = [
            {
                "id": "jira-bug-101",
                "key": "PROJ-101",
                "summary": "Critical: Authentication failing for new users",
                "description": "Users are reporting 500 errors when trying to sign up since the last deploy.",
                "reporter": {"displayName": "QA Engineer", "name": "qa.engineer"},
                "assignee": {"displayName": "Me", "name": "me"},
                "issue_type": "bug",
                "priority": "highest",
                "status": "To Do",
                "project_key": "PROJ",
                "updated": (datetime.now()).isoformat()
            },
            {
                "id": "jira-feat-202",
                "key": "PROJ-202",
                "summary": "Feature Request: Add dark mode toggle",
                "description": "As a user, I want to be able to switch to dark mode to save my eyes.",
                "reporter": {"displayName": "Product Manager", "name": "pm.user"},
                "assignee": {"displayName": "Me", "name": "me"},
                "issue_type": "story",
                "priority": "medium",
                "status": "Backlog",
                "project_key": "PROJ",
                "updated": (datetime.now()).isoformat()
            },
            {
                "id": "jira-comm-303",
                "key": "PROJ-101",
                "summary": "Lead Dev commented on PROJ-101",
                "comment_author": {"displayName": "Lead Dev", "name": "lead.dev"},
                "text": "I've started looking into this. Seems related to the latest SDK update. We need a fix ASAP.",
                "issue_type": "comment",
                "priority": "high",
                "project_key": "PROJ",
                "updated": (datetime.now()).isoformat()
            },
            {
                "id": "jira-task-404",
                "key": "PROJ-404",
                "summary": "Update documentation for API v2",
                "description": "The API documentation is outdated and needs to be updated with the new endpoints.",
                "reporter": {"displayName": "Sarah Connor", "name": "sarah.c"},
                "assignee": {"displayName": "Me", "name": "me"},
                "issue_type": "task",
                "priority": "low",
                "status": "In Progress",
                "project_key": "PROJ",
                "updated": (datetime.now()).isoformat()
            }
        ]

        normalized_items = []
        for item in mock_jira_items:
            normalized_items.append(self.normalize(item))
            
        return normalized_items

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedCommunication:
        content = raw_data.get("text") or raw_data.get("description") or raw_data.get("summary")
        
        # Determine sender info based on item type
        sender_info = raw_data.get("comment_author") or raw_data.get("reporter") or {"displayName": "Unknown", "name": "unknown"}
        
        return NormalizedCommunication(
            id=str(uuid.uuid4()),
            source="jira",
            external_id=raw_data["id"],
            thread_id=raw_data["key"],
            sender={
                "name": sender_info["displayName"], 
                "handle": sender_info["name"]
            },
            recipient="me",
            subject=raw_data["summary"],
            content=content,
            timestamp=raw_data["updated"],
            metadata=raw_data
        )
