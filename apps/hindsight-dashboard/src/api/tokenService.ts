import { apiFetch } from './http';

export type TokenStatus = 'active' | 'revoked' | 'expired';

export interface Token {
  id: string;
  user_id: string;
  name: string;
  scopes: string[];
  organization_id?: string | null;
  status: TokenStatus;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
  prefix?: string | null;
  last_four?: string | null;
}

export interface TokenCreateRequest {
  name: string;
  scopes: string[];
  organization_id?: string;
  expires_at?: string; // ISO
}

export interface TokenCreateResponse extends Token {
  token: string; // one-time secret
}

const tokenService = {
  list: async (): Promise<Token[]> => {
    const resp = await apiFetch('/users/me/tokens');
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    return await resp.json();
  },

  create: async (data: TokenCreateRequest): Promise<TokenCreateResponse> => {
    const resp = await apiFetch('/users/me/tokens', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    return await resp.json();
  },

  revoke: async (id: string): Promise<void> => {
    const resp = await apiFetch(`/users/me/tokens/${id}`, { method: 'DELETE' });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${text}`);
    }
  },

  rotate: async (id: string): Promise<TokenCreateResponse> => {
    const resp = await apiFetch(`/users/me/tokens/${id}/rotate`, { method: 'POST' });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    return await resp.json();
  },

  update: async (id: string, data: { name?: string; expires_at?: string | null }): Promise<Token> => {
    const resp = await apiFetch(`/users/me/tokens/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    return await resp.json();
  },
};

export default tokenService;

