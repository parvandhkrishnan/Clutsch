import time
from typing import Any, Dict, Optional, List

class SimpleTTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._tags: Dict[str, List[str]] = {}  # tag -> [keys]

    def set(self, key: str, value: Any, tags: Optional[List[str]] = None):
        self.cache[key] = {
            "value": value,
            "expiry": time.time() + self.ttl
        }
        # Register tags for invalidation
        if tags:
            for tag in tags:
                if tag not in self._tags:
                    self._tags[tag] = []
                self._tags[tag].append(key)

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

    def invalidate_tag(self, tag: str):
        """Invalidate all cache entries that were stored with the given tag."""
        if tag not in self._tags:
            return
        for key in self._tags[tag]:
            self.cache.pop(key, None)
        self._tags.pop(tag, None)

    def invalidate_all(self):
        """Clear the entire cache."""
        self.cache.clear()
        self._tags.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics for monitoring."""
        active = sum(1 for v in self.cache.values() if time.time() < v["expiry"])
        expired = len(self.cache) - active
        return {
            "total_entries": len(self.cache),
            "active": active,
            "expired": expired,
            "tags": len(self._tags)
        }

# Global cache instances
config_cache = SimpleTTLCache(ttl_seconds=600)   # 10 minutes
integration_cache = SimpleTTLCache(ttl_seconds=300)  # 5 minutes
