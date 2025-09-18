import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PaginationControls from '../PaginationControls';

describe('PaginationControls', () => {
  const setup = (overrides = {}) => {
    const props = {
      pagination: { page: 2, per_page: 10, total_pages: 5, total_items: 100 },
      onPageChange: jest.fn(),
      onPerPageChange: jest.fn(),
      onPageInputChange: jest.fn(),
      pageInputValue: 2,
      onPageInputKeyPress: jest.fn(),
      onPageInputBlur: jest.fn(),
      ...overrides,
    };
    render(<PaginationControls {...props} />);
    return props;
  };

  test('calls onPageChange for navigation buttons', () => {
    const props = setup();
    fireEvent.click(screen.getByTitle('First Page'));
    expect(props.onPageChange).toHaveBeenCalledWith(1);
    fireEvent.click(screen.getByTitle('Previous Page'));
    expect(props.onPageChange).toHaveBeenCalledWith(1);
    fireEvent.click(screen.getByTitle('Next Page'));
    expect(props.onPageChange).toHaveBeenCalledWith(3);
    fireEvent.click(screen.getByTitle('Last Page'));
    expect(props.onPageChange).toHaveBeenCalledWith(5);
  });

  test('calls +/-10 page jumps when enabled', () => {
    const props = setup({ pagination: { page: 20, per_page: 10, total_pages: 50, total_items: 500 }, pageInputValue: 20 });
    fireEvent.click(screen.getByTitle('Previous 10 Pages'));
    expect(props.onPageChange).toHaveBeenCalledWith(10);
    fireEvent.click(screen.getByTitle('Next 10 Pages'));
    expect(props.onPageChange).toHaveBeenCalledWith(30);
  });

  test('per-page select triggers onPerPageChange', () => {
    const props = setup();
    const select = screen.getByLabelText('Items per page:');
    fireEvent.change(select, { target: { value: '20' } });
    expect(props.onPerPageChange).toHaveBeenCalled();
  });

  test('page input binds value and triggers events', () => {
    const props = setup({ pageInputValue: 3 });
    const input = screen.getByLabelText(/Current page/);
    expect(input.value).toBe('3');
    fireEvent.change(input, { target: { value: '4' } });
    expect(props.onPageInputChange).toHaveBeenCalled();
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });
    expect(props.onPageInputKeyPress).toHaveBeenCalled();
    fireEvent.blur(input);
    expect(props.onPageInputBlur).toHaveBeenCalled();
  });

  test('disables buttons appropriately on first/last page', () => {
    setup({ pagination: { page: 1, per_page: 10, total_pages: 1, total_items: 5 } });
    expect(screen.getByTitle('First Page')).toBeDisabled();
    expect(screen.getByTitle('Previous Page')).toBeDisabled();
    expect(screen.getByTitle('Next Page')).toBeDisabled();
    expect(screen.getByTitle('Last Page')).toBeDisabled();
  });
});
