import datetime
from typing import Any, Dict, List, Tuple
from prioritizer import PriorityEngine
from ai_analyzer import AIAnalyzer
from scoring_service import ScoringService
from database import db

# Shared service instances to avoid circular imports
engine = PriorityEngine()
analyzer = AIAnalyzer()
scoring_service = ScoringService(engine, analyzer, db=db)


def split_archived_snoozed(items: List[Dict[str, Any]]) -> Tuple[set, Dict[str, datetime.datetime]]:
    """Derive the (archived_ids, snoozed_until_by_id) pair that ScoringService
    and various routes need, from each item's own is_archived/is_snoozed/
    snoozed_until columns — replaces the old separate archived_items/
    snoozed_items in-memory dicts (now real Item columns, see models.py)."""
    archived_ids = {i["id"] for i in items if i.get("is_archived")}
    snoozed = {
        i["id"]: i["snoozed_until"]
        for i in items
        if i.get("is_snoozed") and i.get("snoozed_until")
    }
    return archived_ids, snoozed
