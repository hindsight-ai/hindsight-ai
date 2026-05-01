/**
 * Per-suite-run unique identifier for namespacing test data.
 *
 * Every entity created during a suite run uses this prefix so that
 * (a) tests don't collide with each other, (b) cleanup helpers can
 * find and delete only this run's leftovers, and (c) the reference
 * dataset (which uses fixed names) is never touched by cleanup.
 */
export const runId: string = process.env.E2E_RUN_ID || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

/** Wrap a name with the run-id namespace. */
export function tname(name: string): string {
  return `test-${runId}-${name}`;
}

/** Wrap an email with the run-id namespace. Returns `${user}+${runId}@example.com`. */
export function temail(user: string): string {
  return `${user}+${runId}@example.com`;
}
