import { test, expect } from '@playwright/test';
import { asUser } from '../helpers/auth';
import { autoAcceptConfirm } from '../helpers/dialogs';
import { provisionUser } from '../helpers/provision';
import { temail, tname, runId } from '../helpers/runId';

/**
 * Journey 8 — Org admin members (multi-user). (RFC v3, umbrella #96, issue #101)
 *
 * The first multi-user smoke journey. Tests:
 *   - Owner sees newly-added member in members list
 *   - Owner can change member role via UI dropdown
 *   - Owner can remove member (window.confirm-gated)
 *   - Removed member's org disappears from their org list
 *
 * **Scope:** uses API for setup (create org + add member directly) so the
 * test exercises member-management UI without going through the full
 * invitation accept/decline flow. That flow has its own dedicated journey
 * (#109 / journey 9) at the @full tier. Direct member-add is a real UI path
 * for superadmins; here we use the API to bypass invitation latency.
 *
 * Tagged @smoke. Multi-user via mid-test `asUser` swap (round-2 F1 path).
 */

const BACKEND = 'http://localhost:8000';

test.describe('Journey 8 — Org admin members (multi-user) @smoke', () => {
  test('owner adds, role-changes, and removes a member; member sees changes', async ({ page, request }) => {
    autoAcceptConfirm(page);

    const ownerEmail = temail('org-owner');
    const aliceEmail = temail('alice-member');
    const orgName = tname('test-org');

    // Provision both users (auto-approve beta access).
    await provisionUser(page, ownerEmail);
    await provisionUser(page, aliceEmail);

    const ownerHeaders = { 'x-auth-request-email': ownerEmail, 'x-auth-request-user': ownerEmail };

    // ── 1. Setup via API: create org + add alice as editor ────────────────────
    const orgResp = await request.post(`${BACKEND}/organizations/`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: { name: orgName, slug: `test-org-${runId}` },
    });
    expect(orgResp.ok(), `org creation failed: ${await orgResp.text()}`).toBe(true);
    const org = await orgResp.json();

    const addMemberResp = await request.post(`${BACKEND}/organizations/${org.id}/members`, {
      headers: { ...ownerHeaders, 'content-type': 'application/json' },
      data: { email: aliceEmail, role: 'editor' },
    });
    expect(addMemberResp.ok(), `add-member failed: ${await addMemberResp.text()}`).toBe(true);

    // ── 2. As owner: open Manage Organizations modal, verify alice listed ─────
    await asUser(page, ownerEmail);

    // Click the avatar button (first letter of email, in chrome).
    // It's the only visible-clickable affordance that opens the user dropdown.
    await page.locator('button').filter({ hasText: ownerEmail.charAt(0).toUpperCase() }).first().click();
    await page.getByText(/manage organizations/i).click();

    // Modal opens with the org list. Click our org.
    await page.getByText(orgName).first().click();

    // Members list should show alice's email.
    await expect(page.getByText(aliceEmail, { exact: false })).toBeVisible({ timeout: 10_000 });

    // ── 3. Change alice's role from editor → viewer via UI ────────────────────
    // Each member row has a role <select>. Find alice's row.
    const aliceRow = page.locator('tr,div,li').filter({ hasText: aliceEmail }).first();
    const roleSelect = aliceRow.locator('select').first();
    if (await roleSelect.count()) {
      await roleSelect.selectOption('viewer');
    } else {
      // Fallback: any select dropdown that follows alice's email
      throw new Error('role select not found in alice row');
    }

    // Verify via API (UI may not visibly re-render the role text immediately)
    const verifyResp = await request.get(`${BACKEND}/organizations/${org.id}/members`, { headers: ownerHeaders });
    const members: Array<{ email: string; role: string }> = (await verifyResp.json()).items || (await verifyResp.json());
    // Re-fetch since we already consumed
    const verifyResp2 = await request.get(`${BACKEND}/organizations/${org.id}/members`, { headers: ownerHeaders });
    const data = await verifyResp2.json();
    const alice = (data.items || data).find((m: any) => m.email === aliceEmail);
    expect(alice?.role).toBe('viewer');

    // ── 4. Remove alice from the org via UI ───────────────────────────────────
    const removeBtn = aliceRow.getByRole('button', { name: /^remove$/i }).first();
    if (await removeBtn.count()) {
      await removeBtn.click();
    } else {
      // Fallback selector
      await aliceRow.locator('button').filter({ hasText: /remove|delete/i }).first().click();
    }
    // window.confirm is auto-accepted by autoAcceptConfirm.

    // Verify removal via API (UI updates may need a refresh).
    await page.waitForTimeout(500);
    const afterResp = await request.get(`${BACKEND}/organizations/${org.id}/members`, { headers: ownerHeaders });
    const after = await afterResp.json();
    const stillMember = (after.items || after).find((m: any) => m.email === aliceEmail);
    expect(stillMember).toBeFalsy();

    // ── 5. As alice: verify the org is no longer in her list ──────────────────
    await asUser(page, aliceEmail);
    const aliceHeaders = { 'x-auth-request-email': aliceEmail, 'x-auth-request-user': aliceEmail };
    const aliceOrgsResp = await request.get(`${BACKEND}/organizations/`, { headers: aliceHeaders });
    const aliceOrgs = await aliceOrgsResp.json();
    const stillVisible = (aliceOrgs.items || aliceOrgs).find((o: any) => o.id === org.id);
    expect(stillVisible).toBeFalsy();

    // ── 6. Cleanup ────────────────────────────────────────────────────────────
    await request.delete(`${BACKEND}/organizations/${org.id}`, { headers: ownerHeaders });
  });
});
