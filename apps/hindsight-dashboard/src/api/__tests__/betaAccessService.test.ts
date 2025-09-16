import betaAccessService from '../betaAccessService';
import { apiFetch } from '../http';

jest.mock('../http', () => ({
  apiFetch: jest.fn(),
}));

const mockApiFetch = apiFetch as jest.Mock;

describe('betaAccessService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns response when review succeeds', async () => {
    mockApiFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ success: true, message: 'ok' }),
    });

    const result = await betaAccessService.reviewWithToken('req-1', 'accepted', 'token-123');
    expect(result).toEqual({ success: true, message: 'ok' });
    expect(mockApiFetch).toHaveBeenCalledWith('/beta-access/review/req-1/token', expect.objectContaining({ method: 'POST' }));
  });

  it('throws error with detail when review fails', async () => {
    mockApiFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'invalid token' }),
    });

    await expect(betaAccessService.reviewWithToken('req-2', 'denied', 'token')).rejects.toThrow('invalid token');
  });
});
