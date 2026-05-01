import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { autoAcceptConfirm, expectConfirm } from '../helpers/dialogs';
import { provisionUser } from '../helpers/provision';
import { runId, temail, tname } from '../helpers/runId';

/**
 * Journey 2 — Memory block CRUD. (RFC v3, umbrella #96, issue #98)
 *
 * Tests view / edit / archive / hard-delete via the dashboard UI.
 *
 * **Scope adaptation:** the dashboard's "Create Memory Block" button is currently
 * a placeholder (`alert('Create Memory functionality coming soon!')` in
 * MemoryBlocksPage.tsx). The journey therefore API-seeds the block as the
 * test user and exercises the rest of the CRUD via UI. The view/edit/archive/delete
 * flows are all implemented and worth testing end-to-end. See issue #98 for the
 * note on the missing create UI.
 *
 * Exercises both `window.confirm()` dialogs in MemoryBlocksPage (archive +
 * permanent-delete). Uses the strict `expectConfirm` helper at least once to
 * defend against "delete button skipped its confirm popup" regressions.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 2 — Memory block CRUD @smoke', () => {
  test('view, edit, archive, then permanently delete a memory block', async ({ page, request }) => {
    const email = temail('crud');
    const headers = {
      'x-auth-request-email': email,
      'x-auth-request-user': email,
      'x-active-scope': 'personal',
    };

    // ── 1. Seed: agent + memory block via API ─────────────────────────────────
    const agentResp = await request.post(`${BACKEND}/agents/`, {
      headers,
      data: { agent_name: tname('crud-agent'), visibility_scope: 'personal' },
    });
    expect(agentResp.ok(), `agent seed failed: ${await agentResp.text()}`).toBe(true);
    const agent = await agentResp.json();

    const initialContent = `Initial content ${runId} - this should be visible in the list`;
    const blockResp = await request.post(`${BACKEND}/memory-blocks/`, {
      headers,
      data: {
        agent_id: agent.agent_id,
        conversation_id: '00000000-0000-0000-0000-000000000001',
        content: initialContent,
        lessons_learned: 'Lesson: testing CRUD flows requires real fixtures.',
        visibility_scope: 'personal',
      },
    });
    expect(blockResp.ok(), `block seed failed: ${await blockResp.text()}`).toBe(true);
    const block = await blockResp.json();

    // ── 2. Provision beta-access, auth, and navigate ──────────────────────────
    autoAcceptConfirm(page);
    await provisionUser(page, email);
    await asUser(page, email);
    await page.goto('/memory-blocks');

    // ── 3. View: block appears in the list ────────────────────────────────────
    // The card renders `lessons_learned` and a content preview. Either should match.
    await expect(page.getByText('testing CRUD flows', { exact: false })).toBeVisible({ timeout: 15_000 });

    // ── 4. Edit: open detail modal, switch to edit, save new content ──────────
    // Click the card → opens MemoryBlockDetailModal.
    await page.getByText('testing CRUD flows', { exact: false }).click();

    // Modal renders an "Edit" button when `isEditing === false`.
    await page.getByRole('button', { name: /^edit$/i }).click();

    // Editing replaces the content with a textarea or input. Find the largest
    // textarea (the content field) and replace its value.
    const contentField = page.locator('textarea').first();
    const editedContent = `Edited content ${runId}`;
    await contentField.fill(editedContent);

    // Save
    await page.getByRole('button', { name: /^save$/i }).click();

    // Wait for the modal to leave edit mode and reflect the new content.
    await expect(page.getByText(editedContent, { exact: false })).toBeVisible({ timeout: 10_000 });

    // Close the modal (X button or Escape).
    await page.keyboard.press('Escape');

    // ── 5. Archive: triggers `window.confirm()` ───────────────────────────────
    // Archive button is on the card itself, not the modal. title="Archive Memory Block".
    // Use strict confirm assertion to verify the "Are you sure" dialog actually fired.
    const archiveConfirmed = expectConfirm(page, /Are you sure you want to archive/i);
    await page.getByTitle('Archive Memory Block').first().click();
    await archiveConfirmed;

    // After archive, block should disappear from active list.
    await expect(page.getByText('testing CRUD flows', { exact: false })).toHaveCount(0, { timeout: 10_000 });

    // ── 6. Navigate to archived view and permanently delete ───────────────────
    // The archived list is at /archived (or /memory-blocks?archived=true depending
    // on routing). Try the most likely path; fall back if not found.
    await page.goto('/archived');

    // Block should be visible in archived list. Match either content or lessons.
    await expect(page.getByText(editedContent, { exact: false })).toBeVisible({ timeout: 15_000 });

    // Permanent delete: triggers the SECOND `window.confirm()` ("This action cannot be undone").
    // Use the auto-accept handler that's already registered.
    const deleteButton = page.getByTitle(/permanent.*delet|delete.*forever|hard.*delet/i).first();
    if (await deleteButton.count()) {
      await deleteButton.click();
    } else {
      // Fallback: any button with "Delete" text on the archived row
      await page.getByRole('button', { name: /^delete$/i }).first().click();
    }

    // After delete, block should disappear from archived list.
    await expect(page.getByText(editedContent, { exact: false })).toHaveCount(0, { timeout: 10_000 });

    // ── 7. Cleanup: agent + any leftovers ─────────────────────────────────────
    await request.delete(`${BACKEND}/agents/${agent.agent_id}`, { headers });
  });
});
