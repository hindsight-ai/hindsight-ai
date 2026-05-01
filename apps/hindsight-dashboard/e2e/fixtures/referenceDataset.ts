import type { APIRequestContext } from '@playwright/test';

/**
 * Reference dataset for the search journey (#99 / journey 3a).
 *
 * Seeds 50 memory blocks of varied content owned by a fixed user so that
 * search-ranking assertions can use positional checks ("query 'python'
 * returns the python-content block at position ≤ 3") rather than just
 * existence. The dataset is shared across the suite but only USED by
 * search tests; cleanup helpers explicitly skip the reference agent
 * (per round-2 review F6).
 *
 * Owner: `e2e-reference-owner@e2e.local`. Must be in BETA_ACCESS_ADMINS
 * so beta-access doesn't gate the seed.
 *
 * Idempotent: globalSetup checks block count and re-seeds only on drift.
 */

const BACKEND = 'http://localhost:8000';

export const REFERENCE_OWNER_EMAIL = 'e2e-reference-owner@e2e.local';
export const REFERENCE_OWNER_NAME = 'E2E Reference Owner';
export const REFERENCE_AGENT_NAME = 'e2e-reference-agent';
export const REFERENCE_BLOCK_COUNT = 50;

interface ReferenceBlock {
  content: string;
  lessons_learned: string;
  // Positional-assertion anchor — tests grep for these unique substrings
  marker: string;
}

/**
 * The 50 reference blocks. Each has a distinctive `marker` substring that
 * the journey 3a tests grep for. Variety in topics + word distribution
 * lets us validate ranking quality, not just hit/miss.
 */
function buildReferenceBlocks(): ReferenceBlock[] {
  const topics = [
    { topic: 'python', uniques: ['python-async', 'python-fastapi', 'python-pytest', 'python-typing'] },
    { topic: 'react', uniques: ['react-hooks', 'react-context', 'react-query', 'react-router'] },
    { topic: 'postgres', uniques: ['postgres-index', 'postgres-vacuum', 'postgres-jsonb', 'postgres-trigger'] },
    { topic: 'docker', uniques: ['docker-compose', 'docker-network', 'docker-volume', 'docker-buildkit'] },
    { topic: 'auth', uniques: ['auth-oauth2', 'auth-jwt', 'auth-pat', 'auth-csrf'] },
    { topic: 'testing', uniques: ['testing-e2e', 'testing-mock', 'testing-fixture', 'testing-coverage'] },
    { topic: 'api', uniques: ['api-rest', 'api-graphql', 'api-pagination', 'api-versioning'] },
    { topic: 'database', uniques: ['database-migration', 'database-orm', 'database-pool', 'database-replica'] },
    { topic: 'cache', uniques: ['cache-redis', 'cache-cdn', 'cache-stale', 'cache-warm'] },
    { topic: 'logging', uniques: ['logging-structured', 'logging-trace', 'logging-correlation', 'logging-rotation'] },
    { topic: 'security', uniques: ['security-audit', 'security-pen', 'security-tls', 'security-rotation'] },
    { topic: 'deploy', uniques: ['deploy-blue', 'deploy-canary', 'deploy-rollback', 'deploy-feature'] },
    { topic: 'monitor', uniques: ['monitor-metric', 'monitor-alert'] },
  ];
  const blocks: ReferenceBlock[] = [];
  for (const t of topics) {
    for (const u of t.uniques) {
      blocks.push({
        marker: u,
        content: `Key insight: ${u} works well when applied to ${t.topic} workflows. Reference dataset entry.`,
        lessons_learned: `${t.topic} pattern: use ${u} for production-grade ${t.topic} pipelines.`,
      });
    }
  }
  // Truncate or pad to exactly REFERENCE_BLOCK_COUNT
  while (blocks.length > REFERENCE_BLOCK_COUNT) blocks.pop();
  while (blocks.length < REFERENCE_BLOCK_COUNT) {
    const i = blocks.length;
    blocks.push({
      marker: `padding-${i}`,
      content: `Padding entry ${i}. Reference dataset filler. Topic: misc.`,
      lessons_learned: `padding-${i} lesson: filler content for the reference dataset.`,
    });
  }
  return blocks;
}

export const REFERENCE_BLOCKS = buildReferenceBlocks();

/**
 * Idempotent seeder — used by `e2e/global-setup.ts` once before workers start.
 *
 * Steps:
 *   1. Hit /user-info as the reference owner (creates row).
 *   2. Look up or create the reference agent.
 *   3. Count existing blocks under that agent. If exactly REFERENCE_BLOCK_COUNT,
 *      return (idempotent).
 *   4. Otherwise, delete all existing blocks under the agent + recreate from
 *      `REFERENCE_BLOCKS` (drift recovery).
 */
export async function seedReferenceDataset(ctx: APIRequestContext): Promise<{ agentId: string; blockCount: number }> {
  const headers = {
    'x-auth-request-email': REFERENCE_OWNER_EMAIL,
    'x-auth-request-user': REFERENCE_OWNER_NAME,
    'x-active-scope': 'personal',
  };

  // 1. Owner row
  await ctx.get(`${BACKEND}/user-info`, { headers });

  // 2. Find or create the agent
  const agentsResp = await ctx.get(`${BACKEND}/agents/`, {
    headers,
    params: { scope: 'personal' },
  });
  const agentsData = await agentsResp.json();
  const items: Array<{ agent_id: string; agent_name: string }> = agentsData.items || agentsData || [];
  let agent = items.find((a) => a.agent_name === REFERENCE_AGENT_NAME);

  if (!agent) {
    const createResp = await ctx.post(`${BACKEND}/agents/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: { agent_name: REFERENCE_AGENT_NAME, visibility_scope: 'personal' },
    });
    if (!createResp.ok()) {
      throw new Error(`[reference] failed to create agent: ${createResp.status()} ${await createResp.text()}`);
    }
    agent = await createResp.json();
  }

  // 3. Count existing blocks
  const blocksResp = await ctx.get(`${BACKEND}/memory-blocks/`, {
    headers,
    params: { agent_id: agent!.agent_id, scope: 'personal', limit: '200' },
  });
  const blocksData = await blocksResp.json();
  const existingBlocks: Array<{ id: string }> = blocksData.items || blocksData || [];

  if (existingBlocks.length === REFERENCE_BLOCK_COUNT) {
    return { agentId: agent!.agent_id, blockCount: existingBlocks.length };
  }

  // 4. Drift — delete + reseed
  // eslint-disable-next-line no-console
  console.log(
    `[reference] drift detected (have ${existingBlocks.length}, want ${REFERENCE_BLOCK_COUNT}); reseeding`,
  );
  for (const b of existingBlocks) {
    await ctx.delete(`${BACKEND}/memory-blocks/${b.id}/hard-delete`, { headers });
  }
  for (let i = 0; i < REFERENCE_BLOCKS.length; i++) {
    const b = REFERENCE_BLOCKS[i];
    const r = await ctx.post(`${BACKEND}/memory-blocks/`, {
      headers: { ...headers, 'content-type': 'application/json' },
      data: {
        agent_id: agent!.agent_id,
        // Make conversation_ids unique-per-block so the backend doesn't merge
        conversation_id: `00000000-0000-0000-0000-${i.toString(16).padStart(12, '0')}`,
        content: b.content,
        lessons_learned: b.lessons_learned,
        visibility_scope: 'personal',
      },
    });
    if (!r.ok()) {
      throw new Error(
        `[reference] failed to create block ${i} (${b.marker}): ${r.status()} ${await r.text()}`,
      );
    }
  }
  return { agentId: agent!.agent_id, blockCount: REFERENCE_BLOCK_COUNT };
}
