import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail, tname } from '../helpers/runId';

/**
 * Journey 13 — Compaction trigger. (RFC v3, umbrella #96, issue #111)
 *
 * The compaction flow has two halves:
 *   1. **Trigger**: user clicks "Compact" on a memory block card. The handler
 *      checks `llmEnabled` — if disabled, shows a toast and bails; if enabled,
 *      opens the `MemoryCompactionModal`. Pure client-side logic.
 *   2. **Apply**: the modal calls `POST /memory-blocks/:id/compress` which is
 *      LLM-gated and returns 503 in CI.
 *
 * This journey exercises the **disabled-LLM trigger path** in CI:
 *   - Seed a memory block
 *   - Click Compact button → verify toast shown ("LLM features are currently disabled")
 *   - Verify modal does NOT open (regression defense: a bug that opens the
 *     modal anyway and tries to apply against the disabled backend would
 *     produce a confusing error rather than the clean toast UX)
 *
 * The enabled-LLM apply path stays deferred — needs LLM in CI to test.
 *
 * Tagged @full — runs on push to staging.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 13 — Compaction trigger (LLM-disabled path) @full', () => {
  test('clicking Compact when LLM is disabled shows toast, does not open modal', async ({ page, request }) => {
    const email = temail('compact-user');
    await provisionUser(page, email);
    const headers = { 'x-auth-request-email': email, 'x-auth-request-user': email, 'x-active-scope': 'personal' };

    // ── 1. Seed a memory block with substantial content ──────────────────────
    const agentRes = await request.post(`${BACKEND}/agents/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: { agent_name: tname('compact-agent'), visibility_scope: 'personal' },
    });
    expect(agentRes.ok()).toBe(true);
    const agent = await agentRes.json();

    const longContent = 'compaction trigger test content. '.repeat(80); // ~2500 chars
    const blockRes = await request.post(`${BACKEND}/memory-blocks/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: {
        agent_id: agent.agent_id,
        conversation_id: '00000000-0000-0000-0000-000000001301',
        content: longContent,
        lessons_learned: 'Compaction trigger journey block',
        visibility_scope: 'personal',
      },
    });
    expect(blockRes.ok()).toBe(true);

    // ── 2. Navigate to /memory-blocks ─────────────────────────────────────────
    await asUser(page, email);
    await page.goto('/memory-blocks');

    // Block card should render with the lessons preview.
    await expect(page.getByText('Compaction trigger journey block')).toBeVisible({ timeout: 15_000 });

    // ── 3. Click the Compact button on the card ──────────────────────────────
    // The button has title="Compact Memory - Intelligently condense content"
    // (per MemoryBlockCard.tsx around line 95).
    const compactBtn = page.getByTitle(/Compact Memory/i).first();
    await expect(compactBtn).toBeVisible({ timeout: 10_000 });

    // Track if the modal opens — it shouldn't, because LLM is disabled in CI.
    // The modal heading should never appear on screen.
    await compactBtn.click();

    // Give the click a chance to surface a toast or open the modal.
    await page.waitForTimeout(1_000);

    // The compaction modal must NOT have opened. The modal's distinctive
    // content includes "Compaction Settings" or "Compact Memory Block" headers.
    await expect(
      page.getByRole('heading', { name: /compaction settings|compact memory block/i }),
    ).toHaveCount(0);

    // The toast should be visible (or the notification has been logged).
    // notificationService inserts the toast into a notification container.
    // Match the literal text from `MemoryBlockCard.tsx:28` /
    // `MemoryBlocksPage.tsx:300`.
    await expect(page.getByText(/LLM features are currently disabled/i)).toBeVisible({
      timeout: 5_000,
    });

    // ── 4. Cleanup ────────────────────────────────────────────────────────────
    await request.delete(`${BACKEND}/agents/${agent.agent_id}`, { headers });
  });
});
