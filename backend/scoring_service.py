import datetime
from typing import List, Dict, Any, Tuple
from prioritizer import PriorityEngine
from ai_analyzer import AIAnalyzer

class ScoringService:
    def __init__(self, engine: PriorityEngine, analyzer: AIAnalyzer, db=None):
        self.engine = engine
        self.analyzer = analyzer
        self.db = db

    def process_items(self, tenant_id: str, items: List[Dict[str, Any]], archived_ids: set, snoozed_items: Dict[str, datetime.datetime], contact_priorities: Dict[str, Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Process a list of items: filter, analyze, score, and sort.
        """
        now = datetime.datetime.now()
        processed_items = []
        
        # Fetch custom weights for the tenant
        custom_weights = None
        semantic_weights = {}
        project_priorities = {}
        client_priorities = {}
        if self.db:
            custom_weights = self.db.get_custom_weights(tenant_id)
            semantic_weights = self.db.get_semantic_weights(tenant_id)
            project_priorities = self.db.get_project_priorities(tenant_id)
            client_priorities = self.db.get_client_priorities(tenant_id)

        for item in items:
            # Filter archived and snoozed
            if item["id"] in archived_ids:
                continue
            if item["id"] in snoozed_items and snoozed_items[item["id"]] > now:
                continue

            # Analyze with AI
            text = item.get("content") or item.get("text") or ""
            analysis = self.analyzer.analyze_message(text)
            
            # Extract source-specific signals
            multiplier, explanation_parts, boosts = self._get_source_signals(item)

            # Apply semantic weighting (New)
            semantic_boost = 0.0
            found_semantics = analysis.get("semantics", [])
            for concept in found_semantics:
                boost = semantic_weights.get(concept, 0.0)
                if boost > 0:
                    semantic_boost += boost
                    explanation_parts.append(f"Semantic match: {concept.replace('_', ' ')}")

            # Apply manual contact priorities
            contact_multiplier, contact_explanation = self._get_contact_signals(item, contact_priorities)
            if contact_multiplier != 1.0:
                multiplier *= contact_multiplier
                explanation_parts.append(contact_explanation)

            # Apply entity weighting (New)
            metadata = item.get("metadata", {})
            project_id = metadata.get("project_id")
            if project_id and project_id in project_priorities:
                p_priority = project_priorities[project_id].lower()
                if p_priority == "high": multiplier *= 1.3; explanation_parts.append(f"High priority project ({project_id})")
                elif p_priority == "low": multiplier *= 0.7; explanation_parts.append(f"Low priority project ({project_id})")

            client_id = metadata.get("client_id")
            if client_id and client_id in client_priorities:
                c_priority = client_priorities[client_id].lower()
                if c_priority == "high": multiplier *= 1.4; explanation_parts.append(f"High priority client ({client_id})")
                elif c_priority == "low": multiplier *= 0.6; explanation_parts.append(f"Low priority client ({client_id})")
            
            urgency_boost, importance_boost = boosts
            
            final_urgency = min(1.0, analysis.get("urgency", 0.0) + urgency_boost)
            final_importance = min(1.0, analysis.get("importance", 0.0) + importance_boost + semantic_boost)
            
            # Contextual Scaling (New)
            context_multiplier, context_explanation = self._get_contextual_signals(now, item.get("deadline"))
            if context_multiplier != 1.0:
                multiplier *= context_multiplier
                explanation_parts.append(context_explanation)

            # Calculate priority score (0.0 - 1.0)
            # Use custom weights if available
            original_weights = self.engine.weights
            if custom_weights:
                self.engine.weights = custom_weights

            base_score = self.engine.score(
                urgency=final_urgency,
                importance=final_importance,
                sender_rank=item.get("sender_rank", 0.5),
                deadline=item.get("deadline")
            )
            
            # Restore weights
            self.engine.weights = original_weights
            
            # Apply source multiplier and convert to 0-100 scale
            final_score_raw = min(1.0, base_score * multiplier)
            priority_score = round(final_score_raw * 100, 2)
            
            # Determine Tier
            priority_tier = self._get_tier(priority_score)
            
            # Final Explanation
            ai_summary = analysis.get("summary", "")
            if ai_summary and not ai_summary.endswith('.'):
                ai_summary += '.'
                
            source_explanation = ". ".join(explanation_parts)
            if source_explanation and not source_explanation.endswith('.'):
                source_explanation += '.'
                
            final_explanation = f"{ai_summary} {source_explanation}".strip()
            if not final_explanation:
                final_explanation = f"Ranked {priority_tier} based on general signals."

            processed_items.append({
                **item,
                "priorityScore": priority_score,
                "priorityTier": priority_tier,
                "explanation": final_explanation,
                "urgency": final_urgency,
                "importance": final_importance,
                "ai_summary": ai_summary,
                "action_suggested": analysis.get("action_suggested", "Review")
            })
        
        # Sort by priority score descending
        processed_items.sort(key=lambda x: x["priorityScore"], reverse=True)
        return processed_items

    def _get_contextual_signals(self, now: datetime.datetime, deadline: Any) -> Tuple[float, str]:
        multiplier = 1.0
        explanation = ""
        
        # Time of day scaling (Business hours boost)
        # Assuming 9 AM to 6 PM (9-18)
        if 9 <= now.hour < 18:
            multiplier *= 1.1
            explanation = "Active business hours scaling applied"
        
        # Proximity to deadline scaling
        if deadline:
            if isinstance(deadline, str):
                try:
                    if deadline.endswith('Z'):
                        deadline = deadline.replace('Z', '+00:00')
                    deadline = datetime.datetime.fromisoformat(deadline)
                except ValueError:
                    deadline = None
            
            if deadline:
                # Ensure we compare timezone-aware or timezone-naive consistently
                if deadline.tzinfo is not None:
                    now_tz = datetime.datetime.now(datetime.timezone.utc)
                else:
                    now_tz = now
                    
                time_diff = (deadline - now_tz).total_seconds()
                
                # If deadline is within 4 hours, significant boost
                if 0 < time_diff < 4 * 3600:
                    multiplier *= 1.25
                    if explanation: explanation += ". "
                    explanation += "Critical deadline proximity (within 4h)"
                # If deadline is today
                elif 0 < time_diff < 24 * 3600:
                    multiplier *= 1.15
                    if explanation: explanation += ". "
                    explanation += "Impending deadline today"

        return multiplier, explanation

    def _get_tier(self, score: float) -> str:
        if score >= 80:
            return "urgent"
        elif score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        else:
            return "low"

    def _get_source_signals(self, item: Dict[str, Any]) -> Tuple[float, List[str], Tuple[float, float]]:
        source = item.get("source", "").lower()
        multiplier = 1.0
        explanations = []
        urgency_boost = 0.0
        importance_boost = 0.0
        metadata = item.get("metadata", {})

        # Deadline signal
        deadline = item.get("deadline")
        if deadline:
            explanations.append("Approaching deadline detected")

        if source == "jira":
            priority = metadata.get("priority", "").lower()
            if priority == "highest":
                multiplier = 1.25
                explanations.append("Highest Jira priority override")
            elif priority == "high":
                multiplier = 1.15
                explanations.append("High Jira priority signal")
            
            if metadata.get("issue_type") == "bug":
                importance_boost = 0.1
                explanations.append("Issue is a bug report")
                
        elif source == "slack":
            msg_type = metadata.get("message_type") or metadata.get("metadata", {}).get("message_type")
            if msg_type == "dm":
                multiplier = 1.1
                explanations.append("Direct Message from colleague")
            
            is_urgent = metadata.get("is_urgent") or metadata.get("metadata", {}).get("is_urgent")
            if is_urgent is True:
                multiplier *= 1.2
                explanations.append("Explicitly marked as urgent in Slack")
                
        elif source == "teams":
            if metadata.get("message_type") == "mention":
                multiplier = 1.15
                explanations.append("Directly mentioned in Teams")
                
        elif source == "outlook":
            if "Urgent" in metadata.get("categories", []):
                multiplier = 1.2
                explanations.append("Categorized as Urgent in Outlook")
                
        elif source == "whatsapp":
            if metadata.get("chat_type") == "personal":
                urgency_boost = 0.1
                explanations.append("Personal WhatsApp message")

        # Custom Boost from triggers
        if metadata.get("custom_boost"):
            importance_boost += metadata.get("custom_boost")
            explanations.append("Custom urgency trigger matched")

        return multiplier, explanations, (urgency_boost, importance_boost)
    def _get_contact_signals(self, item: Dict[str, Any], contact_priorities: Dict[str, Dict[str, str]]) -> Tuple[float, str]:
        if not contact_priorities:
            return 1.0, ""
        
        source = item.get("source", "").lower()
        sender = item.get("sender", {})
        handle = sender.get("handle")
        
        if not handle or source not in contact_priorities:
            return 1.0, ""
        
        priority = contact_priorities[source].get(handle, "").lower()
        if priority == "high":
            return 1.5, f"High priority contact ({handle})"
        elif priority == "low":
            return 0.5, f"Low priority contact ({handle})"
        elif priority == "medium":
            return 1.1, f"Medium priority contact ({handle})"
            
        return 1.0, ""
