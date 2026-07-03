from prioritizer import PriorityEngine
from ai_analyzer import AIAnalyzer
from scoring_service import ScoringService
from database import db

# Shared service instances to avoid circular imports
engine = PriorityEngine()
analyzer = AIAnalyzer()
scoring_service = ScoringService(engine, analyzer, db=db)

# We use the dicts directly from db to ensure they stay in sync after db.clear()
archived_items = db.archived_items
snoozed_items = db.snoozed_items
