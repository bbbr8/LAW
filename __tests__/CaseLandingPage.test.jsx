import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { CaseLandingPage } from '../CaseProfileApp';

describe('CaseLandingPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('calls onNew when New Case button clicked', () => {
    const onNew = jest.fn();
    render(<CaseLandingPage onNew={onNew} onOpen={jest.fn()} />);
    fireEvent.click(screen.getByText('+ New Case'));
    expect(onNew).toHaveBeenCalled();
  });

  it('loads cases and calls onOpen when a case is clicked', async () => {
    const cases = [{ id: '1', caseName: 'Test Case' }];
    localStorage.setItem('bj_case_profiles_v1', JSON.stringify(cases));
    const onOpen = jest.fn();
    render(<CaseLandingPage onNew={jest.fn()} onOpen={onOpen} />);
    const caseCard = await screen.findByText('Test Case');
    fireEvent.click(caseCard);
    expect(onOpen).toHaveBeenCalledWith(cases[0]);
  });
});
