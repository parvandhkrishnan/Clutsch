# PriorityFlow Test Plan: Dashboard & Integrations Hub

**Date:** 2026-06-21  
**Author:** Software Tester (PriorityFlow)  
**Scope:** Dashboard Quick Actions, Integration Adapters (Slack/Gmail), Integration Connection Modal, Settings UI, Priority Scoring Edge Cases  

---

## 1. Overview

This test plan covers the functional validation, integration testing, and UI/UX verification of two critical user-facing areas of PriorityFlow:

1. **Dashboard** — The primary workspace where users view AI-prioritized communications and take quick actions (Archive, Snooze).
2. **Integrations Hub** — Where users connect, configure, and manage communication platform integrations (Slack, Gmail, Outlook, Teams, WhatsApp, Jira).

### Objectives
- Ensure Quick Actions (Archive/Snooze) work correctly across all item types and tiers.
- Validate Slack and Gmail adapter normalization, error handling, and tenant isolation.
- Verify the Integration Connection Modal and Settings Modal UI/UX flows.
- Identify edge cases in priority scoring where conflicting signals may produce unexpected results.

---

## 2. Test Environment

| Component | Version/Tool | Notes |
|-----------|-------------|-------|
| Backend | FastAPI + Python 3.12 | Run with `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, and password env vars set |
| Frontend | React 19 + Vite 8 | Build with `npm run build`; dev with `npm run dev` |
| Test Client | `fastapi.testclient.TestClient` | For backend unit/integration tests |
| Test Framework | `unittest` + `pytest` | Backend tests |
| E2E Framework | Playwright (recommended) | For frontend modal and dashboard flows |
| API Base URL | `http://localhost:3000` (backend) | Frontend expects `VITE_API_URL` |

### Environment Variables Required
```bash
JWT_SECRET_KEY=<secure-key>
ENCRYPTION_KEY=<base64-fernet-key>
ADMIN_PASSWORD=<admin-password>
JOHN_PASSWORD=<john-password>
SARAH_PASSWORD=<sarah-password>
```

---

## 3. Dashboard — Quick Actions Test Cases

### 3.1 Archive Action

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| DA-01 | Archive an item from the focus panel | User logged in, item selected in Dashboard | 1. Click "Mark Done" on selected item | Item removed from list, toast "Item archived" shown, `POST /items/{id}/archive` returns 200 | 🔴 High |
| DA-02 | Archive an urgent-tier item | User logged in, urgent item visible | 1. Select urgent item, click "Mark Done" | Item archived, stats count increments, item no longer appears in urgent tier filter | 🔴 High |
| DA-03 | Archive already-archived item (idempotency) | User logged in, item already archived | 1. Call `POST /items/{id}/archive` again | Returns 200 or 403 (consistent behavior), no duplicate audit log entries | 🟡 Medium |
| DA-04 | Archive item belonging to another tenant | Tenant A logged in, item belongs to Tenant B | 1. Attempt to archive Tenant B's item with Tenant A's token | Returns 403, anomaly logged: `TENANT_LEAK_ATTEMPT` | 🔴 High |
| DA-05 | Archive item without authentication | Not logged in | 1. Call `POST /items/{id}/archive` without Bearer token | Returns 401, `SECURITY_ANOMALY` logged | 🔴 High |
| DA-06 | Archive item from empty feed | Feed has 0 items | 1. Verify "All clear" empty state is shown | No crash, graceful empty state with correct tier label | 🟢 Low |

### 3.2 Snooze Action

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| DS-01 | Snooze item for 1 hour | User logged in, item selected | 1. Click "Snooze" on selected item | Item removed from active list, toast shows snooze duration, `POST /items/{id}/snooze` with `{hours: 1}` returns 200 | 🔴 High |
| DS-02 | Snooze item for 24 hours | User logged in, item selected | 1. Click "Snooze" with 24h duration | Item hidden until `now + 24h`, reappears after expiry | 🔴 High |
| DS-03 | Snoozed item reappears after expiry | Item snoozed 1 hour ago | 1. Wait 1+ hours (or manipulate system clock) | Item reappears in feed with original priority score | 🟡 Medium |
| DS-04 | Unsnooze a snoozed item | Item is currently snoozed | 1. Click "Unsnooze" (or call `POST /items/{id}/unsnooze`) | Item immediately reappears in feed, returns 200 | 🟡 Medium |
| DS-05 | Unsnooze already-unsnoozed item | Item is not snoozed | 1. Call `POST /items/{id}/unsnooze` | Returns 200 (idempotent), no error | 🟢 Low |
| DS-06 | Snooze item from another tenant | Tenant A logged in | 1. Attempt to snooze Tenant B's item | Returns 403, `TENANT_LEAK_ATTEMPT` logged | 🔴 High |
| DS-07 | Snooze with invalid duration (negative) | User logged in | 1. Call `POST /items/{id}/snooze` with `{hours: -1}` | Returns 400 or gracefully handles (no crash) | 🟡 Medium |
| DS-08 | Snooze with zero duration | User logged in | 1. Call `POST /items/{id}/snooze` with `{hours: 0}` | Returns 200, item may immediately reappear | 🟢 Low |

### 3.3 Dashboard Feed & Tier Filtering

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| DF-01 | Feed loads with AI scores | User has items | 1. Open Dashboard | Items display `priorityScore`, `priorityTier`, `ai_summary`, `explanation` | 🔴 High |
| DF-02 | Filter by urgent tier | Items exist across all tiers | 1. Click "urgent" tier chip | Only items with `priorityTier === "urgent"` shown, URL query param `tier=urgent` passed | 🔴 High |
| DF-03 | Filter by high tier | Items exist across all tiers | 1. Click "high" tier chip | Only high-tier items shown | 🔴 High |
| DF-04 | Filter by medium tier | Items exist across all tiers | 1. Click "medium" tier chip | Only medium-tier items shown | 🟡 Medium |
| DF-05 | Filter by low tier | Items exist across all tiers | 1. Click "low" tier chip | Only low-tier items shown | 🟡 Medium |
| DF-06 | Switch back to "all" tiers | Currently filtering by tier | 1. Click "all" tier chip | All items shown, no query param | 🟡 Medium |
| DF-07 | Empty state for tier filter | No items in selected tier | 1. Click tier with 0 items | Shows "All clear in the [tier] tier!" empty state | 🟡 Medium |
| DF-08 | Select item updates focus panel | Feed has items | 1. Click different items in list | Focus panel updates with correct item details, gauge, and actions | 🔴 High |
| DF-09 | Auto-select first item on load | Feed has items | 1. Refresh Dashboard | First item automatically selected in focus panel | 🟡 Medium |
| DF-10 | Dashboard unauthorized access | Not logged in | 1. Navigate to Dashboard | Redirected to login page | 🔴 High |

---

## 4. Integration Adapter Testing

### 4.1 Slack Adapter

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| IA-SL-01 | Fetch and normalize Slack messages | Slack adapter instantiated | 1. Call `SlackAdapter().fetch_items()` | Returns 3 `NormalizedCommunication` objects with correct fields | 🔴 High |
| IA-SL-02 | Verify normalized fields | Messages fetched | 1. Inspect first message | `source="slack"`, `sender.name="Alice (Ops)"`, `sender.handle="U12345"`, `metadata.is_urgent=true`, `metadata.message_type="mention"` | 🔴 High |
| IA-SL-03 | Timestamp conversion | Messages fetched | 1. Inspect `timestamp` field | ISO 8601 format derived from Slack unix timestamp string | 🟡 Medium |
| IA-SL-04 | DM vs channel message distinction | Messages fetched | 1. Compare message 1 (channel) vs message 2 (DM) | Message 1 has `channel_name="ops-incidents"`, Message 2 has `channel_name="direct-message"` | 🟡 Medium |
| IA-SL-05 | Thread ID presence | Messages fetched | 1. Inspect message 2 | `thread_id` is set to parent thread timestamp when applicable | 🟢 Low |
| IA-SL-06 | Empty token handling | No token provided | 1. Call `fetch_items(token=None)` | Returns mock data (current behavior), or raises appropriate error if token required | 🟡 Medium |
| IA-SL-07 | Tenant isolation after sync | Two tenants connected Slack | 1. Connect Slack for Tenant A and Tenant B, trigger sync | Tenant A only sees Tenant A's Slack messages, Tenant B only sees Tenant B's | 🔴 High |
| IA-SL-08 | Slack message with special characters | Adapter mocked with special chars | 1. Add message with emojis, URLs, mentions to mock data | Normalized `content` preserves text accurately, no encoding issues | 🟢 Low |

### 4.2 Gmail Adapter

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| IA-GM-01 | Fetch and normalize Gmail messages | Gmail adapter instantiated | 1. Call `GmailAdapter().fetch_items()` | Returns 2 `NormalizedCommunication` objects | 🔴 High |
| IA-GM-02 | Verify sender parsing | Messages fetched | 1. Inspect first message | `sender.name="John Doe"`, `sender.handle="john@example.com"` (parsed from `From` header) | 🔴 High |
| IA-GM-03 | Subject extraction | Messages fetched | 1. Inspect `subject` field | Correctly extracted from `Subject` header | 🔴 High |
| IA-GM-04 | Body content extraction | Messages fetched | 1. Inspect `content` field | Plain text body extracted from `payload.body.data` | 🔴 High |
| IA-GM-05 | Thread ID mapping | Messages fetched | 1. Inspect `thread_id` | Maps to `threadId` from Gmail API response | 🟡 Medium |
| IA-GM-06 | Handle malformed From header | Adapter with bad data | 1. Add message with missing or malformed `From` header | Gracefully falls back to "Unknown", no crash | 🟡 Medium |
| IA-GM-07 | Handle missing body | Adapter with no body | 1. Add message with empty `payload.body` | `content` is empty string or snippet, no crash | 🟡 Medium |
| IA-GM-08 | Handle missing subject | Adapter with no subject | 1. Add message with no `Subject` header | `subject` is `None` (per Pydantic model), no crash | 🟢 Low |
| IA-GM-09 | Base64 body decoding (future) | Real Gmail API response | 1. Message with Base64-encoded body | Body correctly decoded from Base64 to plain text | 🟡 Medium |
| IA-GM-10 | Large inbox pagination (future) | 1000+ messages | 1. Trigger Gmail sync | Adapter handles pagination, no timeout, all messages normalized | 🟡 Medium |

### 4.3 Adapter General Tests (All Adapters)

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| IA-GEN-01 | All adapters implement BaseAdapter | Adapters loaded | 1. Verify each adapter inherits `BaseAdapter` | All 6 adapters (gmail, slack, whatsapp, outlook, teams, jira) inherit correctly | 🟢 Low |
| IA-GEN-02 | Provider name consistency | Adapters instantiated | 1. Call `get_provider_name()` on each | Returns lowercase string matching key in `ADAPTERS` dict | 🟢 Low |
| IA-GEN-03 | NormalizedCommunication schema compliance | Items normalized | 1. Validate each item against `NormalizedCommunication` model | All required fields present, types correct | 🔴 High |
| IA-GEN-04 | Duplicate external_id handling | Same message synced twice | 1. Trigger sync twice for same integration | `db.upsert_items` updates existing rather than creating duplicate | 🔴 High |
| IA-GEN-05 | Adapter error handling | Adapter raises exception | 1. Mock adapter to raise `ConnectionError` | `sync_all_integrations` catches error, logs `SYNC_ERROR`, continues with other adapters | 🔴 High |
| IA-GEN-06 | Retry logic on adapter failure | Adapter fails transiently | 1. Configure adapter to fail on first call, succeed on second | `async_retry_with_backoff` retries up to 3 times with exponential backoff | 🟡 Medium |

---

## 5. Integration Connection Modal — UI/UX Test Cases

### 5.1 Connection Flow

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| ICM-01 | Open connection modal | On Integrations page | 1. Click "Connect" on any integration card | Modal opens with correct integration name and icon | 🔴 High |
| ICM-02 | Modal displays correct content | Modal is open | 1. Verify title, description, icon | Title says "Connect [Integration Name]", description mentions the service | 🔴 High |
| ICM-03 | Click "Authorize" starts connection | Modal is open | 1. Click "Authorize [Name]" | State changes to "connecting" with spinner, loading text shown | 🔴 High |
| ICM-04 | Successful connection | Mock OAuth succeeds | 1. Wait for mock 2s delay | State changes to "success", checkmark shown, "Done" button appears | 🔴 High |
| ICM-05 | Click "Done" closes modal | Success state shown | 1. Click "Done" | Modal closes, integration card shows "Connected" badge | 🔴 High |
| ICM-06 | Connection failure | Mock OAuth fails | 1. Simulate failure | State changes to "error", error message shown, "Try Again" button appears | 🔴 High |
| ICM-07 | Click "Try Again" retries | Error state shown | 1. Click "Try Again" | Returns to "connecting" state, retries connection | 🟡 Medium |
| ICM-08 | Close modal during connection | Modal in "connecting" state | 1. Click overlay or X button | Modal closes gracefully, connection may continue in background | 🟡 Medium |
| ICM-09 | Close modal after success | Modal in "success" state | 1. Click X button | Modal closes, integration list reflects connected state | 🟢 Low |
| ICM-10 | Keyboard accessibility | Modal open | 1. Press Escape key | Modal closes | 🟡 Medium |
| ICM-11 | Focus trap | Modal open | 1. Press Tab repeatedly | Focus cycles within modal, never escapes to background | 🟡 Medium |

### 5.2 Settings Modal

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| ISM-01 | Open settings modal for connected integration | Integration connected | 1. Click "Manage" on connected card | Settings modal opens with correct integration name, icon, and current settings | 🔴 High |
| ISM-02 | Toggle integration enabled switch | Settings modal open | 1. Click enable/disable toggle | Toggle state changes, settings object updates | 🟡 Medium |
| ISM-03 | Adjust priority threshold slider | Settings modal open | 1. Drag slider from 50 to 75 | Slider moves smoothly, displayed value updates to 75 | 🟡 Medium |
| ISM-04 | Change sync frequency | Settings modal open | 1. Select "Daily" from dropdown | Dropdown updates, settings object reflects new frequency | 🟡 Medium |
| ISM-05 | Toggle urgent notifications | Settings modal open | 1. Click notify toggle | Toggle state changes, settings object updates | 🟢 Low |
| ISM-06 | Save settings | Settings modified | 1. Click "Save Settings" | Settings saved (console log for now), modal closes, card reflects changes | 🔴 High |
| ISM-07 | Cancel without saving | Settings modified | 1. Change settings, click "Cancel" | Modal closes, original settings preserved | 🟡 Medium |
| ISM-08 | Disconnect integration | Settings modal open | 1. Click "Disconnect Integration" | Integration status changes to disconnected, card no longer shows "Connected" badge | 🔴 High |
| ISM-09 | Settings modal for disconnected integration | Integration not connected | 1. Click "Manage" on disconnected card | Modal shows default settings, no sync-related options active | 🟢 Low |
| ISM-10 | Responsive layout | Various screen sizes | 1. Resize browser window | Modal remains centered and usable on tablet and desktop | 🟡 Medium |

---

## 6. Integrations Hub — Functional Test Cases

### 6.1 Gallery View

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| IG-01 | Gallery view loads all integrations | Page loaded | 1. Open Integrations Hub | 6 cards shown (Gmail, Outlook, Slack, Teams, WhatsApp, Jira) | 🔴 High |
| IG-02 | Connected integration shows badge | Slack is connected | 1. Open Integrations Hub | Slack card shows green "Connected" badge | 🔴 High |
| IG-03 | Disconnected integration shows "Connect" button | Gmail not connected | 1. Open Integrations Hub | Gmail card shows "Connect" button | 🔴 High |
| IG-04 | Connected integration shows "Sync" and "Manage" buttons | Slack connected | 1. Open Integrations Hub | Slack card shows "Sync" and "Manage" buttons | 🔴 High |
| IG-05 | Sync button triggers sync | Slack connected | 1. Click "Sync" | Button shows spinner for ~1s, `POST /integrations/sync` called | 🔴 High |
| IG-06 | Sync button disabled during sync | Sync in progress | 1. Click "Sync" again while syncing | Button is disabled, no duplicate API calls | 🟡 Medium |

### 6.2 List View

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| IL-01 | Switch to list view | On gallery view | 1. Click list view toggle | Table layout shown with columns: Service, Account, Status, Last Sync, Actions | 🔴 High |
| IL-02 | Switch back to gallery view | On list view | 1. Click gallery view toggle | Grid layout with cards restored | 🟡 Medium |
| IL-03 | List view shows correct status | Mixed connected/disconnected | 1. View list | Connected shows "Active" with green dot, disconnected shows "Inactive" with gray dot | 🔴 High |
| IL-04 | List view actions | Integration connected | 1. Click sync/settings icons | Same behavior as gallery view | 🟡 Medium |

### 6.3 Backend API Integration Tests

| ID | Test Case | Preconditions | Steps | Expected Result | Priority |
|----|-----------|---------------|-------|-----------------|----------|
| IB-01 | List integrations | User logged in | 1. `GET /integrations` | Returns `{available: [...], connected: [...]}` | 🔴 High |
| IB-02 | Connect valid integration | User logged in | 1. `POST /integrations/slack/connect` with token | Returns 200, token encrypted in storage | 🔴 High |
| IB-03 | Connect invalid integration | User logged in | 1. `POST /integrations/invalid/connect` | Returns 404 | 🔴 High |
| IB-04 | Connect without auth | Not logged in | 1. `POST /integrations/slack/connect` | Returns 401 | 🔴 High |
| IB-05 | Trigger manual sync | Integration connected | 1. `POST /integrations/sync` | Returns `{status: "processing", task_id: "..."}` | 🔴 High |
| IB-06 | Trigger sync without connected integrations | No integrations connected | 1. `POST /integrations/sync` | Returns 200 with processing status (background worker handles empty case) | 🟡 Medium |
| IB-07 | Token encryption at rest | Integration connected | 1. Inspect `db.connected_integrations` | Token is encrypted (Fernet), not plaintext | 🔴 High |
| IB-08 | Token decryption on sync | Integration connected | 1. Trigger sync | Backend decrypts token before passing to adapter | 🔴 High |

---

## 7. Priority Scoring — Edge Cases

### 7.1 Conflicting Priority Signals

| ID | Test Case | Input | Expected Score/Tier | Explanation | Priority |
|----|-----------|-------|---------------------|-------------|----------|
| PS-01 | Urgent Slack DM + low-priority contact | `source: "slack"`, `metadata.message_type: "dm"`, contact priority: `low` | Score < 60 (medium or low) | Contact priority (0.5x) should override or significantly reduce DM boost | 🔴 High |
| PS-02 | Jira highest priority bug + high-priority contact | `source: "jira"`, `metadata.priority: "highest"`, `metadata.issue_type: "bug"`, contact: `high` | Score >= 80 (urgent) | Multiple boosts should stack but cap at 100 | 🔴 High |
| PS-03 | Regular email from high-priority contact | `source: "gmail"`, contact priority: `high` | Score elevated, explanation includes "High priority contact" | Contact multiplier (1.5x) applied | 🔴 High |
| PS-04 | Spam email from low-priority contact | `source: "gmail"`, text: "Buy pills", contact priority: `low` | Score < 30 (low) | Low contact (0.5x) reduces score despite spammy urgency keywords | 🔴 High |
| PS-05 | Empty message | `text: ""` | Score ~20 (low) | Empty text gets urgency=0, importance=0 from AI analyzer | 🟡 Medium |
| PS-06 | Message with only PII | `text: "SSN: 123-45-6789"` | Score based on sanitized text | PII redacted before AI analysis, sanitized text has no urgency signals | 🟡 Medium |
| PS-07 | Overdue deadline | `deadline: "2020-01-01"` | Deadline factor = 1.0 (max) | Overdue items get maximum deadline boost | 🟡 Medium |
| PS-08 | Far future deadline | `deadline: "2030-01-01"` | Deadline factor ≈ 0.0 | Distant deadlines contribute minimally to score | 🟢 Low |
| PS-09 | Multiple source signals (Slack urgent + DM) | `source: "slack"`, `metadata.is_urgent: true`, `metadata.message_type: "dm"` | Multipliers stack multiplicatively (1.1 * 1.2 = 1.32x) | Both DM and urgent flags applied | 🟡 Medium |
| PS-10 | Teams mention + high Jira priority | Different sources, same tenant | Each scored independently by source-specific rules | No cross-source interference | 🟢 Low |
| PS-11 | Archived item in scoring | Item is archived | Item excluded from `process_items` output | Archive filtering works before scoring | 🔴 High |
| PS-12 | Snoozed item in scoring | Item is snoozed until future | Item excluded from `process_items` output | Snooze filtering works before scoring | 🔴 High |
| PS-13 | Custom weights | `weights: {urgency: 1.0, importance: 0, sender_rank: 0, deadline: 0}` | Score = urgency only | Custom weights override defaults | 🟢 Low |
| PS-14 | Invalid deadline string | `deadline: "not-a-date"` | Deadline factor = 0.0 | Invalid dates gracefully fallback to 0 | 🟡 Medium |
| PS-15 | Z-suffix UTC timestamp | `deadline: "2026-01-01T00:00:00Z"` | Correctly parsed as UTC | `Z` replaced with `+00:00` before parsing | 🟢 Low |

### 7.2 Tier Boundary Tests

| ID | Test Case | Score | Expected Tier | Priority |
|----|-----------|-------|---------------|----------|
| PT-01 | Exact boundary — urgent | 80.0 | "urgent" | 🟡 Medium |
| PT-02 | Just below urgent | 79.99 | "high" | 🟡 Medium |
| PT-03 | Exact boundary — high | 60.0 | "high" | 🟡 Medium |
| PT-04 | Just below high | 59.99 | "medium" | 🟡 Medium |
| PT-05 | Exact boundary — medium | 30.0 | "medium" | 🟡 Medium |
| PT-06 | Just below medium | 29.99 | "low" | 🟡 Medium |
| PT-07 | Minimum score | 0.0 | "low" | 🟢 Low |
| PT-08 | Maximum score | 100.0 | "urgent" | 🟢 Low |

---

## 8. Regression Test Cases

| ID | Test Case | Area | Steps | Expected Result | Priority |
|----|-----------|------|-------|-----------------|----------|
| REG-01 | Dashboard still works after integration connect | Dashboard + Integrations | 1. Connect Slack, 2. Open Dashboard, 3. Verify feed loads | Feed loads with Slack items included | 🔴 High |
| REG-02 | Settings consent toggle still works | Settings | 1. Toggle consent on/off, 2. Verify `/dpdp/consent` called | API called correctly, state persists | 🔴 High |
| REG-03 | Tenant isolation after multiple integrations | Security | 1. Connect Gmail for Tenant A, 2. Connect Slack for Tenant B, 3. Verify feeds | Each tenant only sees their own items | 🔴 High |
| REG-04 | Rate limit banner still shows | API | 1. Trigger 429 response, 2. Verify ErrorBanner appears | Banner shows rate limit message | 🟡 Medium |
| REG-05 | Token refresh still works | Auth | 1. Let access token expire, 2. Make API call | Token refreshes automatically, request succeeds | 🔴 High |

---

## 9. Accessibility (a11y) Test Cases

| ID | Test Case | Tool/Method | Steps | Expected Result | Priority |
|----|-----------|-------------|-------|-----------------|----------|
| A11Y-01 | Modal focus trap | Manual/axe-core | 1. Open IntegrationModal, 2. Press Tab repeatedly | Focus stays within modal | 🟡 Medium |
| A11Y-02 | Modal close on Escape | Manual | 1. Open modal, 2. Press Escape | Modal closes | 🟡 Medium |
| A11Y-03 | Button labels | axe-core | 1. Run axe on Integrations page | All buttons have accessible labels or aria-labels | 🟡 Medium |
| A11Y-04 | Color contrast — tier badges | axe-core | 1. Run axe on Dashboard | Tier badge colors meet WCAG AA contrast ratio (4.5:1) | 🟡 Medium |
| A11Y-05 | Form labels in Settings modal | axe-core | 1. Run axe on Settings modal | All inputs have associated labels | 🟡 Medium |
| A11Y-06 | Slider accessibility | Manual/Screen reader | 1. Navigate to priority threshold slider with keyboard | Value is announced, arrow keys adjust value | 🟢 Low |

---

## 10. Test Execution Schedule

### Phase 1: Backend Unit Tests (Day 1)
- Execute all test cases in sections 4.1, 4.2, 4.3 (Adapter tests)
- Execute all test cases in sections 7.1, 7.2 (Priority scoring edge cases)
- Execute all test cases in section 6.3 (Backend API integration tests)

### Phase 2: Backend Functional Tests (Day 1–2)
- Execute all test cases in sections 3.1, 3.2, 3.3 (Dashboard Quick Actions)
- Execute all test cases in section 8 (Regression tests)

### Phase 3: Frontend UI/UX Tests (Day 2)
- Execute all test cases in sections 5.1, 5.2 (Modal tests)
- Execute all test cases in sections 6.1, 6.2 (Integrations Hub views)

### Phase 4: Accessibility & Polish (Day 3)
- Execute all test cases in section 9 (a11y)
- Document any visual/UX inconsistencies

---

## 11. Entry & Exit Criteria

### Entry Criteria
- [ ] Backend server starts successfully with all required env vars
- [ ] Frontend builds without errors (`npm run build` succeeds)
- [ ] All existing unit tests pass (`test_security.py`, `test_scalability.py`, `test_priority_service.py`)
- [ ] Database is in a clean state (or seeded with known test data)

### Exit Criteria
- [ ] All 🔴 High priority test cases pass
- [ ] ≥ 80% of 🟡 Medium priority test cases pass
- [ ] No 🔴 High priority defects remain open
- [ ] All 🔴 High priority accessibility issues resolved
- [ ] Test results documented in `/home/team/shared/priority-flow/testing/TEST_RESULTS.md`

---

## 12. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Mock adapters don't reflect real API behavior | High | Medium | Document assumptions; plan real adapter tests with sandbox tokens |
| Frontend tests require running backend | Medium | High | Use TestClient for backend; mock API responses for frontend unit tests |
| Priority scoring is subjective | Medium | Medium | Define expected tiers for known inputs; test boundary conditions rigorously |
| Race conditions in background sync | Medium | Low | Add sync locking tests; test concurrent sync triggers |
| Browser compatibility issues | Low | Medium | Test on Chrome, Firefox, Safari; use Playwright for cross-browser |

---

## 13. Appendix: Test Data

### Sample Items for Priority Scoring Tests
```python
TEST_ITEMS = [
    {
        "id": "test-urgent-slack",
        "text": "URGENT: server is down ASAP!",
        "source": "Slack",
        "metadata": {"is_urgent": True, "message_type": "dm"}
    },
    {
        "id": "test-regular-email",
        "text": "Just a regular update.",
        "source": "Gmail",
        "metadata": {}
    },
    {
        "id": "test-jira-bug",
        "text": "Bug: Auth failing",
        "source": "Jira",
        "metadata": {"issue_type": "bug", "priority": "highest"}
    },
    {
        "id": "test-boss-email",
        "text": "Meeting at 2pm",
        "source": "Gmail",
        "sender": {"handle": "boss@acme.com"},
        "metadata": {}
    },
    {
        "id": "test-spam-email",
        "text": "Buy more pills",
        "source": "Gmail",
        "sender": {"handle": "spammer@ads.com"},
        "metadata": {}
    }
]
```

### Sample Contact Priorities
```python
CONTACT_PRIORITIES = {
    "gmail": {
        "boss@acme.com": "high",
        "spammer@ads.com": "low"
    }
}
```

---

*Test plan generated by Software Tester (agent-software-tester) for PriorityFlow team.*
