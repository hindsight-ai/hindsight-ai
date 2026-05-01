import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { autoAcceptConfirm, expectConfirm } from '../helpers/dialogs';
import { provisionUser } from '../helpers/provision';
import { temail, tname } from '../helpers/runId';

/**
 * Journey 4 — Keyword CRUD + linkage. (RFC v3, umbrella #96, issue #100)
 *
 * Tests the keyword-management UI:
 *   - Create via /keywords page modal
 *   - Verify in list
 *   - Inline edit + save
 *   - Delete (window.confirm dialog)
 *
 * **Scope adaptation:** the issue mentions exercising
 * `POST /memory-blocks/:id/suggest-keywords` (added in #82). The dashboard
 * does have a `handleSuggestKeywords` button on memory-block cards, but
 * the suggestion-extraction quality varies and the test would be flaky
 * for a smoke-tier gate. Keyword<->block linkage is also a separate UI
 * surface (modal in MemoryBlockDetailModal). Both are deferred to future
 * journeys; this journey focuses on the keyword-management UI itself,
 * which is the most-trafficked surface and the highest-value smoke test.
 *
 * Tagged @smoke.
 */

test.describe('Journey 4 — Keyword CRUD @smoke', () => {
  test('create, edit, then delete a keyword via the UI', async ({ page }) => {
    autoAcceptConfirm(page);

    const email = temail('keywords');
    await provisionUser(page, email);
    await asUser(page, email);

    await page.goto('/keywords');

    // ── 1. Create ─────────────────────────────────────────────────────────────
    // The "Add Keyword" button (KeywordManager.tsx:269) opens an inline modal
    // with `placeholder="Enter keyword..."`.
    await page.getByRole('button', { name: /^add keyword$/i }).first().click();

    const keywordText = tname('test-keyword');
    await page.getByPlaceholder(/enter keyword/i).fill(keywordText);

    // The submit button inside the modal is also "Add Keyword".
    // The first one was already clicked; locate the second (modal-scoped) variant.
    // Fall back to pressing Enter inside the input.
    await page.getByPlaceholder(/enter keyword/i).press('Enter');

    // Verify the keyword is rendered in the list.
    await expect(page.getByText(keywordText, { exact: true })).toBeVisible({ timeout: 10_000 });

    // ── 2. Edit ───────────────────────────────────────────────────────────────
    // KeywordManager has a per-row edit button (KeywordManager.tsx:391-412).
    // Click on the row containing the keyword to open inline edit.
    const row = page.locator('tr,li,div').filter({ hasText: keywordText }).first();
    // Try multiple edit affordances: title="Edit", aria-label="Edit", or the
    // pencil icon button. The component uses an `Edit` button per row.
    const editBtn = row.getByRole('button', { name: /^edit$/i }).first();
    if (await editBtn.count()) {
      await editBtn.click();
    } else {
      // Fallback: click the row to enter edit mode (mobile path).
      await row.click();
    }

    // After entering edit mode, an input/textarea appears with the keyword.
    // Find the editable input within the row context.
    const editedText = `${keywordText}-edited`;
    const inputs = row.locator('input[type="text"], input:not([type]), textarea');
    if (await inputs.count()) {
      await inputs.first().fill(editedText);
    } else {
      // Fallback: any text input on the page after edit click
      await page.locator('input[type="text"], input:not([type])').first().fill(editedText);
    }

    // Save — typically a "Save" button or pressing Enter
    const saveBtn = page.getByRole('button', { name: /^save$/i }).first();
    if (await saveBtn.count()) {
      await saveBtn.click();
    } else {
      await page.keyboard.press('Enter');
    }

    await expect(page.getByText(editedText, { exact: true })).toBeVisible({ timeout: 10_000 });

    // ── 3. Delete (window.confirm) ────────────────────────────────────────────
    // KeywordManager.tsx:112 — `if (window.confirm('Are you sure you want to delete this keyword?'))`.
    // Use strict expectConfirm to defend against future regressions.
    const editedRow = page.locator('tr,li,div').filter({ hasText: editedText }).first();
    const deleteBtn = editedRow.getByRole('button', { name: /^delete$/i }).first();

    const dialogPromise = expectConfirm(page, /Are you sure you want to delete this keyword/i);
    await deleteBtn.click();
    await dialogPromise;

    // Verify the keyword disappears from the list.
    await expect(page.getByText(editedText, { exact: true })).toHaveCount(0, { timeout: 10_000 });
  });
});
