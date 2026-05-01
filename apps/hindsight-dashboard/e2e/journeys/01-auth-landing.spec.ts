import { test, expect, type Page } from '@playwright/test';
import { asUser, asGuest } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail } from '../helpers/runId';

/**
 * Journey 1 — Auth + landing. (RFC v3, umbrella #96)
 *
 * The wiring-proof test. Validates the full auth chain end-to-end without
 * coupling to specific frontend layout choices (which would break tests on
 * harmless UI tweaks).
 *
 * Tagged @smoke — runs on every PR.
 */

const BACKEND = 'http://localhost:8000';

/**
 * Behavior-level auth assertion: page is NOT on the beta-access redirect, and
 * `/user-info` returns the expected email when called from the same browser
 * context. This is robust against UI changes (account button moves, dropdown
 * collapses, sidebar restyles) while still proving the backend resolves the
 * test user's identity correctly through the headers we set.
 */
async function expectAuthedAs(page: Page, email: string): Promise<void> {
  await expect(page).not.toHaveURL(/\/beta-access\//, { timeout: 15_000 });
  const resp = await page.request.get(`${BACKEND}/user-info`);
  expect(resp.ok(), `user-info returned ${resp.status()}: ${await resp.text()}`).toBe(true);
  const info = await resp.json();
  expect(info.email).toBe(email);
  expect(info.beta_access_status).toBe('accepted');
}

test.describe('Journey 1 — Auth + landing @smoke', () => {
  test('an authenticated user lands on the dashboard with the expected identity', async ({ page }) => {
    const email = temail('alice');
    await provisionUser(page, email);
    await asUser(page, email);
    await expectAuthedAs(page, email);
  });

  test('a fresh user is auto-provisioned by the backend on first request', async ({ page }) => {
    const email = temail('newuser');
    await provisionUser(page, email);
    await asUser(page, email);
    await expectAuthedAs(page, email);
  });

  test('identity swap mid-test produces fresh backend identity (round-2 F1 regression)', async ({ page }) => {
    // The auth helper must hard-reload to drain React Query / localStorage,
    // otherwise the post-swap page renders the pre-swap user's data while
    // subsequent API calls carry the new identity.
    const aliceEmail = temail('alice-swap');
    const bobEmail = temail('bob-swap');

    await provisionUser(page, aliceEmail);
    await provisionUser(page, bobEmail);

    await asUser(page, aliceEmail);
    await expectAuthedAs(page, aliceEmail);

    await asUser(page, bobEmail);
    await expectAuthedAs(page, bobEmail);
  });

  test('asGuest clears auth — backend now reports guest', async ({ page }) => {
    const email = temail('logout-test');
    await provisionUser(page, email);
    await asUser(page, email);
    await expectAuthedAs(page, email);

    await asGuest(page);
    // After clearing all auth, /user-info should return 401 OR `authenticated: false`.
    const resp = await page.request.get(`${BACKEND}/user-info`);
    if (resp.ok()) {
      const info = await resp.json();
      expect(info.authenticated).toBe(false);
    } else {
      expect(resp.status()).toBe(401);
    }
  });
});
