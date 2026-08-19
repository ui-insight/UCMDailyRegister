import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getValidDates } from '../../api/schedule';
import type { Submission, SubmissionScheduleRequest } from '../../types/submission';
import SubmissionMeta from './SubmissionMeta';

vi.mock('../../api/schedule', () => ({
  getValidDates: vi.fn(),
}));

const getValidDatesMock = vi.mocked(getValidDates);

function makeScheduleRequest(
  overrides: Partial<SubmissionScheduleRequest> = {},
): SubmissionScheduleRequest {
  return {
    Id: 'schedule-1',
    Requested_Date: '2026-05-05',
    Second_Requested_Date: null,
    Repeat_Count: 1,
    Repeat_Note: null,
    Is_Flexible: false,
    Flexible_Deadline: null,
    Recurrence_Type: 'once',
    Recurrence_Interval: 1,
    Recurrence_End_Date: null,
    Excluded_Dates: [],
    Occurrence_Dates: ['2026-05-05'],
    ...overrides,
  };
}

function makeSubmission(overrides: Partial<Submission> = {}): Submission {
  return {
    Id: 'submission-1',
    Category: 'employee_announcement',
    Target_Newsletter: 'tdr',
    Original_Headline: 'Campus forum',
    Original_Body: 'Forum details.',
    Submitter_Name: 'Jane Submitter',
    Submitter_Email: 'jane@example.edu',
    Submitter_Notes: null,
    Assigned_Editor: null,
    Editorial_Notes: null,
    Survey_End_Date: null,
    Has_Image: false,
    Image_Path: null,
    Status: 'approved',
    Show_In_SLC_Calendar: false,
    Event_Classification: null,
    Created_At: '2026-04-28T12:00:00Z',
    Updated_At: '2026-04-28T12:00:00Z',
    Links: [],
    Schedule_Requests: [makeScheduleRequest()],
    Occurrence_Dates: ['2026-05-05'],
    ...overrides,
  };
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true, now: new Date(2026, 4, 1, 9, 0, 0) });
  vi.clearAllMocks();
  getValidDatesMock.mockResolvedValue({
    dates: [
      { date: '2026-05-05', newsletters: ['tdr'] },
      { date: '2026-05-06', newsletters: ['tdr'] },
    ],
    blackout_dates: [],
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe('SubmissionMeta schedule management', () => {
  it('adds a plain run date without recurrence', async () => {
    const user = userEvent.setup();
    const onAddScheduleDate = vi.fn().mockResolvedValue(undefined);
    render(
      <SubmissionMeta
        submission={makeSubmission()}
        onAddScheduleDate={onAddScheduleDate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add run date/i }));
    const dateInput = await screen.findByDisplayValue('');
    await user.type(dateInput, '2026-05-06');
    await waitFor(() => {
      expect(screen.getByText('Valid publication date')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(onAddScheduleDate).toHaveBeenCalledWith('tdr', '2026-05-06', undefined);
    });
  });

  it('adds a valid My UI date to a both-newsletters submission', async () => {
    const user = userEvent.setup();
    const onAddScheduleDate = vi.fn().mockResolvedValue(undefined);
    getValidDatesMock.mockResolvedValue({
      dates: [{ date: '2026-05-04', newsletters: ['myui'] }],
      blackout_dates: [],
    });
    render(
      <SubmissionMeta
        submission={makeSubmission({ Target_Newsletter: 'both' })}
        onAddScheduleDate={onAddScheduleDate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add run date/i }));
    await user.click(screen.getByRole('radio', { name: 'My UI' }));
    await waitFor(() => {
      expect(getValidDatesMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        'myui',
      );
    });
    await user.type(screen.getByLabelText('Run date'), '2026-05-04');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(onAddScheduleDate).toHaveBeenCalledWith('myui', '2026-05-04', undefined);
    });
  });

  it('rejects a My UI date that is not in the valid-date service response', async () => {
    const user = userEvent.setup();
    const onAddScheduleDate = vi.fn().mockResolvedValue(undefined);
    getValidDatesMock.mockResolvedValue({
      dates: [{ date: '2026-05-04', newsletters: ['myui'] }],
      blackout_dates: [],
    });
    render(
      <SubmissionMeta
        submission={makeSubmission({ Target_Newsletter: 'both' })}
        onAddScheduleDate={onAddScheduleDate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add run date/i }));
    await user.click(screen.getByRole('radio', { name: 'My UI' }));
    await user.type(screen.getByLabelText('Run date'), '2026-05-05');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(
      await screen.findByText('Not a valid publication date for My UI (Mondays only).'),
    ).toBeInTheDocument();
    expect(onAddScheduleDate).not.toHaveBeenCalled();
  });

  it('labels separate Daily Register and My UI dates', () => {
    render(
      <SubmissionMeta
        submission={makeSubmission({
          Target_Newsletter: 'both',
          Schedule_Requests: [
            makeScheduleRequest({
              Requested_Date: '2026-05-05',
              Second_Requested_Date: '2026-05-04',
            }),
          ],
        })}
      />,
    );

    expect(screen.getByText('Daily Register:')).toBeInTheDocument();
    expect(screen.getByText('My UI:')).toBeInTheDocument();
    expect(screen.getByText(/Mon, May 4, 2026/)).toBeInTheDocument();
    expect(screen.getAllByText(/Tue, May 5, 2026/)).not.toHaveLength(0);
  });

  it('adds a recurring run date with interval and end date', async () => {
    const user = userEvent.setup();
    const onAddScheduleDate = vi.fn().mockResolvedValue(undefined);
    render(
      <SubmissionMeta
        submission={makeSubmission()}
        onAddScheduleDate={onAddScheduleDate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add run date/i }));
    const dateInput = await screen.findByDisplayValue('');
    await user.type(dateInput, '2026-05-06');
    await user.selectOptions(screen.getByLabelText('Repeats'), 'weekly');
    const intervalInput = screen.getByLabelText(/every n weeks/i);
    fireEvent.change(intervalInput, { target: { value: '2' } });
    await user.type(
      screen.getByLabelText(/ends on/i),
      '2026-06-30',
    );
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(onAddScheduleDate).toHaveBeenCalledWith('tdr', '2026-05-06', {
        Recurrence_Type: 'weekly',
        Recurrence_Interval: 2,
        Recurrence_End_Date: '2026-06-30',
      });
    });
  });

  it('adds an indefinite recurring run date when a first run date is selected', async () => {
    const user = userEvent.setup();
    const onAddScheduleDate = vi.fn().mockResolvedValue(undefined);
    render(
      <SubmissionMeta
        submission={makeSubmission()}
        onAddScheduleDate={onAddScheduleDate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add run date/i }));
    const dateInput = await screen.findByDisplayValue('');
    await user.type(dateInput, '2026-05-06');
    await user.selectOptions(screen.getByLabelText('Repeats'), 'weekly');
    fireEvent.change(screen.getByLabelText(/every n weeks/i), {
      target: { value: '6' },
    });
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(onAddScheduleDate).toHaveBeenCalledWith('tdr', '2026-05-06', {
        Recurrence_Type: 'weekly',
        Recurrence_Interval: 6,
        Recurrence_End_Date: undefined,
      });
    });
  });

  it('explains that a recurring schedule needs a first run date', async () => {
    const user = userEvent.setup();
    render(
      <SubmissionMeta
        submission={makeSubmission()}
        onAddScheduleDate={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add run date/i }));
    await user.selectOptions(screen.getByLabelText('Repeats'), 'weekly');

    expect(
      screen.getByText('Select a first run date to enable Save.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
  });

  it('rejects a recurrence end date before the first run date', async () => {
    const user = userEvent.setup();
    const onAddScheduleDate = vi.fn().mockResolvedValue(undefined);
    render(
      <SubmissionMeta
        submission={makeSubmission()}
        onAddScheduleDate={onAddScheduleDate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add run date/i }));
    const dateInput = await screen.findByDisplayValue('');
    await user.type(dateInput, '2026-05-06');
    await user.selectOptions(screen.getByLabelText('Repeats'), 'weekly');
    // Fake-timer clock is May 1, so May 5 is in range but before the run date.
    const endInput = screen.getByLabelText(/ends on/i);
    endInput.removeAttribute('min');
    await user.type(endInput, '2026-05-05');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(
      await screen.findByText(/end date cannot be before the first run date/i),
    ).toBeInTheDocument();
    expect(onAddScheduleDate).not.toHaveBeenCalled();
  });

  it('removes a schedule request', async () => {
    const user = userEvent.setup();
    const onRemoveScheduleRequest = vi.fn().mockResolvedValue(undefined);
    render(
      <SubmissionMeta
        submission={makeSubmission({
          Schedule_Requests: [
            makeScheduleRequest({
              Id: 'schedule-weekly',
              Recurrence_Type: 'weekly',
            }),
          ],
        })}
        onRemoveScheduleRequest={onRemoveScheduleRequest}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Remove' }));
    await waitFor(() => {
      expect(onRemoveScheduleRequest).toHaveBeenCalledWith('schedule-weekly');
    });
  });

  it('hides the remove control when no handler is provided', () => {
    render(<SubmissionMeta submission={makeSubmission()} />);
    expect(screen.queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
  });
});
