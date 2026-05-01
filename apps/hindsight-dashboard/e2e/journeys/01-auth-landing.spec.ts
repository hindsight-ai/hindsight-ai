import { test, expect } from '@playwright/test';
import { asUser, asGuest } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail } from '../helpers/runId';

/**
 * Journey 1 — Auth + landing. (RFC v3, umbrella #96)
 *
 * The wiring-proof test. Validates that:
 * 1. Playwright can start the backend + frontend via `webServer` config
 * 2. The auth helper successfully injects `x-auth-request-*` headers
 * 3. The backend resolves the headers (DEV_MODE=false) and creates/loads the user
 * 4. `provisionUser` pre-approves the user's beta access via the admin endpoint
 *    so the dashboard renders instead of redirecting to /beta-access/request
 * 5. The frontend fetches `/user-info` and renders the user identity
 * 6. The hard-reload after `setExtraHTTPHeaders` correctly resets frontend state
 *
 * Tagged @smoke — runs on every PR.
 */

test.describe('Journey 1 — Auth + landing @smoke', () => {
  test('an authenticated user lands on the dashboard and sees their identity', async ({ page }) => {
    // No displayName is passed — provisionUser/asUser default it to the email.
    // This avoids `uq_users_external_subject` collisions when multiple parallel
    // workers happen to share a display name (the backend stores display_name
    // as external_subject, which has a UNIQUE constraint).
    const email = temail('alice');
    await provisionUser(page, email);
    await asUser(page, email);

    // After `asUser` we are on `/`. The dashboard fetches `/user-info` and
    // renders the email somewhere in the chrome (account button, sidebar, etc.).
    await expect(page.getByText(email, { exact: false })).toBeVisible({ timeout: 15_000 });
  });

  test('a fresh user is auto-provisioned by the backend on first request', async ({ page }) => {
    const email = temail('newuser');
    await provisionUser(page, email);
    await asUser(page, email);

    await expect(page.getByText(email, { exact: false })).toBeVisible({ timeout: 15_000 });
  });

  test('identity swap mid-test produces fresh frontend state', async ({ page }) => {
    // Round-2 F1 regression test: the auth helper must hard-reload to drain
    // React Query / localStorage, otherwise the post-swap page renders the
    // pre-swap user's data while subsequent API calls carry the new identity.
    const aliceEmail = temail('alice-swap');
    const bobEmail = temail('bob-swap');

    await provisionUser(page, aliceEmail);
    await provisionUser(page, bobEmail);

    await asUser(page, aliceEmail);
    await expect(page.getByText(aliceEmail, { exact: false })).toBeVisible({ timeout: 15_000 });

    await asUser(page, bobEmail);
    await expect(page.getByText(bobEmail, { exact: false })).toBeVisible({ timeout: 15_000 });
    // Alice's email should NOT still be visible somewhere on the page.
    await expect(page.getByText(aliceEmail, { exact: true })).toHaveCount(0);
  });

  test('asGuest clears auth and the page no longer shows the previous identity', async ({ page }) => {
    const email = temail('logout-test');
    await provisionUser(page, email);
    await asUser(page, email);
    await expect(page.getByText(email, { exact: false })).toBeVisible({ timeout: 15_000 });

    await asGuest(page);
    // The landing page may render a sign-in CTA or guest banner; we just assert
    // the previous user's email isn't displayed anymore.
    await expect(page.getByText(email, { exact: true })).toHaveCount(0);
  });
});
