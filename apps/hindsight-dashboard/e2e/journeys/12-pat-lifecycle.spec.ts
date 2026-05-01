import { test, expect } from '@playwright/test';
import { asPAT, asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail, tname } from '../helpers/runId';

/**
 * Journey 12 — PAT lifecycle. (RFC v3, umbrella #96, issue #103)
 *
 * Tests:
 *   - PAT appears in the user's token list after creation
 *   - PAT works for authenticated requests (sanity)
 *   - Revocation via UI (Revoke button)
 *   - **Revocation actually denies subsequent requests** (the value of an E2E
 *     test — backend tests trust the revoke endpoint, this tests the
 *     full chain)
 *
 * **Scope adaptation:** the PAT is created via API (POST /users/me/tokens)
 * rather than through the create form on /tokens. The create-form flow has
 * its own UI surface (name input, scopes, expiry, one-time-secret render)
 * that's worth a dedicated future test; this journey focuses on the
 * lifecycle (list, revoke, post-revoke 401) which is the smoke value.
 *
 * Tagged @smoke.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 12 — PAT lifecycle @smoke', () => {
  test('list, revoke, then verify revocation denies subsequent requests', async ({ page, request }) => {
    const email = temail('pat-lifecycle');
    await provisionUser(page, email);
    const headers = { 'x-auth-request-email': email, 'x-auth-request-user': email };

    // ── 1. Create PAT via API ─────────────────────────────────────────────────
    const tokenRes = await request.post(`${BACKEND}/users/me/tokens`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: { name: tname('lifecycle-pat'), scopes: ['read', 'write'] },
    });
    expect(tokenRes.ok(), `PAT create failed: ${await tokenRes.text()}`).toBe(true);
    const tokenData = await tokenRes.json();
    const patString: string = tokenData.token;
    const patId: string = tokenData.id;
    expect(patString).toBeTruthy();
    expect(patId).toBeTruthy();

    // ── 2. Sanity: PAT works for authenticated requests ───────────────────────
    await asPAT(page, patString);
    const userInfoBefore = await page.request.get(`${BACKEND}/user-info`);
    expect(userInfoBefore.ok(), 'PAT should authenticate before revocation').toBe(true);
    const infoBefore = await userInfoBefore.json();
    expect(infoBefore.email).toBe(email);

    // ── 3. As the user, navigate to /tokens and verify the PAT in list ────────
    await asUser(page, email);
    await page.goto('/tokens');
    await expect(page.getByText(tokenData.name, { exact: true })).toBeVisible({ timeout: 10_000 });

    // ── 4. Revoke via UI ──────────────────────────────────────────────────────
    // Each token row has a "Revoke" button (TokenManagement.tsx:172).
    const tokenRow = page.locator('tr,div,li').filter({ hasText: tokenData.name }).first();
    await tokenRow.getByRole('button', { name: /^revoke$/i }).first().click();

    // The button on the row should disable after revocation (`disabled={t.status !== 'active'}`).
    // Verify via API.
    const listRes = await request.get(`${BACKEND}/users/me/tokens`, { headers });
    const tokens: Array<{ id: string; status: string }> = await listRes.json();
    const ours = tokens.find((t) => t.id === patId);
    expect(ours?.status, 'token should now be revoked').not.toBe('active');

    // ── 5. Critical: verify the revoked PAT is denied ─────────────────────────
    await asPAT(page, patString);
    const userInfoAfter = await page.request.get(`${BACKEND}/user-info`);
    // Backend may return 401 OR 200 with `authenticated: false`. Either is OK
    // as long as the user is no longer authenticated as `email`.
    if (userInfoAfter.ok()) {
      const infoAfter = await userInfoAfter.json();
      expect(infoAfter.authenticated, 'revoked PAT must not authenticate').not.toBe(true);
    } else {
      expect(userInfoAfter.status(), 'revoked PAT should return 401').toBe(401);
    }
  });
});
