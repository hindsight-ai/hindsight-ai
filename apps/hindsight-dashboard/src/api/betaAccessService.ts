import { apiFetch } from './http';

export type BetaReviewDecision = 'accepted' | 'denied';

export interface BetaReviewResponse {
  success: boolean;
  message?: string;
}

const betaAccessService = {
  async reviewWithToken(requestId: string, decision: BetaReviewDecision, token: string): Promise<BetaReviewResponse> {
    const response = await apiFetch(`/beta-access/review/${requestId}/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      noScope: true,
      body: JSON.stringify({ decision, token }),
    });

    let data: any = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      const detail = data?.detail || data?.message || 'Unable to update beta access request.';
      const error = new Error(detail);
      (error as any).status = response.status;
      throw error;
    }

    return data as BetaReviewResponse;
  },
};

export default betaAccessService;
