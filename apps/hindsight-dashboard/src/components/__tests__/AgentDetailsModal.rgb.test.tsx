import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import AgentDetailsModal from '../AgentDetailsModal';
import memoryService from '../../api/memoryService';
import notificationService from '../../services/notificationService';

jest.mock('../../api/agentService');
jest.mock('../../api/memoryService');
jest.mock('../../services/notificationService');

const mockMemoryService = memoryService as jest.Mocked<typeof memoryService>;
const mockNotificationService = notificationService as jest.Mocked<typeof notificationService>;

const baseAgent = {
  agent_id: 'agent-123',
  agent_name: 'Test Agent',
  description: 'Agent description',
};

const renderModal = () => (
  render(
    <AgentDetailsModal
      isOpen
      onClose={() => {}}
      agent={baseAgent}
    />
  )
);

const originalClipboard = navigator.clipboard;
const originalExecCommand = document.execCommand;

describe('AgentDetailsModal clipboard RGB coverage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNotificationService.showSuccess.mockReturnValue(1 as any);
    mockNotificationService.showError.mockReturnValue(2 as any);
    mockMemoryService.getMemoryBlocks.mockResolvedValue({ total_items: 0 } as any);
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

  describe('RED Phase', () => {
    it('copies Agent ID using navigator.clipboard.writeText when available', async () => {
      const writeText = jest.fn().mockResolvedValue(undefined);

      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText },
      });

      renderModal();

      const copyButton = await screen.findByRole('button', { name: /copy/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledWith(baseAgent.agent_id);
      });
    });
  });

  describe('GREEN Phase', () => {
    it('shows success notification after successful clipboard write', async () => {
      const writeText = jest.fn().mockResolvedValue(undefined);

      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText },
      });

      renderModal();

      const copyButton = await screen.findByRole('button', { name: /copy/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockNotificationService.showSuccess).toHaveBeenCalledWith('Agent ID copied to clipboard');
      });
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });
  });

  describe('BLUE Phase', () => {
    it('falls back to document.execCommand when navigator.clipboard is unavailable', async () => {
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: undefined,
      });

      const execCommandMock = jest.fn().mockReturnValue(true);
      Object.defineProperty(document, 'execCommand', {
        configurable: true,
        value: execCommandMock,
      });

      renderModal();

      const copyButton = await screen.findByRole('button', { name: /copy/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(execCommandMock).toHaveBeenCalledWith('copy');
        expect(mockNotificationService.showSuccess).toHaveBeenCalledWith('Agent ID copied to clipboard');
      });
    });

    it('surfaces error notification when clipboard copy fails', async () => {
      const writeText = jest.fn().mockRejectedValue(new Error('no clipboard'));

      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText },
      });

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      renderModal();

      const copyButton = await screen.findByRole('button', { name: /copy/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockNotificationService.showError).toHaveBeenCalledWith('Failed to copy Agent ID. Please try again.');
      });
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });
});
