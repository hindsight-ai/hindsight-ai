import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { provisionUser } from '../helpers/provision';
import { temail, tname, runId } from '../helpers/runId';

/**
 * Journey 9 — Org invitations + audit log. (RFC v3, umbrella #96, issue #109)
 *
 * Tests the invitation flow:
 *   - Owner sends invitation via API (creates pending row)
 *   - Invitee accepts (POST /accept as the invitee email — backend matches
 *     email to invitation, no token required)
 *   - Verify membership exists
 *   - Owner revokes a second pending invitation
 *   - Verify revoked invitation no longer in pending list
 *
 * **Scope adaptation:** the issue mentioned audit-log modal verification.
 * The audit-log UI surface (lifted in #80 to its own component, with
 * coverage from #91) is a separate journey concern. This test focuses
 * on the invitation lifecycle backend round-trips with multi-user
 * identity swap mid-test — the highest-value smoke for the invitation
 * flow itself.
 *
 * Tagged @full — runs on push to staging, not per-PR.
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 9 — Org invitations + accept flow @full', () => {
  test('owner invites, invitee accepts, owner revokes a second invite', async ({ page, request }) => {
    const ownerEmail = temail('inv-owner');
    const invitee1Email = temail('invitee-1');
    const invitee2Email = temail('invitee-2');

    await provisionUser(page, ownerEmail);
    await provisionUser(page, invitee1Email);
    await provisionUser(page, invitee2Email);

    const ownerHeaders = { 'x-auth-request-email': ownerEmail, 'x-auth-request-user': ownerEmail };
    const invitee1Headers = { 'x-auth-request-email': invitee1Email, 'x-auth-request-user': invitee1Email };

    // ── 1. Owner creates org ──────────────────────────────────────────────────
    const orgRes = await request.post(`${BACKEND}/organizations/`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: { name: tname('inv-org'), slug: `inv-org-${runId}` },
    });
    expect(orgRes.ok(), `org create failed: ${await orgRes.text()}`).toBe(true);
    const org = await orgRes.json();

    // ── 2. Owner sends two invitations ────────────────────────────────────────
    const inv1Res = await request.post(`${BACKEND}/organizations/${org.id}/invitations`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: { email: invitee1Email, role: 'editor' },
    });
    expect(inv1Res.ok(), `invitation 1 failed: ${await inv1Res.text()}`).toBe(true);
    const inv1 = await inv1Res.json();

    const inv2Res = await request.post(`${BACKEND}/organizations/${org.id}/invitations`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: { email: invitee2Email, role: 'viewer' },
    });
    expect(inv2Res.ok(), `invitation 2 failed: ${await inv2Res.text()}`).toBe(true);
    const inv2 = await inv2Res.json();

    // ── 3. Verify both invitations are pending ────────────────────────────────
    const pendingRes = await request.get(`${BACKEND}/organizations/${org.id}/invitations`, {
      headers: ownerHeaders,
    });
    const pendingData = await pendingRes.json();
    const pendingItems: Array<{ id: string; status: string }> = pendingData.items || pendingData;
    expect(pendingItems.find((i) => i.id === inv1.id)?.status?.toLowerCase()).toBe('pending');
    expect(pendingItems.find((i) => i.id === inv2.id)?.status?.toLowerCase()).toBe('pending');

    // ── 4. As invitee 1: accept the first invitation ──────────────────────────
    await asUser(page, invitee1Email);
    const acceptRes = await page.request.post(
      `${BACKEND}/organizations/${org.id}/invitations/${inv1.id}/accept`,
    );
    expect(acceptRes.ok(), `accept failed: ${await acceptRes.text()}`).toBe(true);

    // ── 5. Verify invitee 1 is now a member of the org ───────────────────────
    const aliceOrgsRes = await request.get(`${BACKEND}/organizations/`, { headers: invitee1Headers });
    const aliceOrgs = await aliceOrgsRes.json();
    const found = (aliceOrgs.items || aliceOrgs).find((o: any) => o.id === org.id);
    expect(found, `invitee 1 should be a member of ${org.id}`).toBeTruthy();

    // ── 6. As owner: revoke invitation 2 ──────────────────────────────────────
    await asUser(page, ownerEmail);
    const revokeRes = await page.request.delete(
      `${BACKEND}/organizations/${org.id}/invitations/${inv2.id}`,
    );
    expect(revokeRes.ok() || revokeRes.status() === 204, `revoke failed: ${await revokeRes.text()}`).toBe(
      true,
    );

    // ── 7. Verify revoked invitation reflects status ──────────────────────────
    const afterRes = await request.get(`${BACKEND}/organizations/${org.id}/invitations`, {
      headers: ownerHeaders,
      params: { status: 'all' },
    });
    const afterData = await afterRes.json();
    const afterItems: Array<{ id: string; status: string }> = afterData.items || afterData;
    const inv2Final = afterItems.find((i) => i.id === inv2.id);
    expect(
      inv2Final?.status?.toLowerCase() === 'revoked' || !inv2Final,
      'invitation 2 should be revoked or removed',
    ).toBeTruthy();

    // The accepted invitation 1 should now show as accepted.
    const inv1Final = afterItems.find((i) => i.id === inv1.id);
    expect(inv1Final?.status?.toLowerCase()).toBe('accepted');

    // ── 8. Cleanup: delete the org (cascades) ─────────────────────────────────
    await request.delete(`${BACKEND}/organizations/${org.id}`, { headers: ownerHeaders });
  });
});
