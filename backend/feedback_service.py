import logging
from typing import Dict, Any, List, Optional
from database import db
from ai_analyzer import AIAnalyzer

logger = logging.getLogger("feedback_service")

class FeedbackService:
    def __init__(self, db_instance, analyzer: AIAnalyzer):
        self.db = db_instance
        self.analyzer = analyzer
        self.adjustment_step = 0.05
        self.max_boost = 0.5
        self.min_boost = 0.0

    async def process_feedback(self, tenant_id: str, user_id: str, item_id: str, feedback_type: str, suggested_tier: Optional[str] = None):
        """
        Process user feedback on an item's priority.
        feedback_type: 'agree', 'disagree', 'correction'
        suggested_tier: 'urgent', 'high', 'medium', 'low'
        """
        # 1. Get the item from DB
        items = self.db.get_items(tenant_id)
        item = next((i for i in items if i["id"] == item_id), None)
        
        if not item:
            logger.warning(f"Item {item_id} not found for tenant {tenant_id}")
            return False

        # 2. Re-analyze or use item metadata to find semantics
        # Preferably, the item already has ai_analysis or semantics in it if processed by ScoringService
        semantics = item.get("semantics", [])
        if not semantics:
            # Try to get from AI analysis if available in item
            analysis = self.analyzer.analyze_message(item.get("content") or item.get("text") or "")
            semantics = analysis.get("semantics", [])

        if feedback_type == "agree":
            # Optional: reinforce slightly? 
            # For now, just log it.
            self.db.add_audit_log(user_id, "priority_feedback", f"User agreed with priority for item {item_id}")
            return True

        if feedback_type == "correction" and suggested_tier:
            current_tier = item.get("priorityTier", "low")
            if current_tier == suggested_tier:
                return True # No change needed
            
            # Determine direction
            tier_ranks = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
            current_rank = tier_ranks.get(current_tier, 0)
            target_rank = tier_ranks.get(suggested_tier, 0)
            
            direction = 1 if target_rank > current_rank else -1
            
            # Adjust semantic weights
            if semantics:
                weights = self.db.get_semantic_weights(tenant_id)
                for concept in semantics:
                    current_weight = weights.get(concept, 0.15) # Default if not set
                    new_weight = current_weight + (direction * self.adjustment_step)
                    new_weight = max(self.min_boost, min(self.max_boost, new_weight))
                    weights[concept] = round(new_weight, 3)
                
                self.db.set_semantic_weights(tenant_id, weights)
                self.db.add_audit_log(user_id, "auto_tuning", f"Adjusted weights for {semantics} based on feedback for {item_id}")

            # Adjust entity weights (Project/Client)
            metadata = item.get("metadata", {})
            project_id = metadata.get("project_id")
            if project_id:
                p_priorities = self.db.get_project_priorities(tenant_id)
                current_p = p_priorities.get(project_id, "medium").lower()
                # Simple logic: if correction to higher, bump project to high. If lower, bump to low.
                if direction > 0:
                    p_priorities[project_id] = "high"
                else:
                    p_priorities[project_id] = "low"
                self.db.set_project_priority(tenant_id, project_id, p_priorities[project_id])

            client_id = metadata.get("client_id")
            if client_id:
                c_priorities = self.db.get_client_priorities(tenant_id)
                if direction > 0:
                    c_priorities[client_id] = "high"
                else:
                    c_priorities[client_id] = "low"
                self.db.set_client_priority(tenant_id, client_id, c_priorities[client_id])

            return True

        return False

# Initialize service (using shared instances)
from services import analyzer
feedback_service = FeedbackService(db, analyzer)
