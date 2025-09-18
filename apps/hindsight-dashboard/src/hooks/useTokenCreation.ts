import { useState } from 'react';
import tokenService from '../api/tokenService';
import notificationService from '../services/notificationService';

type CreatePayload = { name: string; scopes: string[]; organization_id?: string; expires_at?: string };

export default function useTokenCreation() {
  const [loading, setLoading] = useState(false);
  const [oneTimeSecret, setOneTimeSecret] = useState<string | null>(null);
  const [lastCreated, setLastCreated] = useState<any | null>(null);

  const create = async (payload: CreatePayload) => {
    setLoading(true);
    try {
      const created = await tokenService.create(payload);
      setOneTimeSecret(created.token);
      setLastCreated(created);
      notificationService.showSuccess('API token created');
      return created;
    } catch (err: any) {
      notificationService.showApiError?.(parseInt(err?.message?.match(/HTTP (\d+)/)?.[1] || '500', 10), err?.message, 'create token');
      notificationService.showError('Failed to create token');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const clearOneTime = () => setOneTimeSecret(null);

  return { create, loading, oneTimeSecret, lastCreated, clearOneTime };
}
