import logging
from typing import List, Dict, Any
from database import db
import datetime

logger = logging.getLogger("workflow_service")

class WorkflowService:
    def __init__(self, db_instance):
        self.db = db_instance

    async def run_workflows_for_items(self, tenant_id: str, items: List[Dict[str, Any]]):
        """
        Evaluate items against active workflows and execute actions.
        """
        workflows = self.db.get_workflows(tenant_id)
        active_workflows = [w for w in workflows.values() if w.get("enabled", True)]
        
        if not active_workflows:
            return

        for item in items:
            for workflow in active_workflows:
                if self._check_conditions(item, workflow.get("conditions", [])):
                    await self._execute_actions(tenant_id, item, workflow.get("actions", []))

    def _check_conditions(self, item: Dict[str, Any], conditions: List[Dict[str, Any]]) -> bool:
        if not conditions:
            return False
            
        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator")
            expected_value = cond.get("value")
            
            # Get actual value from item or metadata
            actual_value = item.get(field)
            if actual_value is None and "metadata" in item:
                actual_value = item["metadata"].get(field)
            
            if not self._evaluate_condition(actual_value, operator, expected_value):
                return False # All conditions must match (AND logic)
                
        return True

    def _evaluate_condition(self, actual, operator, expected) -> bool:
        if actual is None:
            return False
            
        try:
            if operator == "gt": return float(actual) > float(expected)
            if operator == "lt": return float(actual) < float(expected)
            if operator == "eq": return str(actual) == str(expected)
            if operator == "contains": return str(expected).lower() in str(actual).lower()
        except (ValueError, TypeError):
            return False
        return False

    async def _execute_actions(self, tenant_id: str, item: Dict[str, Any], actions: List[Dict[str, Any]]):
        item_id = item["id"]
        
        # We need access to snoozed/archived sets. In this mock, they are in db.
        # But ScoringService/main.py uses the global ones.
        # Let's import them or use db helpers if they exist.
        
        from services import archived_items, snoozed_items
        from team_routes import delegate_item # Careful with circular imports
        from realtime_routes import notify_delegation

        for action in actions:
            action_type = action.get("type")
            params = action.get("params", {})
            
            logger.info(f"Executing workflow action {action_type} for item {item_id}")
            
            if action_type == "archive":
                if tenant_id not in archived_items:
                    archived_items[tenant_id] = set()
                archived_items[tenant_id].add(item_id)
                self.db.add_audit_log("system", "workflow_archive", f"Auto-archived item {item_id}")
                
            elif action_type == "snooze":
                hours = params.get("hours", 24)
                if tenant_id not in snoozed_items:
                    snoozed_items[tenant_id] = {}
                until = datetime.datetime.now() + datetime.timedelta(hours=hours)
                snoozed_items[tenant_id][item_id] = until
                self.db.add_audit_log("system", "workflow_snooze", f"Auto-snoozed item {item_id} for {hours}h")
                
            elif action_type == "delegate":
                to_user_id = params.get("to_user_id")
                if to_user_id:
                    success = self.db.delegate_item(
                        item_id=item_id,
                        tenant_id=tenant_id,
                        to_user_id=to_user_id,
                        assigned_by="system",
                        note=params.get("note", "Auto-delegated by workflow")
                    )
                    if success:
                        # Notify via WebSocket if possible
                        try:
                            await notify_delegation(tenant_id, to_user_id, item_id, "System")
                        except Exception:
                            pass
                        self.db.add_audit_log("system", "workflow_delegate", f"Auto-delegated item {item_id} to {to_user_id}")

workflow_service = WorkflowService(db)
