"""
Compliance audit logging for DPDP, GDPR, and CCPA requests.
Entries use a hashed user reference (SHA-256 of user_id with a fixed pepper) 
instead of raw PII. This means the audit log survives user erasure — the 
hashed reference is not PII per most DPA interpretations, and there is no 
way to reverse it back to the original user_id after erasure.

The audit log itself is NOT erasable by the erasure flow (by regulation).
"""
import time
import hashlib
import json
from typing import Optional, Dict, Any, List
from threading import Lock

# Fixed pepper for hashing — in production, load from env
_AUDIT_PEPPER = "clutsch-compliance-audit-pepper-v1"

_compliance_audit_log: List[Dict[str, Any]] = []
_audit_lock = Lock()


def _hash_user_ref(user_id: str) -> str:
    """Create an anonymized, non-reversible user reference for audit logs."""
    raw = f"{user_id}::{_AUDIT_PEPPER}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def log_compliance_event(
    user_id: str,
    regulation: str,        # "DPDP" | "GDPR" | "CCPA"
    request_type: str,      # "CONSENT_CHANGE" | "DATA_ACCESS" | "DATA_EXPORT" | 
                            # "DATA_ERASURE" | "DATA_RECTIFICATION" | "RESTRICT_PROCESSING" |
                            # "DO_NOT_SELL" | "NOMINATE" | "GRIEVANCE"
    outcome: str,           # "fulfilled" | "rejected" | "pending"
    details: Optional[str] = None
):
    """Record a compliance event. The user_id is hashed on write."""
    entry = {
        "timestamp": time.time(),
        "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_ref": _hash_user_ref(user_id),
        "regulation": regulation,
        "request_type": request_type,
        "outcome": outcome,
    }
    if details:
        entry["details"] = details

    with _audit_lock:
        _compliance_audit_log.append(entry)
    return entry


def get_compliance_audit_log(
    regulation: Optional[str] = None,
    request_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieve compliance audit log entries, optionally filtered."""
    with _audit_lock:
        results = list(_compliance_audit_log)
    
    if regulation:
        results = [e for e in results if e["regulation"] == regulation]
    if request_type:
        results = [e for e in results if e["request_type"] == request_type]
    
    return sorted(results, key=lambda e: e["timestamp"], reverse=True)[:limit]


def clear_compliance_audit_log():
    """Clear the audit log (test helper only — never call in production)."""
    with _audit_lock:
        _compliance_audit_log.clear()


def get_audit_stats() -> Dict[str, Any]:
    """Return summary stats about the compliance audit log."""
    with _audit_lock:
        total = len(_compliance_audit_log)
        by_regulation = {}
        by_outcome = {}
        for e in _compliance_audit_log:
            reg = e["regulation"]
            by_regulation[reg] = by_regulation.get(reg, 0) + 1
            out = e["outcome"]
            by_outcome[out] = by_outcome.get(out, 0) + 1
        return {
            "total_entries": total,
            "by_regulation": by_regulation,
            "by_outcome": by_outcome
        }