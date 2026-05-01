import { request as createRequest, type FullConfig } from '@playwright/test';
import { seedReferenceDataset, REFERENCE_OWNER_EMAIL, REFERENCE_OWNER_NAME } from './fixtures/referenceDataset';

/**
 * Playwright global setup — runs once before any worker starts.
 *
 * Two responsibilities:
 *
 * 1. Provision the designated E2E admin user (`e2e-admin@e2e.local`) so
 *    that concurrent workers don't race to create the row (which caused
 *    `UniqueViolation` on `ix_users_email` + `uq_users_external_subject`
 *    in PR #112's first CI run).
 *
 * 2. Seed the search-journey reference dataset (50 memory blocks under a
 *    fixed agent owned by `e2e-reference-owner@e2e.local`). Idempotent:
 *    re-runs only when block count drifts.
 *
 * Both designated admin/owner emails must be in the backend's
 * `BETA_ACCESS_ADMINS` env var so beta-access doesn't gate them.
 */

const BACKEND = 'http://localhost:8000';
const ADMIN_EMAIL = 'e2e-admin@e2e.local';
const ADMIN_NAME = 'E2E Admin Account';

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const ctx = await createRequest.newContext();
  try {
    // ── 1. Provision the admin user ──────────────────────────────────────────
    const adminResp = await ctx.get(`${BACKEND}/user-info`, {
      headers: {
        'x-auth-request-email': ADMIN_EMAIL,
        'x-auth-request-user': ADMIN_NAME,
      },
    });
    if (!adminResp.ok()) {
      throw new Error(
        `[global-setup] failed to provision admin user (${ADMIN_EMAIL}): ` +
          `${adminResp.status()} ${await adminResp.text()}\n\n` +
          `Verify the backend is reachable at ${BACKEND} and ` +
          `BETA_ACCESS_ADMINS env var includes ${ADMIN_EMAIL}.`,
      );
    }
    const adminInfo = await adminResp.json();
    if (!adminInfo.beta_access_admin && !adminInfo.is_superadmin) {
      throw new Error(
        `[global-setup] admin user ${ADMIN_EMAIL} was created but lacks ` +
          `beta_access_admin / is_superadmin. ` +
          `Backend likely doesn't have BETA_ACCESS_ADMINS=${ADMIN_EMAIL}.`,
      );
    }
    // eslint-disable-next-line no-console
    console.log(`[global-setup] admin provisioned: ${ADMIN_EMAIL} (id=${adminInfo.user_id})`);

    // ── 2. Provision the reference owner + verify beta-admin ─────────────────
    const refResp = await ctx.get(`${BACKEND}/user-info`, {
      headers: {
        'x-auth-request-email': REFERENCE_OWNER_EMAIL,
        'x-auth-request-user': REFERENCE_OWNER_NAME,
      },
    });
    if (!refResp.ok()) {
      throw new Error(
        `[global-setup] failed to provision reference owner (${REFERENCE_OWNER_EMAIL}): ` +
          `${refResp.status()} ${await refResp.text()}`,
      );
    }
    const refInfo = await refResp.json();
    if (!refInfo.beta_access_admin && !refInfo.is_superadmin) {
      throw new Error(
        `[global-setup] reference owner ${REFERENCE_OWNER_EMAIL} lacks beta-access. ` +
          `Add it to BETA_ACCESS_ADMINS env var.`,
      );
    }

    // Beta-admin status only grants the ability to APPROVE other users — the
    // reference owner's own beta_access_status is still 'not_requested' which
    // would redirect them to /beta-access/request when they try to view the
    // dashboard. PATCH them to 'accepted' so they can access their own
    // reference dataset for search journey assertions.
    if (refInfo.beta_access_status !== 'accepted') {
      const patchResp = await ctx.patch(
        `${BACKEND}/beta-access/admin/users/${refInfo.user_id}`,
        {
          headers: {
            'x-auth-request-email': ADMIN_EMAIL,
            'x-auth-request-user': ADMIN_NAME,
            'content-type': 'application/json',
          },
          data: { status: 'accepted' },
        },
      );
      if (!patchResp.ok()) {
        throw new Error(
          `[global-setup] failed to approve reference owner beta-access: ` +
            `${patchResp.status()} ${await patchResp.text()}`,
        );
      }
    }

    // ── 3. Seed the reference dataset (idempotent) ───────────────────────────
    const result = await seedReferenceDataset(ctx);
    // eslint-disable-next-line no-console
    console.log(
      `[global-setup] reference dataset ready: agent=${result.agentId}, blocks=${result.blockCount}`,
    );
  } finally {
    await ctx.dispose();
  }
}
