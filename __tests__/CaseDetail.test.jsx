import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { CaseDetail } from '../CaseProfileApp';

describe('CaseDetail', () => {
  it('shows details and triggers onBack', () => {
    const onBack = jest.fn();
    const caseData = { caseName: 'Example Case', caseNumber: '123' };
    render(<CaseDetail caseData={caseData} onBack={onBack} />);
    expect(screen.getByText('Example Case')).toBeInTheDocument();
    fireEvent.click(screen.getByText('← Back'));
    expect(onBack).toHaveBeenCalled();
  });
});
