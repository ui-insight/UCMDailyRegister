import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DataGovernancePage from './DataGovernancePage';

describe('DataGovernancePage', () => {
  it('marks APM 30.11 tiers as proposed pending Data Owner confirmation', () => {
    render(<DataGovernancePage />);
    expect(screen.getByText(/APM 30\.11 tiers \(Low, Moderate, High\) are proposed — Data Owner to confirm \(#176\)/))
      .toBeInTheDocument();
  });

  it('shows the proposed APM 30.11 tier beside the local label for tables and columns', () => {
    render(<DataGovernancePage />);
    // The submissions table is expanded by default and holds submitter contact details.
    const submissionsHeader = screen.getByText('submissions', { selector: 'span' }).closest('button');
    expect(submissionsHeader).not.toBeNull();
    expect(within(submissionsHeader as HTMLElement).getByText('APM 30.11: Moderate (proposed)')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'APM 30.11 (proposed)' })).toBeInTheDocument();

    const emailRow = screen.getByText('Submitter_Email').closest('tr');
    expect(emailRow).not.toBeNull();
    expect(within(emailRow as HTMLElement).getByText('Confidential')).toBeInTheDocument();
    expect(within(emailRow as HTMLElement).getByText('Moderate')).toBeInTheDocument();

    const categoryRow = screen.getByText('Category').closest('tr');
    expect(within(categoryRow as HTMLElement).getByText('Low')).toBeInTheDocument();
  });
});
