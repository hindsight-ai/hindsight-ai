import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail, tname, runId } from '../helpers/runId';

/**
 * Journey 5 — Consolidation validate / reject. (RFC v3, umbrella #96, issue #106)
 *
 * Uses the new test-only fixture endpoint
 * `POST /test-fixtures/consolidation-suggestion` (gated behind
 * `E2E_TEST_HOOKS=true` — see `core/api/test_fixtures.py`) to seed
 * suggestion rows directly. The production-path generation goes through
 * the LLM-driven consolidation worker which is gated by
 * `LLM_FEATURES_ENABLED=true` and not available in CI.
 *
 * Tagged @full — runs on push to staging.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 5 — Consolidation validate / reject @full', () => {
  test('seeded suggestions can be validated and rejected via the UI', async ({ page, request }) => {
    const email = temail('consolidation-user');
    await provisionUser(page, email);
    const headers = { 'x-auth-request-email': email, 'x-auth-request-user': email, 'x-active-scope': 'personal' };

    // ── 1. Seed agent + 2 source memory blocks ───────────────────────────────
    const agentRes = await request.post(`${BACKEND}/agents/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: { agent_name: tname('cons-agent'), visibility_scope: 'personal' },
    });
    expect(agentRes.ok()).toBe(true);
    const agent = await agentRes.json();

    const block1Res = await request.post(`${BACKEND}/memory-blocks/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: {
        agent_id: agent.agent_id,
        conversation_id: '00000000-0000-0000-0000-000000000501',
        content: `Original block 1 ${runId}`,
        lessons_learned: 'Lesson 1',
        visibility_scope: 'personal',
      },
    });
    const block1 = await block1Res.json();

    const block2Res = await request.post(`${BACKEND}/memory-blocks/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: {
        agent_id: agent.agent_id,
        conversation_id: '00000000-0000-0000-0000-000000000502',
        content: `Original block 2 ${runId}`,
        lessons_learned: 'Lesson 2',
        visibility_scope: 'personal',
      },
    });
    const block2 = await block2Res.json();

    // ── 2. Seed two consolidation suggestions via the test-fixture endpoint ──
    const suggestion1ToValidate = `Validate-${runId}`;
    const seed1Res = await request.post(`${BACKEND}/test-fixtures/consolidation-suggestion`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: {
        suggested_content: `${suggestion1ToValidate}: merged content (will be validated)`,
        suggested_lessons_learned: 'Validated suggestion lesson',
        suggested_keywords: ['merged', 'consolidated'],
        original_memory_ids: [block1.id, block2.id],
      },
    });
    expect(seed1Res.status(), `seed 1 failed: ${await seed1Res.text()}`).toBe(201);
    const seed1 = await seed1Res.json();

    const suggestion2ToReject = `Reject-${runId}`;
    const seed2Res = await request.post(`${BACKEND}/test-fixtures/consolidation-suggestion`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: {
        suggested_content: `${suggestion2ToReject}: merged content (will be rejected)`,
        suggested_lessons_learned: 'Rejected suggestion lesson',
        suggested_keywords: ['rejected', 'discarded'],
        original_memory_ids: [block1.id, block2.id],
      },
    });
    expect(seed2Res.status()).toBe(201);
    const seed2 = await seed2Res.json();

    // ── 3. Navigate to consolidation suggestions UI ──────────────────────────
    await asUser(page, email);
    // Auto-accept the alert() that handleValidate / handleReject pop up.
    page.on('dialog', (d) => {
      void d.accept();
    });

    await page.goto('/consolidation-suggestions');

    // Both suggestions should be visible.
    await expect(page.getByText(suggestion1ToValidate, { exact: false })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(suggestion2ToReject, { exact: false })).toBeVisible({ timeout: 5_000 });

    // ── 4. Validate the first suggestion via UI ──────────────────────────────
    const card1 = page.locator('article,div,li,tr').filter({ hasText: suggestion1ToValidate }).first();
    await card1.getByRole('button', { name: /^accept$/i }).click();

    // ── 5. Reject the second suggestion ──────────────────────────────────────
    const card2 = page.locator('article,div,li,tr').filter({ hasText: suggestion2ToReject }).first();
    await card2.getByRole('button', { name: /^reject$/i }).click();

    // ── 6. Verify status flips via API ───────────────────────────────────────
    await page.waitForTimeout(500);
    const listRes = await request.get(`${BACKEND}/consolidation-suggestions/`, { headers });
    const data = await listRes.json();
    const items: Array<{ suggestion_id: string; status: string }> = data.items || data;
    const after1 = items.find((s) => s.suggestion_id === seed1.suggestion_id);
    const after2 = items.find((s) => s.suggestion_id === seed2.suggestion_id);
    expect(after1?.status?.toLowerCase()).toBe('validated');
    expect(after2?.status?.toLowerCase()).toBe('rejected');

    // ── 7. Cleanup ────────────────────────────────────────────────────────────
    await request.delete(`${BACKEND}/consolidation-suggestions/${seed1.suggestion_id}`, { headers });
    await request.delete(`${BACKEND}/consolidation-suggestions/${seed2.suggestion_id}`, { headers });
    await request.delete(`${BACKEND}/agents/${agent.agent_id}`, { headers });
  });
});
