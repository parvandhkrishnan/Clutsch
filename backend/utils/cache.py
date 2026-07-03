import time
from typing import Any, Dict, Optional

class SimpleTTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any):
        self.cache[key] = {
            "value": value,
            "expiry": time.time() + self.ttl
        }

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if time.time() > item["expiry"]:
            del self.cache[key]
            return None
        
        return item["value"]

    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]

# Global cache instances
config_cache = SimpleTTLCache(ttl_seconds=600) # 10 minutes
integration_cache = SimpleTTLCache(ttl_seconds=300) # 5 minutes
