import type { Page } from '@playwright/test';

/**
 * User-provisioning helpers.
 *
 * Newly-created users in the backend default to `beta_access_status='not_requested'`.
 * The dashboard redirects such users to `/beta-access/request` instead of rendering
 * the main app, which means the rest of the journey can't run. Production gates
 * the dashboard behind beta-access approval; for tests we bypass that by
 * pre-approving users via the admin endpoint.
 *
 * Setup:
 *   1. CI / local env sets `BETA_ACCESS_ADMINS=e2e-admin@e2e.local` (the CI workflow
 *      already does this).
 *   2. The first call to `provisionUser` ensures the admin row exists and has its
 *      `is_beta_access_admin` flag computed from the env-var match.
 *   3. The same admin then PATCHes the test user's beta-access to 'accepted'.
 *
 * After provisioning, `asUser(page, email)` lands on the dashboard, not the
 * beta-access request page.
 */

const BACKEND = 'http://localhost:8000';
const ADMIN_EMAIL = 'e2e-admin@e2e.local';
// Must match the constant in `e2e/global-setup.ts` — both call /user-info as
// this admin and the backend matches them on email + external_subject.
const ADMIN_NAME = 'E2E Admin Account';

/**
 * Pre-approve a test user's beta access. Idempotent — safe to call from beforeEach.
 *
 * Flow:
 *   1. Hit /user-info as the user → triggers backend's get_or_create_user_for_request
 *   2. Capture user_id from the response
 *   3. Hit /beta-access/admin/users/{user_id} as the admin → flips status to 'accepted'
 *
 * Returns the provisioned user's ID for tests that need it.
 */
export async function provisionUser(
  page: Page,
  email: string,
  displayName?: string,
): Promise<string> {
  const userHeaders = {
    'x-auth-request-email': email,
    'x-auth-request-user': displayName || email,
  };
  const adminHeaders = {
    'x-auth-request-email': ADMIN_EMAIL,
    'x-auth-request-user': ADMIN_NAME,
  };

  // 1. Create user row + grab user_id.
  const userInfoResp = await page.request.get(`${BACKEND}/user-info`, {
    headers: userHeaders,
  });
  if (!userInfoResp.ok()) {
    throw new Error(
      `provisionUser: /user-info failed for ${email}: ${userInfoResp.status()} ${await userInfoResp.text()}`,
    );
  }
  const userInfo = await userInfoResp.json();
  const userId: string = userInfo.user_id;
  if (!userId) {
    throw new Error(`provisionUser: /user-info returned no user_id: ${JSON.stringify(userInfo)}`);
  }

  // Short-circuit if already accepted — keeps the helper idempotent + cheap.
  if (userInfo.beta_access_status === 'accepted') {
    return userId;
  }

  // 2. Bootstrap the admin user row (idempotent — first call creates it).
  const adminInfoResp = await page.request.get(`${BACKEND}/user-info`, {
    headers: adminHeaders,
  });
  if (!adminInfoResp.ok()) {
    throw new Error(
      `provisionUser: admin /user-info failed: ${adminInfoResp.status()} ${await adminInfoResp.text()}`,
    );
  }
  const adminInfo = await adminInfoResp.json();
  if (!adminInfo.beta_access_admin && !adminInfo.is_superadmin) {
    throw new Error(
      `provisionUser: admin email ${ADMIN_EMAIL} is not in BETA_ACCESS_ADMINS env var. ` +
        `Set BETA_ACCESS_ADMINS=${ADMIN_EMAIL} in your env / CI workflow.`,
    );
  }

  // 3. Approve the test user via the admin endpoint.
  const patchResp = await page.request.patch(
    `${BACKEND}/beta-access/admin/users/${userId}`,
    {
      headers: { ...adminHeaders, 'content-type': 'application/json' },
      data: { status: 'accepted' },
    },
  );
  if (!patchResp.ok()) {
    throw new Error(
      `provisionUser: admin PATCH failed for ${email}: ${patchResp.status()} ${await patchResp.text()}`,
    );
  }

  return userId;
}

/** Convenience: provision the admin itself (no-op approval, just creates the row). */
export async function ensureAdminProvisioned(page: Page): Promise<void> {
  const adminHeaders = {
    'x-auth-request-email': ADMIN_EMAIL,
    'x-auth-request-user': ADMIN_NAME,
  };
  await page.request.get(`${BACKEND}/user-info`, { headers: adminHeaders });
}
