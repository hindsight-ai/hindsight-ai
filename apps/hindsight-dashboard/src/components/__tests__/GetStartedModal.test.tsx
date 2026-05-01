import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import GetStartedModal from '../GetStartedModal';

describe('GetStartedModal', () => {
  it('does not render when closed', () => {
    const { container } = render(
      <GetStartedModal isOpen={false} onClose={jest.fn()} onAcknowledge={jest.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders Codex CLI instructions by default', () => {
    render(<GetStartedModal isOpen onClose={jest.fn()} onAcknowledge={jest.fn()} />);

    expect(screen.getByText('Get Started with Hindsight AI')).toBeInTheDocument();
    expect(screen.getByText('Prepare your Hindsight workspace')).toBeInTheDocument();
    expect(screen.getByText('Select your MCP client')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Codex CLI/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Configure Codex CLI')).toBeInTheDocument();
    const codexConfigOccurrences = screen.getAllByText('~/.config/codex.toml');
    expect(codexConfigOccurrences.length).toBeGreaterThan(0);
    expect(screen.getByText('Adjust your workflow')).toBeInTheDocument();
    expect(screen.getByText('Markdown File for Instructions')).toBeInTheDocument();
    expect(screen.getByText('AGENTS.md template')).toBeInTheDocument();
  });

  it('renders Claude Code instructions when selected', () => {
    render(<GetStartedModal isOpen onClose={jest.fn()} onAcknowledge={jest.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Claude Code/i }));
    expect(screen.getByText('Configure Claude Code')).toBeInTheDocument();
    expect(screen.getByText('claude mcp add-json command')).toBeInTheDocument();
    expect(screen.getByText('CLAUDE.md template')).toBeInTheDocument();
    expect(screen.queryByText('~/.config/codex.toml')).not.toBeInTheDocument();
  });

  // Transient close paths — must NOT mark the guide as seen. App.tsx
  // wires `onClose` to a handler that doesn't write localStorage.
  describe('transient close (does not mark seen)', () => {
    it('calls onClose when the close button is pressed', () => {
      const onClose = jest.fn();
      const onAcknowledge = jest.fn();
      render(<GetStartedModal isOpen onClose={onClose} onAcknowledge={onAcknowledge} />);

      fireEvent.click(screen.getByRole('button', { name: /close get started guide/i }));
      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onAcknowledge).not.toHaveBeenCalled();
    });

    it('calls onClose on Escape', () => {
      const onClose = jest.fn();
      const onAcknowledge = jest.fn();
      render(<GetStartedModal isOpen onClose={onClose} onAcknowledge={onAcknowledge} />);

      fireEvent.keyDown(window, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onAcknowledge).not.toHaveBeenCalled();
    });

    it('does not call onClose on Escape when the modal is closed', () => {
      const onClose = jest.fn();
      render(
        <GetStartedModal isOpen={false} onClose={onClose} onAcknowledge={jest.fn()} />,
      );

      fireEvent.keyDown(window, { key: 'Escape' });
      expect(onClose).not.toHaveBeenCalled();
    });

    it('calls onClose when the backdrop is clicked', () => {
      const onClose = jest.fn();
      const onAcknowledge = jest.fn();
      render(
        <GetStartedModal isOpen onClose={onClose} onAcknowledge={onAcknowledge} />,
      );

      // Modal renders via Portal, so query document.body. The backdrop
      // is the only aria-hidden div in the modal tree.
      const backdrop = document.body.querySelector('div[aria-hidden="true"]');
      expect(backdrop).not.toBeNull();
      fireEvent.click(backdrop!);
      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onAcknowledge).not.toHaveBeenCalled();
    });
  });

  // Acknowledged dismiss — the only path that marks the guide as seen.
  it('calls onAcknowledge (not onClose) when "Got it" is pressed', () => {
    const onClose = jest.fn();
    const onAcknowledge = jest.fn();
    render(<GetStartedModal isOpen onClose={onClose} onAcknowledge={onAcknowledge} />);

    fireEvent.click(screen.getByRole('button', { name: /got it/i }));
    expect(onAcknowledge).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });

  // Contract: the UI/UX audit skill (.claude/skills/ui-ux-audit/audit.mjs)
  // suppresses this modal between probes by clicking
  // `button[aria-label="Close get started guide"]`. Renaming the label
  // silently breaks every screenshot taken after that route. If the
  // label genuinely needs to change, update the suppressor in audit.mjs
  // in the same PR.
  it('exposes the exact aria-label the audit script depends on', () => {
    render(<GetStartedModal isOpen onClose={jest.fn()} onAcknowledge={jest.fn()} />);
    const btn = screen.getByLabelText('Close get started guide');
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe('BUTTON');
  });
});
