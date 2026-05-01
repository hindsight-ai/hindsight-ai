import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { autoAcceptConfirm, expectConfirm } from '../helpers/dialogs';
import { provisionUser } from '../helpers/provision';
import { temail, tname, runId } from '../helpers/runId';

/**
 * Journey 7 — Pruning. (RFC v3, umbrella #96, issue #108)
 *
 * Validates the pruning UI: generate suggestions → confirm pruning →
 * verify blocks are archived.
 *
 * **Backend gate bypass:** the pruning service has a deterministic
 * `_fallback_scoring` heuristic that runs when LLM_API_KEY is unset.
 * The endpoint-level 503 gate (`if not llm_features_enabled(): raise 503`)
 * normally prevents reaching it; this PR adds an `E2E_TEST_HOOKS=true`
 * bypass so the fallback can run in CI and produce repeatable scores.
 *
 * Tagged @full — runs on push to staging.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 7 — Pruning @full', () => {
  test('generate suggestions, confirm pruning, verify archive', async ({ page, request }) => {
    autoAcceptConfirm(page);
    const email = temail('prune-user');
    await provisionUser(page, email);
    const headers = { 'x-auth-request-email': email, 'x-auth-request-user': email, 'x-active-scope': 'personal' };

    // ── 1. Seed: agent + several memory blocks (need enough for the heuristic
    //         to score them) ──────────────────────────────────────────────────
    const agentRes = await request.post(`${BACKEND}/agents/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: { agent_name: tname('prune-agent'), visibility_scope: 'personal' },
    });
    expect(agentRes.ok()).toBe(true);
    const agent = await agentRes.json();

    // Seed 5 blocks with varying content lengths and "engagement" so the
    // fallback heuristic produces a range of scores.
    for (let i = 0; i < 5; i++) {
      const r = await request.post(`${BACKEND}/memory-blocks/`, {
        headers: { ...headers, 'content-type': 'application/json' },
        data: {
          agent_id: agent.agent_id,
          conversation_id: `00000000-0000-0000-0000-00000000070${i}`,
          content: `Pruning candidate ${i} ${runId} ${'.'.repeat(50 * (i + 1))}`,
          lessons_learned: `lesson ${i}`,
          visibility_scope: 'personal',
        },
      });
      expect(r.ok()).toBe(true);
    }

    // ── 2. Navigate to /pruning-suggestions ───────────────────────────────────
    await asUser(page, email);
    await page.goto('/pruning-suggestions');

    // ── 3. Click "Generate Suggestions" ──────────────────────────────────────
    await page.getByRole('button', { name: /generate suggestions/i }).click();

    // Wait for the fallback heuristic to compute scores. It's deterministic
    // and CPU-only (sklearn), so completes within a few seconds.
    // The UI renders cards with the seeded block content once suggestions arrive.
    await expect(page.getByText(/Pruning candidate \d+ /).first()).toBeVisible({
      timeout: 25_000,
    });

    // ── 4. Select the first suggestion via its checkbox ───────────────────────
    // The selection UI uses native checkboxes per row. Click the first one.
    const firstCheckbox = page.locator('input[type="checkbox"]').first();
    await firstCheckbox.check();

    // ── 5. Confirm Pruning — uses strict expectConfirm to defend against
    //         "confirm popup got bypassed" regressions ──────────────────────────
    const dialog = expectConfirm(
      page,
      /Are you sure you want to archive .* memory blocks for pruning/i,
    );
    await page.getByRole('button', { name: /confirm pruning/i }).click();
    await dialog;

    // ── 6. Verify at least one block was archived via API ─────────────────────
    // Wait briefly for the backend to commit the archive.
    await page.waitForTimeout(1_000);
    const archivedRes = await request.get(`${BACKEND}/memory-blocks/`, {
      headers,
      params: { include_archived: 'true', limit: '50' },
    });
    const data = await archivedRes.json();
    const items: Array<{ id: string; archived?: boolean; agent_id: string }> = data.items || data;
    const archivedFromOurAgent = items.filter(
      (b) => b.agent_id === agent.agent_id && b.archived === true,
    );
    expect(archivedFromOurAgent.length, 'at least one block should be archived').toBeGreaterThan(0);

    // ── 7. Cleanup ────────────────────────────────────────────────────────────
    await request.delete(`${BACKEND}/agents/${agent.agent_id}`, { headers });
  });
});
