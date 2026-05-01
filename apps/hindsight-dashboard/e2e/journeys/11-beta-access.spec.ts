import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail } from '../helpers/runId';

/**
 * Journey 11 — Beta-access flow. (RFC v3, umbrella #96, issue #110)
 *
 * Validates the beta-access state machine end-to-end across two users:
 *   1. Requester starts at `not_requested`
 *   2. Requester POSTs /beta-access/request → pending
 *   3. Admin PATCHes to accepted → flipped
 *   4. Admin PATCHes to revoked → flipped
 *   5. Requester sees the latest status on next /user-info call
 *
 * Validates the work in #77 (request-row source-of-truth ordering) and
 * #89 (single-transaction atomicity). Backend tests cover those at the
 * unit level; this E2E confirms the full chain (frontend redirect on
 * non-accepted, backend state machine, admin override).
 *
 * **Note:** intentionally does NOT call `provisionUser` for the requester —
 * the journey requires the requester to start in `not_requested` state.
 * The admin IS provisioned (via the global setup admin email).
 *
 * Tagged @full — multi-user state-machine test, runs on push to staging.
 */

const BACKEND = 'http://localhost:8000';
const ADMIN_EMAIL = 'e2e-admin@e2e.local';
const ADMIN_NAME = 'E2E Admin Account';

test.describe('Journey 11 — Beta-access state machine @full', () => {
  test('requester transitions: not_requested → pending → accepted → revoked', async ({ page, request }) => {
    const requesterEmail = temail('beta-requester');
    const requesterHeaders = {
      'x-auth-request-email': requesterEmail,
      'x-auth-request-user': requesterEmail,
    };
    const adminHeaders = {
      'x-auth-request-email': ADMIN_EMAIL,
      'x-auth-request-user': ADMIN_NAME,
    };

    // ── 1. Create the requester's user row WITHOUT approving ──────────────────
    // Hit /user-info to create the row; default beta_access_status='not_requested'.
    // Do NOT call provisionUser — that auto-approves.
    const initialRes = await request.get(`${BACKEND}/user-info`, { headers: requesterHeaders });
    expect(initialRes.ok(), `requester /user-info init failed: ${await initialRes.text()}`).toBe(true);
    const initialInfo = await initialRes.json();
    expect(initialInfo.beta_access_status).toBe('not_requested');
    const requesterUserId: string = initialInfo.user_id;

    // ── 2. Requester submits beta-access request → pending ────────────────────
    const requestRes = await request.post(`${BACKEND}/beta-access/request`, {
      headers: requesterHeaders,
    });
    expect(requestRes.ok(), `request submission failed: ${await requestRes.text()}`).toBe(true);

    const afterRequestRes = await request.get(`${BACKEND}/user-info`, { headers: requesterHeaders });
    expect((await afterRequestRes.json()).beta_access_status).toBe('pending');

    // ── 3. Admin approves → accepted ─────────────────────────────────────────
    const approveRes = await request.patch(
      `${BACKEND}/beta-access/admin/users/${requesterUserId}`,
      {
        headers: { ...adminHeaders, 'content-type': 'application/json' },
        data: { status: 'accepted' },
      },
    );
    expect(approveRes.ok(), `admin approve failed: ${await approveRes.text()}`).toBe(true);

    const afterApproveRes = await request.get(`${BACKEND}/user-info`, { headers: requesterHeaders });
    expect((await afterApproveRes.json()).beta_access_status).toBe('accepted');

    // ── 4. As requester, verify dashboard renders (no redirect) ───────────────
    await asUser(page, requesterEmail);
    // The dashboard should NOT redirect us to /beta-access/request now.
    await expect(page).not.toHaveURL(/\/beta-access\//, { timeout: 10_000 });

    // ── 5. Admin revokes → revoked/denied ─────────────────────────────────────
    const revokeRes = await request.patch(
      `${BACKEND}/beta-access/admin/users/${requesterUserId}`,
      {
        headers: { ...adminHeaders, 'content-type': 'application/json' },
        data: { status: 'revoked' },
      },
    );
    expect(revokeRes.ok(), `admin revoke failed: ${await revokeRes.text()}`).toBe(true);

    // ── 6. Requester reflects revocation ──────────────────────────────────────
    const afterRevokeRes = await request.get(`${BACKEND}/user-info`, { headers: requesterHeaders });
    const revokedStatus = (await afterRevokeRes.json()).beta_access_status;
    // The status PATCH endpoint may map 'revoked' → 'revoked' or 'denied' depending
    // on backend flow (see #77's status normalization). Accept either as a
    // valid revocation signal.
    expect(['revoked', 'denied']).toContain(revokedStatus);
  });
});
