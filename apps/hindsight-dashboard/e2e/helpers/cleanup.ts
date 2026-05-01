import type { APIRequestContext } from '@playwright/test';
import { runId } from './runId';

/**
 * Per-run cleanup helpers.
 *
 * Each test creates entities prefixed with `test-${runId}-`. After the test
 * (or the suite) runs, this helper deletes those entities via the same API
 * the dashboard uses. Reference dataset entities (those owned by the fixed
 * `e2e-reference-agent`) are intentionally never touched — round-2 review
 * F6 flagged the risk of broad cleanup wiping shared mutable state.
 */

const PREFIX = `test-${runId}-`;

/**
 * The reference agent name, owned by `seedReferenceData()` (see fixture for #99).
 * Cleanup helpers must skip anything attached to this agent.
 */
export const REFERENCE_AGENT_NAME = 'e2e-reference-agent';

/**
 * Delete all agents created during this run.
 * Uses the agent_name prefix to scope deletion; never touches the reference agent.
 */
export async function cleanupAgents(api: APIRequestContext, headers: Record<string, string>): Promise<number> {
  const resp = await api.get('/api/agents/', { headers });
  if (!resp.ok()) return 0;
  const data = await resp.json();
  const items: Array<{ agent_id: string; agent_name: string }> = data.items || data || [];
  let deleted = 0;
  for (const a of items) {
    if (a.agent_name === REFERENCE_AGENT_NAME) continue;
    if (!a.agent_name.startsWith(PREFIX)) continue;
    const r = await api.delete(`/api/agents/${a.agent_id}`, { headers });
    if (r.ok() || r.status() === 404) deleted++;
  }
  return deleted;
}

/**
 * Delete all keywords created during this run.
 */
export async function cleanupKeywords(api: APIRequestContext, headers: Record<string, string>): Promise<number> {
  const resp = await api.get('/api/keywords/', { headers });
  if (!resp.ok()) return 0;
  const data = await resp.json();
  const items: Array<{ keyword_id: string; keyword_text: string }> = data.items || data || [];
  let deleted = 0;
  for (const k of items) {
    if (!k.keyword_text.startsWith(PREFIX)) continue;
    const r = await api.delete(`/api/keywords/${k.keyword_id}`, { headers });
    if (r.ok() || r.status() === 404) deleted++;
  }
  return deleted;
}

/**
 * Run all cleanup steps in a sensible order (keywords first since they reference blocks).
 */
export async function cleanupAll(
  api: APIRequestContext,
  headers: Record<string, string>,
): Promise<{ keywords: number; agents: number }> {
  const keywords = await cleanupKeywords(api, headers);
  const agents = await cleanupAgents(api, headers);
  return { keywords, agents };
}
