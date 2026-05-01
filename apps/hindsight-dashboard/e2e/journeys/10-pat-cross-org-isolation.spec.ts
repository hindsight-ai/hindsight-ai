import { test, expect } from '@playwright/test';
import { asPAT, asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail, tname, runId } from '../helpers/runId';

/**
 * Journey 10 — PAT cross-org isolation. (RFC v3, umbrella #96, issue #102)
 *
 * **The single highest-value test in the suite.** The cross-org PAT boundary
 * is the one auth-bug class that ONLY a real browser session can validate:
 *   - Backend tests mock `current_user` — they never actually verify the
 *     dependency chain `auth header → PAT scope narrowing → 403`.
 *   - Frontend tests mock the API entirely — they never issue real PAT-bearing
 *     requests.
 *
 * Setup:
 *   1. As `multiOrgUser`: create org-A and org-B (owner of both)
 *   2. Create one memory block in each org
 *   3. Create a PAT scoped to ORG-A only (via /users/me/tokens)
 *   4. Switch the browser context to PAT auth via `asPAT`
 *   5. Attempt to fetch org-B's data with the PAT
 *
 * Assert: response is 403 AND `detail` matches `Token organization restriction
 * mismatch`. The exact-text assertion is required (per round-2 review F3) to
 * confirm the rejection happened at the `get_scoped_user_and_context`
 * dependency layer (introduced in #70), not in some route-body fallback.
 *
 * Tagged @smoke. Single multi-org user; no need for multi-user identity swap.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 10 — PAT cross-org isolation 🔒 @smoke', () => {
  test('PAT scoped to org-A cannot fetch org-B data; 403 fires at dependency layer', async ({
    page,
    request,
  }) => {
    const ownerEmail = temail('multi-org-owner');
    await provisionUser(page, ownerEmail);
    const ownerHeaders = { 'x-auth-request-email': ownerEmail, 'x-auth-request-user': ownerEmail };

    // ── 1. Create two orgs ────────────────────────────────────────────────────
    const orgARes = await request.post(`${BACKEND}/organizations/`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: { name: tname('org-A'), slug: `org-a-${runId}` },
    });
    expect(orgARes.ok(), `orgA create failed: ${await orgARes.text()}`).toBe(true);
    const orgA = await orgARes.json();

    const orgBRes = await request.post(`${BACKEND}/organizations/`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: { name: tname('org-B'), slug: `org-b-${runId}` },
    });
    expect(orgBRes.ok(), `orgB create failed: ${await orgBRes.text()}`).toBe(true);
    const orgB = await orgBRes.json();

    // ── 2. Seed a memory block in each org ────────────────────────────────────
    // Each block needs an agent. Create one per org (org-scoped agent).
    const agentARes = await request.post(`${BACKEND}/agents/`, {
      headers: {
        ...ownerHeaders,
        'content-type': 'application/json',
        'x-active-scope': 'organization',
        'x-organization-id': orgA.id,
      },
      data: { agent_name: tname('agent-a'), visibility_scope: 'organization', organization_id: orgA.id },
    });
    expect(agentARes.ok(), `agentA create failed: ${await agentARes.text()}`).toBe(true);
    const agentA = await agentARes.json();

    const agentBRes = await request.post(`${BACKEND}/agents/`, {
      headers: {
        ...ownerHeaders,
        'content-type': 'application/json',
        'x-active-scope': 'organization',
        'x-organization-id': orgB.id,
      },
      data: { agent_name: tname('agent-b'), visibility_scope: 'organization', organization_id: orgB.id },
    });
    expect(agentBRes.ok(), `agentB create failed: ${await agentBRes.text()}`).toBe(true);
    const agentB = await agentBRes.json();

    const blockARes = await request.post(`${BACKEND}/memory-blocks/`, {
      headers: {
        ...ownerHeaders,
        'content-type': 'application/json',
        'x-active-scope': 'organization',
        'x-organization-id': orgA.id,
      },
      data: {
        agent_id: agentA.agent_id,
        conversation_id: '00000000-0000-0000-0000-00000000000a',
        content: `org-A secret content ${runId}`,
        visibility_scope: 'organization',
        organization_id: orgA.id,
      },
    });
    expect(blockARes.ok(), `blockA create failed: ${await blockARes.text()}`).toBe(true);

    const blockBRes = await request.post(`${BACKEND}/memory-blocks/`, {
      headers: {
        ...ownerHeaders,
        'content-type': 'application/json',
        'x-active-scope': 'organization',
        'x-organization-id': orgB.id,
      },
      data: {
        agent_id: agentB.agent_id,
        conversation_id: '00000000-0000-0000-0000-00000000000b',
        content: `org-B secret content ${runId}`,
        visibility_scope: 'organization',
        organization_id: orgB.id,
      },
    });
    expect(blockBRes.ok(), `blockB create failed: ${await blockBRes.text()}`).toBe(true);

    // ── 3. Create a PAT scoped to org-A only ──────────────────────────────────
    const tokenRes = await request.post(`${BACKEND}/users/me/tokens`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: {
        name: tname('org-a-pat'),
        scopes: ['read', 'write'],
        organization_id: orgA.id,
      },
    });
    expect(tokenRes.ok(), `PAT create failed: ${await tokenRes.text()}`).toBe(true);
    const tokenData = await tokenRes.json();
    const patToken: string = tokenData.token;
    expect(patToken, 'response should include the one-time token string').toBeTruthy();

    // ── 4. Switch browser to PAT auth ─────────────────────────────────────────
    await asPAT(page, patToken);

    // ── 5. Attempt to fetch org-B data via the PAT — expect 403 ───────────────
    // Using `?organization_id=<orgB>` triggers the dependency-layer mismatch
    // check in deps.py:get_scoped_user_and_context.
    const probeRes = await page.request.get(
      `${BACKEND}/memory-blocks/?organization_id=${orgB.id}`,
    );
    expect(probeRes.status(), 'org-A PAT must not fetch org-B').toBe(403);
    const detail = await probeRes.text();
    expect(detail, 'detail must come from the dependency layer (#70)').toMatch(
      /Token organization restriction mismatch/,
    );

    // ── 6. Sanity: same PAT CAN fetch org-A data ──────────────────────────────
    const orgARes2 = await page.request.get(
      `${BACKEND}/memory-blocks/?organization_id=${orgA.id}`,
    );
    expect(orgARes2.ok(), `org-A PAT must fetch org-A: ${await orgARes2.text()}`).toBe(true);
    const orgABlocks = await orgARes2.json();
    const items = orgABlocks.items || orgABlocks;
    expect(items.length, 'expected at least the seeded org-A block').toBeGreaterThan(0);

    // ── 7. Cleanup: revoke PAT, delete orgs (cascades blocks/agents) ──────────
    await page.context().setExtraHTTPHeaders({}); // drop PAT auth
    await asUser(page, ownerEmail);
    await request.delete(`${BACKEND}/users/me/tokens/${tokenData.id}`, { headers: ownerHeaders });
    await request.delete(`${BACKEND}/organizations/${orgA.id}`, { headers: ownerHeaders });
    await request.delete(`${BACKEND}/organizations/${orgB.id}`, { headers: ownerHeaders });
  });
});
