import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import AgentManagementPage from '../AgentManagementPage';
import agentService from '../../api/agentService';
import notificationService from '../../services/notificationService';
import usePageHeader from '../../hooks/usePageHeader';

jest.mock('../../api/agentService');
jest.mock('../../services/notificationService');
jest.mock('../AddAgentModal', () => () => null);
jest.mock('../AgentDetailsModal', () => () => null);
jest.mock('../RefreshIndicator', () => () => null);
jest.mock('../../hooks/usePageHeader');

const mockAgentService = agentService as jest.Mocked<typeof agentService>;
const mockNotificationService = notificationService as jest.Mocked<typeof notificationService>;
const mockUsePageHeader = usePageHeader as jest.MockedFunction<typeof usePageHeader>;

const baseAgent = {
  agent_id: 'agent-123',
  agent_name: 'Clipboard Tester',
  description: 'Clipboard test agent',
};

const renderPage = () => render(<AgentManagementPage />);

const originalClipboard = navigator.clipboard;
const originalExecCommand = document.execCommand;

const prepareAgentList = () => {
  mockAgentService.getAgents.mockResolvedValue({ items: [baseAgent] } as any);
};

describe('AgentManagementPage clipboard RBC coverage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    prepareAgentList();
    mockAgentService.deleteAgent.mockResolvedValue(undefined as any);
    mockUsePageHeader.mockReturnValue({
      setHeaderContent: jest.fn(),
      clearHeaderContent: jest.fn(),
      headerConfig: {},
    });
    mockNotificationService.showSuccess.mockReturnValue(1 as any);
    mockNotificationService.showError.mockReturnValue(2 as any);
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: originalClipboard,
    });
    if (originalExecCommand) {
      document.execCommand = originalExecCommand;
    } else {
      delete (document as any).execCommand;
    }
  });

  const findCopyButton = async () => {
    await waitFor(() => expect(mockAgentService.getAgents).toHaveBeenCalled());
    return screen.findByRole('button', { name: /copy agent id/i });
  };

  describe('RED Phase', () => {
    it('invokes navigator.clipboard.writeText when available', async () => {
      const writeText = jest.fn().mockResolvedValue(undefined);

      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText },
      });

      renderPage();

      const copyButton = await findCopyButton();
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledWith(baseAgent.agent_id);
      });
    });
  });

  describe('GREEN Phase', () => {
    it('shows success notification after successful clipboard copy', async () => {
      const writeText = jest.fn().mockResolvedValue(undefined);

      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText },
      });

      renderPage();

      const copyButton = await findCopyButton();
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockNotificationService.showSuccess).toHaveBeenCalledWith('Agent ID copied to clipboard');
      });
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });
  });

  describe('BLUE Phase', () => {
    it('falls back to document.execCommand when clipboard API is unavailable', async () => {
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: undefined,
      });

      const execCommandMock = jest.fn().mockReturnValue(true);
      Object.defineProperty(document, 'execCommand', {
        configurable: true,
        value: execCommandMock,
      });

      renderPage();

      const copyButton = await findCopyButton();
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(execCommandMock).toHaveBeenCalledWith('copy');
        expect(mockNotificationService.showSuccess).toHaveBeenCalledWith('Agent ID copied to clipboard');
      });
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });

    it('shows error notification when clipboard copy throws', async () => {
      const writeText = jest.fn().mockRejectedValue(new Error('clipboard failed'));

      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText },
      });

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      renderPage();

      const copyButton = await findCopyButton();
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockNotificationService.showError).toHaveBeenCalledWith('Failed to copy Agent ID. Please try again.');
      });
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });
});
