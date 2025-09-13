import organizationService from '../organizationService';

// Mock notificationService to verify 401 handling
jest.mock('../../services/notificationService', () => ({
  __esModule: true,
  default: { 
    show401Error: jest.fn(), 
    showWarning: jest.fn(),
    showError: jest.fn(),
    showSuccess: jest.fn(),
    showNetworkError: jest.fn(),
    showApiError: jest.fn()
  },
}));

describe('organizationService', () => {
  afterEach(() => { jest.restoreAllMocks(); });

  describe('getOrganizations', () => {
    test('fetches organizations successfully', async () => {
      const mockOrganizations = [{ id: 'org1', name: 'Test Org', is_active: true }];
      jest.spyOn(global, 'fetch').mockResolvedValue({ 
        ok: true, 
        json: async () => mockOrganizations 
      } as any);
      
      const result = await organizationService.getOrganizations();
      expect(result).toEqual(mockOrganizations);
    });

    test('handles HTTP errors correctly', async () => {
      jest.spyOn(global, 'fetch').mockResolvedValue({ 
        ok: false, 
        status: 401, 
        text: jest.fn().mockResolvedValue('Unauthorized') 
      } as any);
      
      await expect(organizationService.getOrganizations()).rejects.toThrow('HTTP error 401');
    });
  });

  describe('createOrganization', () => {
    test('creates organization successfully', async () => {
      const newOrgData = { name: 'New Organization' };
      const createdOrg = { id: 'org3', ...newOrgData, is_active: true };
      
      jest.spyOn(global, 'fetch').mockResolvedValue({ 
        ok: true, 
        json: async () => createdOrg 
      } as any);
      
      const result = await organizationService.createOrganization(newOrgData);
      expect(result).toEqual(createdOrg);
    });

    test('handles creation errors', async () => {
      const newOrgData = { name: 'Invalid Org' };
      jest.spyOn(global, 'fetch').mockResolvedValue({ 
        ok: false, 
        status: 400, 
        text: jest.fn().mockResolvedValue('Bad Request') 
      } as any);

      await expect(organizationService.createOrganization(newOrgData)).rejects.toThrow('HTTP error 400');
    });
  });

  describe('API endpoint validation', () => {
    test('calls organization endpoints correctly', async () => {
      const fetchSpy = jest.spyOn(global, 'fetch').mockResolvedValue({ 
        ok: true, 
        json: async () => [] 
      } as any);
      
      await organizationService.getOrganizations();
      
      const calledUrl = fetchSpy.mock.calls[0][0] as string;
      expect(calledUrl).toContain('/organizations/');
    });
  });

  describe('Invitation token forwarding', () => {
    test('acceptInvitation includes token in URL when provided', async () => {
      const fetchSpy = jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => ({}) } as any);
      await organizationService.acceptInvitation('org-123', 'inv-456', 'tok-789');
      const calls = fetchSpy.mock.calls;
      const calledUrl = calls[calls.length-1][0] as string;
      expect(calledUrl).toContain('/organizations/org-123/invitations/inv-456/accept');
      expect(calledUrl).toContain('token=tok-789');
    });

    test('declineInvitation includes token in URL when provided', async () => {
      const fetchSpy = jest.spyOn(global, 'fetch').mockResolvedValue({ ok: true, json: async () => ({}) } as any);
      await organizationService.declineInvitation('org-123', 'inv-456', 'tok-789');
      const calls = fetchSpy.mock.calls;
      const calledUrl = calls[calls.length-1][0] as string;
      expect(calledUrl).toContain('/organizations/org-123/invitations/inv-456/decline');
      expect(calledUrl).toContain('token=tok-789');
    });
  });
});
