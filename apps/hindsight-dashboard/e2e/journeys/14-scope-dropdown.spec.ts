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

    // NOTE on init-script ordering: `asUser` registers a `page.addInitScript`
    // that defaults `localStorage.selectedScope='personal'` on every page load
    // (so journeys that don't care about scope get a sane default). To test a
    // DIFFERENT scope, we must register ANOTHER addInitScript AFTER asUser —
    // Playwright runs init scripts in installation order, so the last one
    // wins. Calling `page.evaluate` + `page.reload` does NOT work, because
    // `asUser`'s init script runs on every reload and overwrites our value.

    // ── Test 1: personal scope ────────────────────────────────────────────────
    // asUser already seeds 'personal'; nothing extra to do.
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
    // Install a SECOND init script that runs after asUser's, overriding the
    // personal default with organization scope.
    await page.addInitScript((orgId) => {
      localStorage.setItem('selectedScope', 'organization');
      localStorage.setItem('selectedOrganizationId', orgId);
    }, org.id);

    // OrganizationContext initializes `isPersonalMode=true` and only flips to
    // `organization` after `refreshOrganizations` → `switchToOrganization`
    // resolves (one /organizations + one /organizations/{id}/members round
    // trip). Attach the capture handler BEFORE reload so we see EVERY
    // /memory-blocks request — both the initial mount-time fetch (personal)
    // and the post-scope-switch refetch (organization).
    const memoryBlockRequests: Array<{ scope?: string; orgId?: string }> = [];
    const captureHandler = (req: import('@playwright/test').Request): void => {
      if (req.url().includes('memory-blocks')) {
        const h = req.headers();
        memoryBlockRequests.push({
          scope: h['x-active-scope'],
          orgId: h['x-organization-id'],
        });
      }
    };
    page.on('request', captureHandler);
    await page.reload();

    // Wait for at least one /memory-blocks request with org scope. If the
    // membership check fails, OrganizationContext falls back to personal
    // — historically that bug existed in OrganizationContext.tsx where the
    // initial mount (with `authLoading=true`) entered the unauthenticated
    // branch and wiped the seeded localStorage. The fix lives in that file.
    await expect
      .poll(() => memoryBlockRequests.find((r) => r.scope === 'organization'), {
        timeout: 15_000,
        message: `expected /memory-blocks request with x-active-scope=organization; saw: ${JSON.stringify(memoryBlockRequests)}`,
      })
      .toBeTruthy();
    page.off('request', captureHandler);

    const orgReq = memoryBlockRequests.find((r) => r.scope === 'organization')!;
    expect(orgReq.scope).toBe('organization');
    expect(orgReq.orgId).toBe(org.id);

    // ── Test 3: persistence — localStorage is read across full reload ────────
    await page.reload();
    const storedScope = await page.evaluate(() => localStorage.getItem('selectedScope'));
    const storedOrg = await page.evaluate(() => localStorage.getItem('selectedOrganizationId'));
    expect(storedScope).toBe('organization');
    expect(storedOrg).toBe(org.id);

    // ── Cleanup ───────────────────────────────────────────────────────────────
    await request.delete(`${BACKEND}/organizations/${org.id}`, { headers });
  });
});
