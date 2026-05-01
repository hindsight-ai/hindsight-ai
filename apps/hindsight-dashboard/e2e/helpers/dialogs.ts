import { expect, type Page } from '@playwright/test';

/**
 * Native browser dialog helpers.
 *
 * Nine components in the dashboard use `window.confirm()` for delete
 * confirmation (e.g. MemoryBlocksPage's archive + permanent-delete).
 * Playwright doesn't auto-handle dialogs — without a listener the test
 * hangs until timeout when a `confirm()` fires. Register `autoAcceptConfirm`
 * in `test.beforeEach` for any test that triggers a delete-style flow.
 */

/**
 * Auto-accept all native dialogs (confirm/alert/prompt) on this page.
 * Called once at the top of a test (typically in beforeEach).
 *
 * Caveat: this is a fire-and-forget listener. If a test needs to verify
 * a specific dialog was shown, use `expectConfirm(page, ...)` below
 * INSTEAD of (not in addition to) this auto-accept.
 */
export function autoAcceptConfirm(page: Page): void {
  page.on('dialog', (d) => {
    void d.accept();
  });
}

/**
 * Strict variant: assert that the next dialog fired is a `confirm`
 * with a message matching `messagePattern`, then accept it.
 *
 * Use this when a regression like "delete button skipped its confirm popup"
 * would be silently green with `autoAcceptConfirm`.
 *
 * Pattern:
 *   const dialog = expectConfirm(page, /Are you sure/);
 *   await page.getByRole('button', { name: 'Delete' }).click();
 *   await dialog;
 *
 * Note: this captures EXACTLY one dialog. If `alert()` fires before
 * `confirm()` from the same click, the captured dialog will be the
 * `alert` and the assertion fails — exposing the unexpected codepath.
 */
export async function expectConfirm(page: Page, messagePattern: RegExp | string): Promise<void> {
  const dialog = await page.waitForEvent('dialog');
  expect(dialog.type()).toBe('confirm');
  if (typeof messagePattern === 'string') {
    expect(dialog.message()).toContain(messagePattern);
  } else {
    expect(dialog.message()).toMatch(messagePattern);
  }
  await dialog.accept();
}
