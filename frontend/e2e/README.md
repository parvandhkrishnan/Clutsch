# PriorityFlow E2E (Playwright)

Covers the core user flow: **login → dashboard loads → toggle consent in Settings → verify persistence across reload → logout**.

## Setup
```bash
cd frontend
npm install
npm i -D @playwright/test
npx playwright install chromium
```

## Run
Start a healthy backend (see backend README) and the frontend, then:
```bash
# terminal 1
npm run dev            # serves on http://localhost:5173
# terminal 2
BASE_URL=http://localhost:5173 \
  E2E_USER=john E2E_PASS=password \
  npx playwright test
```

## Notes
- The consent-persistence assertion depends on the Settings save endpoint working. Item-seeded assertions depend on `POST /items`, which is currently affected by a backend `NameError` (see `/home/team/shared/priority-flow/testing/EXECUTION_REPORT.md`, BUG-001) — re-run once fixed.
- Selectors are resilient (role/placeholder based) to tolerate the in-progress visual overhaul.
