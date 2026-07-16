// Playwright E2E: core user flow for PriorityFlow
// Flow: login -> dashboard loads -> settings toggle consent -> verify persistence -> logout
//
// Run:
//   cd frontend
//   npm i -D @playwright/test && npx playwright install chromium
//   BASE_URL=http://localhost:5173 npx playwright test
//
// Requires a running frontend (vite dev/preview) and a healthy backend the
// frontend points at (VITE_API_URL). Seed account: john / password.

import { test, expect } from '@playwright/test';

const USER = process.env.E2E_USER || 'john';
const PASS = process.env.E2E_PASS || 'password';

test.describe('Core user flow', () => {
  test('login, dashboard, toggle consent, persist, logout', async ({ page }) => {
    // 1. Login with a test account (Standard tab)
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /PriorityFlow/i })).toBeVisible();
    await page.getByPlaceholder('e.g. john').fill(USER);
    await page.getByPlaceholder('••••••••').fill(PASS);
    await page.getByRole('button', { name: /Sign In/i }).click();

    // 2. Verify dashboard loads
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
    // Token must be persisted for a successful auth
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token, 'auth token should be stored after login').toBeTruthy();
    // Dashboard should render its main region (list/feed container)
    await expect(page.locator('main, .dashboard, [class*="dashboard"]').first()).toBeVisible();

    // 3. Navigate to settings and toggle a consent switch
    await page.goto('/settings');
    const consent = page.locator(
      'input[type="checkbox"], [role="switch"]'
    ).first();
    await expect(consent).toBeVisible({ timeout: 10000 });
    const before = await consent.isChecked().catch(() => null);
    await consent.click();
    // Save if there is an explicit save action
    const saveBtn = page.getByRole('button', { name: /save|update|apply/i }).first();
    if (await saveBtn.count()) {
      await saveBtn.click().catch(() => {});
    }

    // 4. Verify change persists across a reload (re-fetch from backend)
    await page.reload();
    await expect(consent).toBeVisible({ timeout: 10000 });
    if (before !== null) {
      const after = await consent.isChecked();
      expect(after, 'consent toggle should persist after reload').not.toBe(before);
    }

    // 5. Logout
    const logout = page.getByRole('button', { name: /log ?out|sign ?out/i })
      .or(page.getByText(/log ?out|sign ?out/i)).first();
    await logout.click();
    await expect(page).toHaveURL(/\/login|\/$/, { timeout: 10000 });
    const clearedToken = await page.evaluate(() => localStorage.getItem('token'));
    expect(clearedToken, 'token should be cleared after logout').toBeFalsy();
  });
});
