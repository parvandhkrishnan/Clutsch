# PriorityFlow — Test Plan Execution Report
**Task:** QA: Execute Test Plan for Core & Enterprise Features (b384bd46)
**Date:** 2026-07-07
**Tester:** software_tester
**Environment:** Fresh backend instance (`uvicorn main:app`) on `127.0.0.1:8010`, code from `parvandhkrishnan/PF@main`. React frontend inspected at source level.

## Executive Summary
The application code boots and serves correctly. However, **two real backend defects** were found that affect core and compliance flows, plus **infrastructure/test-suite hygiene issues**. The shared backend on port 8001 (run by backend_engineer) was found **hung/unresponsive** during testing — see BUG-003.

| ID | Severity | Area | Status |
|----|----------|------|--------|
| BUG-001 | **High** | Core / Items | Open |
| BUG-002 | **High (Compliance)** | Privacy / DPDP | Open |
| BUG-003 | **High (Infra)** | Live backend :8001 | Open |
| BUG-004 | Medium | Test suite hygiene | Open |

---

## Feature Coverage

### 1. Quick Actions (Archive / Snooze) on Dashboard
- **Source review:** `frontend/src/pages/Dashboard.jsx` (527 lines) implements the dashboard item list and action handlers.
- **Backend dependency:** item mutation endpoints (`/items`).
- **Finding:** `POST /items` triggers a `NameError` in the realtime notification path (see **BUG-001**). Any Quick Action that creates/updates items risks hitting the same broken realtime notify code path. Requires re-test once BUG-001 is fixed.

### 2. Integration Hub (Gallery, Connection Modal, Settings UI)
- **Source review:** `pages/Integrations.jsx` (309), `components/IntegrationModal.jsx` (103), `components/IntegrationSettingsModal.jsx` (158).
- **Backend:** `POST /integrations/{provider}/connect` correctly **requires authentication** — returns `401` without a bearer token (verified). The legacy `test_api.py` asserts `200` without auth; that is a stale test, not a product bug (see BUG-004). Endpoint behavior is correct.

### 3. Team Collaboration (Shared Feed, Delegation Modal, Presence)
- **Source review:** `components/DelegationModal.jsx` (155); shared-feed and presence handled in Dashboard/Admin.
- **Backend:** `/items` feed retrieval works; multi-tenant scoping verified in `test_security.py` (`test_tenant_isolation_in_feed`, `test_cross_tenant_item_access_prevention` — **passing**).
- **Finding:** Delegation/feed writes route through `/items`, which is impacted by BUG-001.

---

## Bugs

### BUG-001 — `POST /items` crashes: `NameError: name 'notify_new_items' is not defined` — **High**
- **Repro:** Authenticated `POST /items` with `{"text": "...", "source": "Manual"}`.
- **Expected:** `200` and item created + realtime broadcast.
- **Actual:** Handler references undefined `notify_new_items`; request path raises `NameError`. Item creation / realtime broadcast is broken.
- **Impact:** Core item creation, Quick Actions, delegation writes, and shared-feed updates all flow through this path.
- **Evidence:** `/tmp/my_backend.log` — `NameError: name 'notify_new_items' is not defined`.

### BUG-002 — `DELETE /privacy/account` returns 500: `'MockDatabase' object has no attribute 'delete_tenant_data'` — **High (Compliance)**
- **Repro:** Authenticated `DELETE /privacy/account`.
- **Expected:** `200`, account + tenant data erased (DPDP right-to-erasure).
- **Actual:** `500 Internal Server Error`; `privacy_routes.py:55` calls `db.delete_tenant_data()` which does not exist on the DB object.
- **Impact:** Data-deletion / right-to-erasure is broken — a **DPDP compliance risk** for the India-focused product.
- **Note:** `GET /privacy/export` returns `200` and works.

### BUG-003 — Shared backend on port 8001 is hung / unresponsive — **High (Infra)**
- **Observed:** All routes on `http://localhost:8001` (`/health`, `/docs`, `/`, `/integrations/*/connect`) returned `000` (timeout, no HTTP response) for >5s each. The process (`uvicorn main:app`, owner `agent-backend-engineer`, up ~16h) is listening but not serving.
- **Verification it is a runtime, not code, issue:** a fresh instance of the *same code* on :8010 returned `/health -> 200` instantly.
- **Recommendation:** backend_engineer should restart the :8001 instance and investigate the hang (possible event-loop deadlock / exhausted worker). I did **not** kill the shared process.

### BUG-004 — Legacy smoke tests are stale and inconsistent — **Medium**
- `test_api.py`, `test_auth.py`, `test_health.py`, `test_rate_limit.py`, `test_sync_settings.py` hardcode `BASE_URL = http://localhost:3000`; `test_privacy.py` uses `:8001`. Neither matches the app port (8001 for API). Tests require a live server (they use `requests`, not FastAPI `TestClient`).
- `test_api.py` / `test_auth.py` assume seed passwords (`admin123`, `password`) and unauthenticated connect returning 200 — both outdated.
- **Recommendation:** parameterize `BASE_URL` via env var, use `TestClient` for in-process tests, and align seed credentials with `.env`.

## How to Reproduce
```bash
cd ~/PF/backend
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
export JWT_SECRET_KEY=x JOHN_PASSWORD=password ADMIN_PASSWORD=admin123 ENFORCE_HTTPS=false GOOGLE_API_KEY=test
python3 -m uvicorn main:app --host 127.0.0.1 --port 8010
# then exercise POST /items and DELETE /privacy/account with a valid bearer token
```
