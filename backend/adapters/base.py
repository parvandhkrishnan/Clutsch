from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class NormalizedCommunication(BaseModel):
    id: str              # Internal UUID
    source: str          # 'gmail', 'slack', etc.
    external_id: str     # ID from the source platform
    thread_id: Optional[str] = None
    sender: Dict[str, Any] # { name: str, handle: str, avatar_url?: str }
    recipient: str
    subject: Optional[str] = None
    content: str
    html_content: Optional[str] = None
    timestamp: str       # ISO-8601
    deadline: Optional[str] = None
    source_url: Optional[str] = None
    metadata: Dict[str, Any]

class BaseAdapter(ABC):
    @abstractmethod
    async def fetch_items(self, token: Optional[str] = None) -> List[NormalizedCommunication]:
        """Fetch items from the source platform and normalize them."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of the provider."""
        pass
