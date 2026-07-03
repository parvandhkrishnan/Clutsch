import httpx
import uuid
import time
from typing import List, Dict, Any, Optional
from adapters.base import BaseAdapter, NormalizedCommunication

class CustomAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "custom")
        self.mapping = config.get("mapping", {})
        self.urgency_triggers = config.get("urgency_triggers", [])

    def get_provider_name(self) -> str:
        return self.name

    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        url = self.config.get("url")
        method = self.config.get("method", "GET")
        headers = {}
        
        auth_type = self.config.get("auth_type", "none")
        if auth_type == "api_key":
            headers[self.config.get("auth_header", "X-API-Key")] = self.config.get("auth_value")
        elif auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.config.get('auth_value')}"
            
        async with httpx.AsyncClient() as client:
            try:
                if method == "POST":
                    response = await client.post(url, headers=headers)
                else:
                    response = await client.get(url, headers=headers)
                
                response.raise_for_status()
                raw_items = response.json()
                
                # If the response is a dict with a list field, try to find it
                if isinstance(raw_items, dict):
                    for key, value in raw_items.items():
                        if isinstance(value, list):
                            raw_items = value
                            break
                
                if not isinstance(raw_items, list):
                    return []
                
                return self._normalize(raw_items)
            except Exception as e:
                print(f"Error fetching from custom integration {self.name}: {e}")
                return []

    def _normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedCommunication]:
        normalized = []
        for raw in raw_items:
            try:
                # Basic mapping
                item_id = str(uuid.uuid4())
                external_id = str(self._get_mapped_value(raw, self.mapping.get("external_id", "id")))
                text = str(self._get_mapped_value(raw, self.mapping.get("text", "text")))
                sender_handle = str(self._get_mapped_value(raw, self.mapping.get("sender_handle", "sender")))
                sender_name = str(self._get_mapped_value(raw, self.mapping.get("sender_name", sender_handle)))
                
                # Build metadata and check urgency triggers
                metadata = raw.copy()
                
                # Apply urgency triggers to metadata for the scoring engine to find
                for trigger in self.urgency_triggers:
                    field = trigger.get("field")
                    value = trigger.get("value")
                    boost = trigger.get("boost", 0)
                    if self._get_mapped_value(raw, field) == value:
                        metadata["custom_boost"] = metadata.get("custom_boost", 0) + boost
                
                norm = NormalizedCommunication(
                    id=item_id,
                    source=self.name,
                    external_id=external_id,
                    sender={"name": sender_name, "handle": sender_handle},
                    recipient="user",
                    content=text,
                    timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    metadata=metadata
                )
                normalized.append(norm)
            except Exception as e:
                print(f"Error normalizing item: {e}")
                continue
        return normalized

    def _get_mapped_value(self, data: Dict[str, Any], path: str) -> Any:
        """Helper to get value from nested dict using dot notation."""
        if not path:
            return None
        parts = path.split(".")
        val = data
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                return None
        return val
