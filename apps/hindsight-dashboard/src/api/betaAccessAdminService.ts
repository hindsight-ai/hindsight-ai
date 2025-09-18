import { apiFetch } from './http';

export type BetaAccessManualStatus = 'accepted' | 'denied' | 'revoked' | 'not_requested';

export interface BetaAccessRequestSummary {
  id: string;
  email: string;
  status: string;
  requested_at: string | null;
  reviewed_at: string | null;
  reviewer_email: string | null;
}

export interface BetaAccessAdminUser {
  user_id: string;
  email: string;
  display_name?: string | null;
  beta_access_status: string;
  last_request?: BetaAccessRequestSummary | null;
}

const betaAccessAdminService = {
  async fetchUsers(): Promise<BetaAccessAdminUser[]> {
    const response = await apiFetch('/beta-access/admin/users');
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || 'Unable to fetch beta access users.');
    }
    const data = await response.json();
    return data.users ?? [];
  },

  async updateStatus(userId: string, status: BetaAccessManualStatus): Promise<BetaAccessAdminUser> {
    const response = await apiFetch(`/beta-access/admin/users/${userId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status }),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || 'Unable to update beta access status.');
    }

    const data = await response.json();
    return data.user;
  },
};

export default betaAccessAdminService;
