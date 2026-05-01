import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail, tname, runId } from '../helpers/runId';

/**
 * Journey 6 — Memory optimization. (RFC v3, umbrella #96, issue #107)
 *
 * Validates the #80-split MemoryOptimizationCenter component end-to-end.
 *
 * **Important:** memory optimization suggestions are HEURISTIC (not LLM-
 * generated). `_compute_suggestions` in `core/api/memory_optimization.py`
 * looks for blocks with content > 1500 chars (compaction), blocks
 * without keywords (keywords), and blocks > 90 days old with low engagement
 * (archive). My initial deferral was wrong — this works in CI without LLM.
 *
 * The journey seeds memory blocks meeting the heuristic criteria, opens
 * the optimization center, and verifies real suggestions render.
 *
 * Tagged @full — runs on push to staging.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 6 — Memory optimization @full', () => {
  test('seeded blocks produce heuristic suggestions; refresh analysis works', async ({ page, request }) => {
    const email = temail('opt-user');
    await provisionUser(page, email);
    const headers = { 'x-auth-request-email': email, 'x-auth-request-user': email, 'x-active-scope': 'personal' };

    // ── 1. Seed: an agent + several memory blocks meeting the heuristic criteria ──
    const agentRes = await request.post(`${BACKEND}/agents/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: { agent_name: tname('opt-agent'), visibility_scope: 'personal' },
    });
    expect(agentRes.ok(), `agent seed failed: ${await agentRes.text()}`).toBe(true);
    const agent = await agentRes.json();

    // Long block (> 1500 chars) — triggers `compaction` suggestion
    const longContent = 'long block content. '.repeat(120); // ~2400 chars
    const longRes = await request.post(`${BACKEND}/memory-blocks/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: {
        agent_id: agent.agent_id,
        conversation_id: '00000000-0000-0000-0000-000000000601',
        content: longContent,
        lessons_learned: 'A long block to trigger the compaction heuristic.',
        visibility_scope: 'personal',
      },
    });
    expect(longRes.ok(), `long block seed failed: ${await longRes.text()}`).toBe(true);

    // 3 blocks without keywords — triggers `keywords` suggestion (note: long
    // block above also has no keywords, contributing to the count)
    for (let i = 0; i < 3; i++) {
      const r = await request.post(`${BACKEND}/memory-blocks/`, {
        headers: { ...headers, 'content-type': 'application/json' },
        data: {
          agent_id: agent.agent_id,
          conversation_id: `00000000-0000-0000-0000-00000000060${i + 2}`,
          content: `Block ${i} without keywords ${runId}`,
          lessons_learned: `lesson ${i}`,
          visibility_scope: 'personal',
        },
      });
      expect(r.ok()).toBe(true);
    }

    // ── 2. Navigate to the optimization center ────────────────────────────────
    await asUser(page, email);
    await page.goto('/memory-optimization-center');

    // ── 3. Verify suggestions are visible after analysis runs ─────────────────
    // The center auto-fetches on mount. Look for suggestion-card text:
    //   - "Compact N lengthy memory blocks" (compaction heuristic)
    //   - "Add keywords to N memory blocks" (keywords heuristic)
    await expect(
      page.getByText(/Compact \d+ lengthy memory blocks?/i).or(
        page.getByText(/Add keywords to \d+ memory blocks?/i),
      ),
    ).toBeVisible({ timeout: 20_000 });

    // ── 4. "Refresh Analysis" button re-runs the heuristics ───────────────────
    await page.getByRole('button', { name: /refresh analysis/i }).click();
    // The same suggestion cards should still be visible (data hasn't changed).
    await expect(
      page.getByText(/Compact \d+ lengthy memory blocks?/i).or(
        page.getByText(/Add keywords to \d+ memory blocks?/i),
      ),
    ).toBeVisible({ timeout: 20_000 });

    // ── 5. Cleanup: delete the agent (cascades blocks) ────────────────────────
    await request.delete(`${BACKEND}/agents/${agent.agent_id}`, { headers });
  });
});
