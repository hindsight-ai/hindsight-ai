import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { jest } from '@jest/globals';

import Button from '../Button';

describe('Button (primitive)', () => {
  it('renders the primary variant by default with the canonical token', () => {
    render(<Button>Save</Button>);
    const btn = screen.getByRole('button', { name: 'Save' });
    expect(btn).toBeInTheDocument();
    // Token guarantees the same primary styling for every consumer. If
    // these classes drift, H1/H2 buttons silently desynchronise.
    expect(btn).toHaveClass('bg-blue-600');
    expect(btn).toHaveClass('text-white');
    expect(btn).toHaveClass('hover:bg-blue-700');
  });

  it('defaults type to "button" so it does not submit forms by accident', () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('forwards onClick and disabled', () => {
    const onClick = jest.fn();
    render(<Button onClick={onClick} disabled>Save</Button>);
    const btn = screen.getByRole('button');
    fireEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
    expect(btn).toBeDisabled();
  });

  it('appends consumer-supplied className after the variant classes', () => {
    render(<Button className="ml-auto">Save</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toHaveClass('bg-blue-600');
    expect(btn).toHaveClass('ml-auto');
  });

  it('renders the secondary variant with the outlined token', () => {
    render(<Button variant="secondary">Cancel</Button>);
    const btn = screen.getByRole('button', { name: 'Cancel' });
    expect(btn).toHaveClass('border');
    expect(btn).toHaveClass('border-gray-300');
    expect(btn).toHaveClass('bg-white');
    expect(btn).toHaveClass('text-gray-700');
    // Secondary must NOT carry the primary's filled-blue styling.
    expect(btn).not.toHaveClass('bg-blue-600');
  });
});
