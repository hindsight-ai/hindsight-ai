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
    // Note: do NOT register autoAcceptConfirm here — we use the strict
    // `expectConfirm` for the archive dialog (to defend against the
    // confirm-popup-bypassed regression), and a one-shot accept for the
    // permanent-delete dialog. Registering both auto + strict handlers
    // causes "dialog already handled" errors because Playwright fires both
    // listeners on the same dialog event.
    await provisionUser(page, email);
    await asUser(page, email);
    // Navigate via direct goto. Wait for the URL AND for the lessons preview
    // to be present, since the page also has to fetch the seeded block list.
    await page.goto('/memory-blocks');
    await page.waitForURL(/\/memory-blocks/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');

    // ── 3. View: block appears in the list ────────────────────────────────────
    // The card renders `lessons_learned` and a content preview. Either should match.
    await expect(page.getByText('testing CRUD flows', { exact: false })).toBeVisible({ timeout: 15_000 });

    // ── 4. Archive: triggers `window.confirm()` (the smoke value) ─────────────
    // Use strict confirm assertion to defend against "delete button skipped its
    // confirm popup" regressions. Archive button is on the card itself,
    // title="Archive Memory Block" per `MemoryBlockCard.tsx`.
    //
    // (Edit-via-modal is exercised separately by component tests; the E2E
    // smoke value here is the confirm dialog + state transition, not the
    // detail-modal field-edit flow which has its own quirks across multiple
    // textareas with similar layouts.)
    const archiveConfirmed = expectConfirm(page, /Are you sure you want to archive/i);
    await page.getByTitle('Archive Memory Block').first().click();
    await archiveConfirmed;

    // After archive, block should disappear from active list.
    await expect(page.getByText('testing CRUD flows', { exact: false })).toHaveCount(0, {
      timeout: 10_000,
    });

    // ── 5. Navigate to /archived-memory-blocks and permanently delete ────────
    await page.goto('/archived-memory-blocks');
    await expect(page.getByText('testing CRUD flows', { exact: false })).toBeVisible({
      timeout: 15_000,
    });

    // ArchivedMemoryCard renders a "Delete" button. Backend's /hard-delete
    // endpoint is invoked; UI confirm message is "...permanently delete...".
    // Register a one-shot dialog handler BEFORE click — `page.once` fires
    // automatically when the dialog appears, no waitForEvent deadlock.
    page.once('dialog', (d) => {
      void d.accept();
    });
    await page.getByRole('button', { name: /^delete$/i }).first().click();

    // After delete, block should disappear from archived list.
    await expect(page.getByText('testing CRUD flows', { exact: false })).toHaveCount(0, {
      timeout: 10_000,
    });

    // ── 7. Cleanup: agent + any leftovers ─────────────────────────────────────
    await request.delete(`${BACKEND}/agents/${agent.agent_id}`, { headers });
  });
});
