import { apiFetch } from './http';

export interface OrganizationSummary {
  id: string;
  name: string;
  slug?: string;
  role?: string;
}

const orgsService = {
  listOrganizations: async (): Promise<OrganizationSummary[]> => {
    const resp = await apiFetch('/organizations/', { ensureTrailingSlash: true });
    if (!resp.ok) {
      if (resp.status === 401) return [];
      throw new Error(`HTTP ${resp.status}`);
    }
    return resp.json();
  },
};

export default orgsService;
