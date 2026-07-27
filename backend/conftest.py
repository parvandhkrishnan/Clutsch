"""Shared test fixtures — reset state between tests so rate limiters don't bleed over."""
import os
import pytest
from main import app
from database import db
import auth.models
from compliance_audit import clear_compliance_audit_log


@pytest.fixture(autouse=True)
def reset_state():
    """Reset rate limiter, database, and user model state before every test."""
    # Reset the shared rate limiter so each test starts with a clean budget
    app.state.limiter.reset()
    # Clear in-memory database state
    db.clear()
    for attr in ['failed_login_attempts', 'locked_accounts', 'audit_logs',
                 'mfa_secrets', 'mfa_pending_secrets', 'mfa_recovery_codes',
                 'consent_preferences', 'do_not_sell', 'processing_restrictions']:
        if hasattr(db, attr) and isinstance(getattr(db, attr), dict):
            getattr(db, attr).clear()
        elif hasattr(db, attr) and isinstance(getattr(db, attr), list):
            getattr(db, attr).clear()
    # Reset user model cache so users are recreated fresh (mfa_enabled resets)
    auth.models._users_db = None
    # Reset MAX_LOGIN_ATTEMPTS to default
    os.environ.pop("MAX_LOGIN_ATTEMPTS", None)
    # Clear DPDP consent records
    for attr in ['consent_records', 'nominees']:
        if hasattr(db, attr):
            setattr(db, attr, {})
    if hasattr(db, 'grievance_logs'):
        db.grievance_logs = []
    # Clear compliance audit log
    clear_compliance_audit_log()
    yield