import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CaseProfileCreator } from '../CaseProfileApp';

describe('CaseProfileCreator', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('creates a profile and calls onSaved', async () => {
    const onSaved = jest.fn();
    render(<CaseProfileCreator onSaved={onSaved} onCancel={jest.fn()} />);
    fireEvent.change(screen.getByLabelText(/Case name/i), { target: { value: 'New Case' } });
    fireEvent.click(screen.getByText('Continue'));
    fireEvent.click(screen.getByText('Continue'));
    fireEvent.click(screen.getByText('Continue'));
    fireEvent.click(screen.getByText('Create profile'));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    const saved = JSON.parse(localStorage.getItem('bj_case_profiles_v1'));
    expect(saved[0].caseName).toBe('New Case');
  });
});
