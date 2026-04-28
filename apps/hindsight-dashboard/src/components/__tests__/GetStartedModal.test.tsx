import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import GetStartedModal from '../GetStartedModal';

describe('GetStartedModal', () => {
  it('does not render when closed', () => {
    const { container } = render(<GetStartedModal isOpen={false} onClose={jest.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders Codex CLI instructions by default', () => {
    render(<GetStartedModal isOpen onClose={jest.fn()} />);

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
    render(<GetStartedModal isOpen onClose={jest.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Claude Code/i }));
    expect(screen.getByText('Configure Claude Code')).toBeInTheDocument();
    expect(screen.getByText('claude mcp add-json command')).toBeInTheDocument();
    expect(screen.getByText('CLAUDE.md template')).toBeInTheDocument();
    expect(screen.queryByText('~/.config/codex.toml')).not.toBeInTheDocument();
  });

  it('calls onClose when the close button is pressed', () => {
    const handleClose = jest.fn();
    render(<GetStartedModal isOpen onClose={handleClose} />);

    fireEvent.click(screen.getByRole('button', { name: /close get started guide/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  // Contract: the UI/UX audit skill (.claude/skills/ui-ux-audit/audit.mjs)
  // suppresses this modal between probes by clicking
  // `button[aria-label="Close get started guide"]`. Renaming the label
  // silently breaks every screenshot taken after that route. If the
  // label genuinely needs to change, update the suppressor in audit.mjs
  // in the same PR.
  it('exposes the exact aria-label the audit script depends on', () => {
    render(<GetStartedModal isOpen onClose={jest.fn()} />);
    const btn = screen.getByLabelText('Close get started guide');
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe('BUTTON');
  });
});
