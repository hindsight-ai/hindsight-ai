import { apiFetch } from '../http';

describe('apiFetch scoping', () => {
  const originalFetch = global.fetch as any;
  const originalLocation = (global as any).window?.location;

  beforeEach(() => {
    // jsdom has window; ensure origin looks like dev
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost:3000/'),
      writable: true,
    });
    // Clear sessionStorage
    try { sessionStorage.clear(); } catch {}
    // Mock fetch
    (global as any).fetch = jest.fn(async (input: any, init?: any) => {
      return {
        ok: true,
        status: 200,
        headers: new Map([['content-type', 'application/json']]),
        json: async () => ({ ok: true })
      } as any;
    });
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    if (originalLocation) {
      Object.defineProperty(window, 'location', { value: originalLocation, writable: true });
    }
  });

  it('injects headers and query from session scope for writes', async () => {
    sessionStorage.setItem('ACTIVE_SCOPE', 'organization');
    sessionStorage.setItem('ACTIVE_ORG_ID', 'org-123');

    await apiFetch('/test-endpoint', { method: 'POST' });

    expect((global as any).fetch).toHaveBeenCalled();
    const [url, init] = (global as any).fetch.mock.calls[0];
    expect(String(url)).toContain('scope=organization');
    expect(String(url)).toContain('organization_id=org-123');
    const headers = new Headers((init as any).headers);
    expect(headers.get('X-Active-Scope')).toBe('organization');
    expect(headers.get('X-Organization-Id')).toBe('org-123');
  });

  it('scopeOverride wins over session scope', async () => {
    sessionStorage.setItem('ACTIVE_SCOPE', 'organization');
    sessionStorage.setItem('ACTIVE_ORG_ID', 'org-123');

    await apiFetch('/test-endpoint', { method: 'POST', scopeOverride: { scope: 'personal' } as any });

    const [url, init] = (global as any).fetch.mock.calls.pop();
    expect(String(url)).toContain('scope=personal');
    expect(String(url)).not.toContain('organization_id=');
    const headers = new Headers((init as any).headers);
    expect(headers.get('X-Active-Scope')).toBe('personal');
    expect(headers.get('X-Organization-Id')).toBeNull();
  });
});
