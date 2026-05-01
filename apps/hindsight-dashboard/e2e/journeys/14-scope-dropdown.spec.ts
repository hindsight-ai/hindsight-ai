import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail, tname, runId } from '../helpers/runId';

/**
 * Journey 14 — Scope dropdown + persistence. (RFC v3, umbrella #96, issue #104)
 *
 * Validates:
 *   1. The scope dropdown's UI selection translates into the correct
 *      `X-Active-Scope` (and `X-Organization-Id`) headers on subsequent
 *      API requests
 *   2. The scope selection persists across page reload (localStorage seed)
 *
 * Why this is smoke-tier: a regression in `scopeProvider` (#68) would
 * silently make every API call carry the wrong scope — backend checks
 * still pass (the user IS authenticated), but data leaks across scope
 * boundaries. Only an E2E test catches this end-to-end.
 *
 * Tagged @smoke.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 14 — Scope dropdown + persistence @smoke', () => {
  test('localStorage scope seed produces correct X-Active-Scope on API requests', async ({
    page,
    request,
  }) => {
    const email = temail('scope-user');
    await provisionUser(page, email);
    const headers = { 'x-auth-request-email': email, 'x-auth-request-user': email };

    // Seed: create one organization the user owns so we can test the org scope path.
    const orgRes = await request.post(`${BACKEND}/organizations/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: { name: tname('scope-org'), slug: `scope-org-${runId}` },
    });
    expect(orgRes.ok()).toBe(true);
    const org = await orgRes.json();

    await asUser(page, email);

    // ── Test 1: personal scope ────────────────────────────────────────────────
    // Set localStorage directly (simulates the user having previously selected
    // 'personal' from the dropdown — the scopeProvider reads this on init).
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('selectedScope', 'personal');
      localStorage.removeItem('selectedOrganizationId');
    });
    await page.reload();

    // Capture request headers from any /memory-blocks/ API call.
    const personalReqPromise = page.waitForRequest(
      (req) => req.url().includes('/memory-blocks/') || req.url().includes('/api/memory-blocks/'),
      { timeout: 15_000 },
    );
    await page.goto('/memory-blocks');
    const personalReq = await personalReqPromise;
    const personalHeaders = personalReq.headers();
    expect(personalHeaders['x-active-scope']).toBe('personal');
    expect(personalHeaders['x-organization-id']).toBeUndefined();

    // ── Test 2: organization scope persists across reload ─────────────────────
    await page.evaluate((orgId) => {
      localStorage.setItem('selectedScope', 'organization');
      localStorage.setItem('selectedOrganizationId', orgId);
    }, org.id);
    await page.reload();

    const orgReqPromise = page.waitForRequest(
      (req) => req.url().includes('/memory-blocks/') || req.url().includes('/api/memory-blocks/'),
      { timeout: 15_000 },
    );
    await page.goto('/memory-blocks');
    const orgReq = await orgReqPromise;
    const orgHeaders = orgReq.headers();
    expect(orgHeaders['x-active-scope']).toBe('organization');
    expect(orgHeaders['x-organization-id']).toBe(org.id);

    // ── Test 3: persistence — localStorage is read across full reload ────────
    // Already verified above (reload happened before each navigate). Add an
    // explicit assertion that localStorage values survive an explicit reload.
    await page.reload();
    const storedScope = await page.evaluate(() => localStorage.getItem('selectedScope'));
    const storedOrg = await page.evaluate(() => localStorage.getItem('selectedOrganizationId'));
    expect(storedScope).toBe('organization');
    expect(storedOrg).toBe(org.id);

    // ── Cleanup ───────────────────────────────────────────────────────────────
    await request.delete(`${BACKEND}/organizations/${org.id}`, { headers });
  });
});
