import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { expectConfirm } from '../helpers/dialogs';
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
    // Note: do NOT register autoAcceptConfirm — `expectConfirm` registers its
    // own one-shot dialog listener for the delete step, and Playwright errors
    // with "dialog already handled" if both fire on the same event (same
    // failure mode that bit journey 2 — see helpers/dialogs.ts comments).
    const email = temail('keywords');
    await provisionUser(page, email);
    await asUser(page, email);

    await page.goto('/keywords');

    // ── 1. Create ─────────────────────────────────────────────────────────────
    // The "Add Keyword" button (KeywordManager.tsx:269) opens an inline modal
    // with `placeholder="Enter keyword..."`. The modal contains a SECOND
    // "Add Keyword" button (KeywordManager.tsx:494) which is the actual submit
    // — pressing Enter inside the input does NOT submit (no form/keydown
    // handler). Scope the submit click to the modal via its "Add New Keyword"
    // heading to disambiguate from the page-header trigger button.
    await page.getByRole('button', { name: /^add keyword$/i }).first().click();

    const modal = page.locator('div').filter({
      has: page.getByRole('heading', { name: /add new keyword/i }),
    }).first();
    await expect(modal).toBeVisible({ timeout: 5_000 });

    const keywordText = tname('test-keyword');
    await modal.getByPlaceholder(/enter keyword/i).fill(keywordText);
    await modal.getByRole('button', { name: /^add keyword$/i }).click();

    // Verify the keyword is rendered in the list (modal closes on success).
    await expect(page.getByText(keywordText, { exact: true })).toBeVisible({ timeout: 10_000 });

    // ── 2. Edit ───────────────────────────────────────────────────────────────
    // KeywordManager has per-card SVG-only buttons — title attributes:
    // "Edit" (the pencil button) / "Save" (the checkmark) / "Delete" (trash).
    // `getByTitle('Edit')` would also match the keyword `<span title="Click
    // to edit">`, so use `button[title="..."]` to disambiguate.
    //
    // The keyword card matches `div:has(span:has-text(keyword))` BEFORE edit,
    // but during edit the span is replaced by an input, breaking that filter.
    // Once edit mode is on, locate the input via `getByDisplayValue` (the
    // input's value still equals the original text), and the Save button is
    // unique on the page (no other `button[title="Save"]` while editing one
    // card).
    const card = page.locator('div').filter({ hasText: new RegExp(`^${keywordText}$`) }).first();
    await card.locator('button[title="Edit"]').click();

    const editedText = `${keywordText}-edited`;
    // The edit input is autoFocused on mount (KeywordManager.tsx:374), so
    // `:focus` reliably points at it. The Add modal is closed, the search
    // box is not focused at this point.
    const editInput = page.locator('input:focus');
    await editInput.fill(editedText);
    await page.locator('button[title="Save"]').first().click();

    await expect(page.getByText(editedText, { exact: true })).toBeVisible({ timeout: 10_000 });

    // ── 3. Delete (window.confirm) ────────────────────────────────────────────
    // KeywordManager.tsx:112 — `if (window.confirm('Are you sure you want to delete this keyword?'))`.
    // Use strict expectConfirm to defend against future regressions.
    const editedCard = page.locator('div').filter({ hasText: new RegExp(`^${editedText}$`) }).first();
    const deleteBtn = editedCard.locator('button[title="Delete"]');

    const dialogPromise = expectConfirm(page, /Are you sure you want to delete this keyword/i);
    await deleteBtn.click();
    await dialogPromise;

    // Verify the keyword disappears from the list.
    await expect(page.getByText(editedText, { exact: true })).toHaveCount(0, { timeout: 10_000 });
  });
});
