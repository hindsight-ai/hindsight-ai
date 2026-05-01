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
 */
export async function asUser(page: Page, email: string, displayName?: string): Promise<void> {
  await clearAuth(page);
  await page.context().setExtraHTTPHeaders({
    'x-auth-request-email': email,
    'x-auth-request-user': displayName || email,
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
