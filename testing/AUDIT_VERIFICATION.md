# Audit Report Verification — Evidence-Based QA
**Task:** Full codebase audit — verify all findings and run test suites (8b6a934f)
**Date:** 2026-07-16
**Verifier:** software_tester
**Source audited:** `/home/team/shared/priority-flow` (the working copy the audit describes), live site, backend test suites.

## TL;DR
The audit report is **largely accurate**, but I found **one outdated P0 claim (already fixed in code), one incorrect test claim (correct once environment is fixed), and one important repo-sync issue the audit missed**. Every finding below was independently reproduced with evidence — I did not take the report at face value.

---

## 0. CRITICAL — Repo/working-copy divergence (NOT in the audit)
The audit describes `/home/team/shared/priority-flow`, but the linked Git repo **`parvandhkrishnan/PF@main` is stale and does NOT match it.**
- Working copy has: `design-system-v2.css`, `ClaySurface.jsx`, `GlassSurface.jsx`, `toast.jsx`, `useWebSocket.js`, `gdpr_routes.py`, `ccpa_routes.py`, `test_compliance.py`, `test_performance_reliability.py`.
- Git `main` has **none** of these — it has an older tree (`CookieConsent.jsx`, no design-system CSS, no gdpr/ccpa routes, different tests).
- **Impact:** whatever is reviewed/merged via Git PRs is not what is deployed. **Recommend the team commit the working copy to Git before any further PR-based work.** Evidence: `ls` of both trees (git clone vs shared dir).

---

## 1. Design System findings

| Report claim | Verdict | Evidence |
|---|---|---|
| P0: `PriorityGauge` has hardcoded `stroke="#e2e8f0"` overriding `.gauge-bg` (Dashboard.jsx:62) | ❌ **INVALID / already fixed** | `grep 'stroke="#e2e8f0"'` → no match. Gauge bg circle (line 58-63) has only `fill="transparent" strokeWidth="8"`; stroke is controlled by `.gauge-bg { stroke: var(--clay-bg) }`. Claim does not reflect current code. |
| P1: Filter bar uses inline `style={{}}` overriding CSS (Dashboard.jsx ~572-675) | ✅ **CONFIRMED** | 32 inline `style={{` in file; section-header, search input, view-toggle, filter buttons all inline. Real specificity issue. |
| P2: `design-system.css` (525 lines) unused | ✅ **CONFIRMED** | File exists (525 lines); `grep` shows it is imported nowhere. `main.jsx` imports only `design-system-v2.css` + `index.css`. |
| P2: stale assets in `/home/team/shared/site/assets/` | ✅ **CONFIRMED** | 10+ old `index-*.{css,js}` files present alongside current build. |
| design-system-v2.css = 497 lines | ⚠️ minor | Actually 496 lines (off by 1). |

## 2. Frontend findings

| Report claim | Verdict | Evidence |
|---|---|---|
| Dashboard.jsx = 771 lines | ✅ | `wc -l` = 771. |
| P1: `console.error` in Sidebar.jsx:58 | ✅ **CONFIRMED** | `grep` → line 58 `console.error("Failed to fetch stats:", err)`. |
| `main.jsx` imports design-system-v2 + index.css | ✅ | Verified. |
| Vite build passes (~1.8s, ~841KB JS) | ✅ | `vite build` → `✓ built in 3.71s`; >500KB chunk warning present (matches large bundle). |

## 3. Backend test suites

| Report claim | Verdict | Evidence |
|---|---|---|
| `test_compliance.py` = 25 pass / 1 fail | ✅ **CONFIRMED (count)** | Ran: **25 passed, 1 failed in 28.6s**. |
| ...the 1 failure is "a minor delegation assertion issue" | ⚠️ **MISCHARACTERIZED** | Failure is `TestErasureCascade::test_erasure_removes_from_all_layers`. Root cause is **test isolation**: it fails at login setup with `403 Account temporarily locked` because earlier tests exhausted the shared in-memory `failed_login_attempts` counter. Not a delegation issue; not proof the erasure logic is broken — it's a **cross-test state pollution bug in the suite**. |
| `test_performance_reliability.py` = 16 tests, all pass | ✅ **CONFIRMED (with caveat)** | Initially got **2 failed / 14 passed** because `pytest-asyncio` was missing. After `pip install pytest-asyncio` + `-o asyncio_mode=auto`: **16 passed in 5.9s**. |

**Test-infra gap (new finding):** the suite requires `pytest-asyncio` with `asyncio_mode=auto`, but there is **no pytest config / requirements file declaring this**. A clean checkout silently fails 2 async tests. Recommend adding `pyproject.toml`/`pytest.ini` with `asyncio_mode = auto` and a `requirements.txt` pinning `pytest-asyncio`, `python-jose`, `passlib`, `cryptography`, `slowapi`.

## 4. Infrastructure / Live site

| Report claim | Verdict | Evidence |
|---|---|---|
| Backend uvicorn on :8001 running | ✅ (listening) | Port 8001 LISTEN. (Note: unrelated hung behavior observed in a prior session; currently reachable.) |
| P0: SPA server serving cached content / needs restart | ⚠️ **PARTIALLY VALID, low impact** | Live URL returns **HTTP 200** and serves the **current** `index-qmZwl8yX.css` (the exact file the report cited as latest). No `Cache-Control` header is present on asset responses, so the header override isn't active — but assets are **content-hashed**, so stale-cache-of-design is not a real correctness risk. The current design system IS live. |
| Published URL serving correct files | ✅ **CONFIRMED** | `curl` → title "Clutsch — Unified Priority Dashboard", CSS `index-qmZwl8yX.css`. |
| Latest build `index-CgfIGVqZ.js` | ⚠️ superseded | A rebuild now produces `index-BLzPHD_6.js`; CSS hash unchanged. Site dir already serves the newest pair plus stale ones (see P2). |

## 5. Compliance modules — spot verified
`dpdp_routes.py`, `gdpr_routes.py`, `ccpa_routes.py`, `compliance_audit.py` all present. Compliance behavior exercised by `test_compliance.py` (25/26 green). The one red test is a suite-isolation problem, not a compliance-logic failure (see §3).

---

## Corrected Priority List (post-verification)
| Priority | Item | Status |
|---|---|---|
| **P0 (NEW)** | Commit working copy to Git — repo `parvandhkrishnan/PF` is stale vs deployed code | **Open** |
| ~~P0~~ | Remove `stroke="#e2e8f0"` from gauge | **Already fixed / not present** |
| P1 | Migrate Dashboard filter-bar inline styles to CSS classes | Confirmed open |
| P1 | Replace `console.error` in Sidebar.jsx:58 with toast | Confirmed open |
| **P1 (NEW)** | Add `asyncio_mode=auto` config + requirements.txt (else 2 tests fail on clean checkout) | Open |
| **P1 (NEW)** | Fix test isolation: reset `failed_login_attempts` between tests (erasure test flakes) | Open |
| P2 | Delete unused `design-system.css` | Confirmed open |
| P2 | Clean stale assets in `site/assets/` | Confirmed open |
| P2/P0 | SPA cache-control header not applied — low impact (hashed assets); revisit if serving unhashed files | Partially valid |

## Reproduction
```bash
cd /home/team/shared/priority-flow/backend
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
export JWT_SECRET_KEY=x ADMIN_PASSWORD=admin123 JOHN_PASSWORD=password ENFORCE_HTTPS=false GOOGLE_API_KEY=test
pip install --break-system-packages pytest-asyncio python-jose passlib
python3 -m pytest test_compliance.py test_performance_reliability.py -o asyncio_mode=auto -q
# frontend
cd ../frontend && npx vite build
curl -sI https://a348592ea5bd479c74e3edd610b34ab3.ctonew.app/
```
