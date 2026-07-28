from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional, Dict, Any
from auth.models import User
from auth.dependencies import get_current_active_user
from database import db
import time
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/metrics")
async def get_enterprise_metrics(current_user: User = Depends(get_current_active_user)):
    """
    Aggregate and return Enterprise KPIs for the tenant.
    """
    tenant_id = current_user.tenant_id
    items = await db.get_items(tenant_id)
    audit_logs = await db.get_audit_logs(tenant_id)

    # 1. Priority Distribution
    priority_dist = {"urgent": 0, "high": 0, "medium": 0, "low": 0}
    # We need to score items to get their priority tier
    from services import scoring_service, split_archived_snoozed
    tenant_archived, tenant_snoozed = split_archived_snoozed(items)
    scored_items = await scoring_service.process_items(tenant_id, items, tenant_archived, tenant_snoozed, {})
    
    for item in scored_items:
        tier = item.get("priorityTier", "low")
        if tier in priority_dist:
            priority_dist[tier] += 1

    # 2. Time to Action
    # Measure duration from item creation to action (archive, snooze, delegate)
    action_times = []
    actions = ["archive_item", "snooze_item", "delegate_item"]
    
    # Map item_id to creation time
    item_creation_times = {item["id"]: item.get("timestamp", time.time()) for item in items}
    
    for log in audit_logs:
        if log["action"] in actions:
            # Extract item_id from details (string parsing in this mock setup)
            # In production, this would be a structured field
            details = log["details"]
            try:
                # Assuming details like "Archived item <uuid>" or "Delegated item <uuid> to <user_id>"
                item_id = details.split("item ")[1].split(" ")[0]
                if item_id in item_creation_times:
                    duration = log["timestamp"] - item_creation_times[item_id]
                    action_times.append(duration)
            except:
                continue
    
    avg_time_to_action = sum(action_times) / len(action_times) if action_times else 0

    # 3. Team Focus Score
    # Example logic: % of critical items resolved (archived/delegated) within 30 mins
    critical_items = [i for i in scored_items if i.get("priorityTier") == "urgent"]
    resolved_critical = 0
    
    for item in critical_items:
        # Check if resolved in audit logs
        resolution_log = next((l for l in audit_logs if item["id"] in l["details"] and l["action"] in ["archive_item", "delegate_item"]), None)
        if resolution_log:
            if resolution_log["timestamp"] - item.get("timestamp", time.time()) < 30 * 60:
                resolved_critical += 1
    
    focus_score = (resolved_critical / len(critical_items) * 100) if critical_items else 100

    # 4. Activity Trends — real daily activity volume over the last 7 days,
    # combining item creation (from Item.timestamp, an epoch float) and audit
    # log actions (from AuditLog.timestamp, also an epoch float) so days with
    # only new items (no actions taken yet) still show up.
    trend_days = 7
    today = datetime.now().date()
    day_keys = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(trend_days)]
    day_buckets = {day_key: 0 for day_key in day_keys}

    for item in items:
        ts = item.get("timestamp")
        if ts is None:
            continue
        day_key = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        if day_key in day_buckets:
            day_buckets[day_key] += 1

    for log in audit_logs:
        ts = log.get("timestamp")
        if ts is None:
            continue
        day_key = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        if day_key in day_buckets:
            day_buckets[day_key] += 1

    trends = [{"date": day_key, "actions": day_buckets[day_key]} for day_key in day_keys]

    return {
        "priority_distribution": priority_dist,
        "average_time_to_action_seconds": avg_time_to_action,
        "team_focus_score": focus_score,
        "activity_trends": trends,
        "total_items_processed": len(items),
        "total_actions_taken": len(audit_logs)
    }
