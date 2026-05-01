import type { Page } from '@playwright/test';

/**
 * Auth helpers for E2E.
 *
 * The backend resolves identity via oauth2-proxy headers when DEV_MODE=false:
 * `x-auth-request-email` + `x-auth-request-user`. Same code path the 875 backend
 * tests already exercise. Tests that need a different identity per request set
 * the headers via `setExtraHTTPHeaders`.
 *
 * Round-2 review (RFC v3 F1, F2) flagged two correctness traps in the naive
 * implementation:
 *   F1 - mid-test identity swap doesn't clear React Query cache / localStorage
 *        without a hard reload, so the frontend renders stale data while the
 *        backend sees the new headers.
 *   F2 - `setExtraHTTPHeaders` MERGES headers; calling `asUser` after `asPAT`
 *        leaves the dangling `Authorization` header, which the backend prefers
 *        over `x-auth-request-*`.
 *
 * Both helpers below address those: they fully replace the header dictionary,
 * clear cookies + storage, and hard-reload to reset the frontend.
 */

const PROBE_PAGE = '/'; // navigated to after each identity swap to drain React Query / localStorage

/**
 * Reset all auth-related state on the browser context:
 * - Replace extra HTTP headers with an empty dict (clears x-auth-request-*, Authorization)
 * - Clear all cookies (drops oauth2-proxy session, CSRF tokens)
 * - Clear localStorage + sessionStorage (drops scope provider state, cached identity)
 */
async function clearAuth(page: Page): Promise<void> {
  await page.context().setExtraHTTPHeaders({});
  await page.context().clearCookies();
  // localStorage clear must happen on a real page; if we navigate first we lose the chance.
  // Strategy: try-clear if there's already a page loaded; otherwise no-op (next goto resets it).
  try {
    await page.evaluate(() => {
      try {
        localStorage.clear();
        sessionStorage.clear();
      } catch {
        // about:blank or restricted page — storage isn't accessible, that's fine.
      }
    });
  } catch {
    // No page loaded yet (about:blank) — no storage to clear.
  }
}

/**
 * Authenticate the browser as a regular user via oauth2-proxy headers.
 * Hard-navigates to `/` so the frontend re-fetches user state under the new identity.
 *
 * Also seeds `localStorage.selectedScope='personal'` by default so the
 * dashboard's first API call carries a scope filter — without this, the
 * `scopeProvider` returns `scope=undefined`, the backend filters differently
 * than journey tests expect, and data-display assertions see empty results.
 * Tests that need org/public scope (or want to test the unset path) can
 * call `page.evaluate(() => localStorage.setItem('selectedScope', '...'))`
 * + `page.reload()` afterwards (e.g. journey 14 does this explicitly).
 */
export async function asUser(page: Page, email: string, displayName?: string): Promise<void> {
  await clearAuth(page);
  await page.context().setExtraHTTPHeaders({
    'x-auth-request-email': email,
    'x-auth-request-user': displayName || email,
  });
  // Seed localStorage scope BEFORE navigation so the first data fetch has it.
  await page.goto('about:blank');
  await page.evaluate(() => {
    try {
      localStorage.setItem('selectedScope', 'personal');
      localStorage.removeItem('selectedOrganizationId');
    } catch {}
  });
  await page.goto(PROBE_PAGE);
}

/**
 * Authenticate the browser as the bearer of a PAT.
 * Used for cross-org isolation tests where we want to exercise the PAT scope-narrowing path
 * specifically rather than the oauth2-proxy header path.
 */
export async function asPAT(page: Page, patToken: string): Promise<void> {
  await clearAuth(page);
  await page.context().setExtraHTTPHeaders({
    authorization: `Bearer ${patToken}`,
  });
  await page.goto(PROBE_PAGE);
}

/**
 * Drop all auth state, returning the browser to a guest/anonymous state.
 * Useful between tests that swap identities multiple times.
 */
export async function asGuest(page: Page): Promise<void> {
  await clearAuth(page);
  await page.goto(PROBE_PAGE);
}

/**
 * Construct scoped HTTP headers for direct API calls (Playwright's `request`
 * fixture or `page.request`).
 *
 * The backend's `enforce_write_scope_metadata` middleware (see
 * `core/api/middleware/scope.py`) returns 400 `scope_required` for any
 * POST/PUT/PATCH/DELETE on `/agents`, `/keywords`, `/memory-blocks`,
 * `/consolidation*` paths unless the request includes either an
 * `X-Active-Scope` header or a `?scope=...` query param. This helper
 * bundles the scope header alongside the auth headers so journey tests
 * don't have to remember it for every write.
 *
 * For `scope='organization'`, `orgId` is required and produces an
 * additional `X-Organization-Id` header.
 */
export function authedHeaders(
  email: string,
  scope: 'personal' | 'organization' | 'public' = 'personal',
  orgId?: string,
): Record<string, string> {
  const h: Record<string, string> = {
    'x-auth-request-email': email,
    'x-auth-request-user': email,
    'x-active-scope': scope,
  };
  if (scope === 'organization') {
    if (!orgId) throw new Error("authedHeaders: 'organization' scope requires orgId");
    h['x-organization-id'] = orgId;
  }
  return h;
}
