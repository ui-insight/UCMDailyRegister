import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getSubmission } from '../../api/submissions';
import type { Submission } from '../../types/submission';
import OriginalEntryPanel from './OriginalEntryPanel';

vi.mock('../../api/submissions', () => ({
  getSubmission: vi.fn(),
}));

const getSubmissionMock = vi.mocked(getSubmission);

function makeSubmission(overrides: Partial<Submission> = {}): Submission {
  return {
    Id: 'submission-1',
    Category: 'employee_announcement',
    Target_Newsletter: 'both',
    Original_Headline: 'Synthetic campus forum',
    Original_Body: 'Original forum details from the submitter.',
    Submitter_Name: 'Test Submitter',
    Submitter_Email: 'tester@example.edu',
    Submitter_Notes: null,
    Assigned_Editor: null,
    Editorial_Notes: null,
    Survey_End_Date: null,
    Has_Image: false,
    Image_Path: null,
    Status: 'approved',
    Show_In_SLC_Calendar: false,
    Event_Classification: null,
    Approved_Version_Id: null,
    Working_Version_Id: null,
    Staff_Revision_Id: null,
    Created_At: '2026-04-28T12:00:00Z',
    Updated_At: '2026-04-28T12:00:00Z',
    Links: [
      { Id: 'link-1', Url: 'https://example.edu/forum', Anchor_Text: 'Register now', Display_Order: 0 },
    ],
    Schedule_Requests: [
      {
        Id: 'schedule-1',
        Requested_Date: '2026-05-05',
        Second_Requested_Date: '2026-05-06',
        Repeat_Count: 1,
        Repeat_Note: null,
        Is_Flexible: false,
        Flexible_Deadline: null,
        Recurrence_Type: 'weekly',
        Recurrence_Interval: 1,
        Recurrence_End_Date: '2026-05-26',
        Repeats_Indefinitely: false,
        Excluded_Dates: ['2026-05-12'],
        Occurrence_Dates: ['2026-05-05', '2026-05-19', '2026-05-26'],
      },
    ],
    Occurrence_Dates: ['2026-05-05', '2026-05-19', '2026-05-26'],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('OriginalEntryPanel', () => {
  it('stays collapsed and does not fetch until opened', () => {
    render(<OriginalEntryPanel submissionId="submission-1" />);

    const toggle = screen.getByRole('button', { name: 'View original entry' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('region', { name: 'Original entry' })).not.toBeInTheDocument();
    expect(getSubmissionMock).not.toHaveBeenCalled();
  });

  it('shows the original text, links and requested schedule when opened by keyboard', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission());
    render(<OriginalEntryPanel submissionId="submission-1" />);

    await user.tab();
    expect(screen.getByRole('button', { name: 'View original entry' })).toHaveFocus();
    await user.keyboard('{Enter}');

    const region = await screen.findByRole('region', { name: 'Original entry' });
    expect(await within(region).findByText('Synthetic campus forum')).toBeInTheDocument();
    expect(within(region).getByText('Original forum details from the submitter.')).toBeInTheDocument();
    expect(within(region).getByText('https://example.edu/forum')).toBeInTheDocument();
    expect(within(region).getByText(/Register now/)).toBeInTheDocument();
    expect(within(region).getByText('Daily Register:')).toBeInTheDocument();
    expect(within(region).getByText('My UI:')).toBeInTheDocument();
    expect(within(region).getByText(/Weekly/)).toBeInTheDocument();
    expect(within(region).getByText(/Ends:/)).toBeInTheDocument();
    expect(within(region).getByText('Skips: 2026-05-12')).toBeInTheDocument();
    expect(getSubmissionMock).toHaveBeenCalledWith('submission-1');

    const toggle = screen.getByRole('button', { name: 'Hide original entry' });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await user.click(toggle);
    await user.click(screen.getByRole('button', { name: 'View original entry' }));
    expect(getSubmissionMock).toHaveBeenCalledTimes(1);
  });

  it('links to the full submission in a new tab', () => {
    render(<OriginalEntryPanel submissionId="submission-1" />);

    const link = screen.getByRole('link', { name: /Open full submission/ });
    expect(link).toHaveAttribute('href', '/edit/submission-1');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('reports a load failure and retries', async () => {
    const user = userEvent.setup();
    getSubmissionMock
      .mockRejectedValueOnce(new Error('Submission not found'))
      .mockResolvedValueOnce(makeSubmission({ Schedule_Requests: [] }));
    render(<OriginalEntryPanel submissionId="submission-1" />);

    await user.click(screen.getByRole('button', { name: 'View original entry' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Submission not found');

    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('No dates requested')).toBeInTheDocument();
  });
});
