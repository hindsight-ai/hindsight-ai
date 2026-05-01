import { request as createRequest, type FullConfig } from '@playwright/test';

/**
 * Playwright global setup — runs once before any worker starts.
 *
 * Provisions the designated E2E admin user (`e2e-admin@e2e.local`) so that
 * concurrent workers don't race to create the row simultaneously (which
 * caused `UniqueViolation` on `ix_users_email` and `uq_users_external_subject`
 * in the first CI run on PR #112). After this hook, workers can call
 * `provisionUser(...)` for their own test users without contending on the
 * admin row.
 *
 * The admin email must be in the backend's `BETA_ACCESS_ADMINS` env var so
 * that the row, once created, has `is_beta_access_admin=True` and can PATCH
 * other users' beta-access status.
 */

const BACKEND = 'http://localhost:8000';
const ADMIN_EMAIL = 'e2e-admin@e2e.local';
const ADMIN_NAME = 'E2E Admin Account';

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const ctx = await createRequest.newContext();
  try {
    // Hit /user-info as the admin email — first time creates the row;
    // subsequent (idempotent) calls just return the existing row.
    const resp = await ctx.get(`${BACKEND}/user-info`, {
      headers: {
        'x-auth-request-email': ADMIN_EMAIL,
        'x-auth-request-user': ADMIN_NAME,
      },
    });
    if (!resp.ok()) {
      const body = await resp.text();
      throw new Error(
        `[global-setup] failed to provision admin user (${ADMIN_EMAIL}): ` +
          `${resp.status()} ${body}\n\n` +
          `Verify the backend is reachable at ${BACKEND} and ` +
          `BETA_ACCESS_ADMINS env var includes ${ADMIN_EMAIL}.`,
      );
    }
    const info = await resp.json();
    if (!info.beta_access_admin && !info.is_superadmin) {
      throw new Error(
        `[global-setup] admin user ${ADMIN_EMAIL} was created but lacks ` +
          `beta_access_admin / is_superadmin. ` +
          `Backend likely doesn't have BETA_ACCESS_ADMINS=${ADMIN_EMAIL} set.`,
      );
    }
    // eslint-disable-next-line no-console
    console.log(
      `[global-setup] admin provisioned: ${ADMIN_EMAIL} (id=${info.user_id}, beta_admin=${info.beta_access_admin})`,
    );
  } finally {
    await ctx.dispose();
  }
}
