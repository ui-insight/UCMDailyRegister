import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getValidDates } from '../api/schedule';
import { listSubmissions } from '../api/submissions';
import type { Submission, SubmissionStatus, TargetNewsletter } from '../types/submission';
import DashboardPage from './DashboardPage';

vi.mock('../api/submissions', () => ({
  listSubmissions: vi.fn(),
}));

vi.mock('../api/schedule', () => ({
  getValidDates: vi.fn(),
}));

const listSubmissionsMock = vi.mocked(listSubmissions);
const getValidDatesMock = vi.mocked(getValidDates);

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function makeSubmission(
  overrides: Partial<Submission> = {},
): Submission {
  return {
    Id: 'submission-1',
    Category: 'faculty_staff',
    Target_Newsletter: 'tdr',
    Original_Headline: 'Campus Forum',
    Original_Body: 'A forum for the campus community.',
    Submitter_Name: 'Jane Editor',
    Submitter_Email: 'jane@example.edu',
    Submitter_Notes: null,
    Assigned_Editor: null,
    Editorial_Notes: null,
    Survey_End_Date: null,
    Has_Image: false,
    Image_Path: null,
    Status: 'new',
    Show_In_SLC_Calendar: false,
    Event_Classification: null,
    Created_At: '2026-04-01T12:00:00Z',
    Updated_At: '2026-04-01T12:00:00Z',
    Links: [],
    Schedule_Requests: [],
    Occurrence_Dates: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  listSubmissionsMock.mockResolvedValue({
    Items: [
      makeSubmission({
        Id: 'submission-1',
        Status: 'approved',
        Category: 'kudos',
        Target_Newsletter: 'myui',
        Assigned_Editor: 'Alex',
        Editorial_Notes: 'Needs short intro.',
        Links: [
          {
            Id: 'link-1',
            Url: 'https://www.uidaho.edu',
            Anchor_Text: 'University of Idaho',
            Display_Order: 1,
          },
        ],
        Has_Image: true,
        Schedule_Requests: [
          {
            Id: 'schedule-1',
            Requested_Date: '2026-04-15',
            Second_Requested_Date: null,
            Repeat_Count: 1,
            Repeat_Note: null,
            Is_Flexible: false,
            Flexible_Deadline: null,
            Recurrence_Type: 'once',
            Recurrence_Interval: 1,
            Recurrence_End_Date: null,
            Excluded_Dates: [],
            Occurrence_Dates: ['2026-04-15'],
          },
        ],
      }),
    ],
    Total: 1,
  });
  getValidDatesMock.mockResolvedValue({
    dates: [
      {
        date: '2026-04-15',
        newsletters: ['tdr', 'myui'],
      },
    ],
    blackout_dates: [],
  });
});

describe('DashboardPage', () => {
  it('loads and renders the submission list', async () => {
    renderDashboard();

    expect(await screen.findByText('Campus Forum')).toBeInTheDocument();
    expect(screen.getByText('1 submission')).toBeInTheDocument();
    expect(screen.getAllByText('Approved')).not.toHaveLength(0);
    expect(screen.getAllByText('Kudos')).not.toHaveLength(0);
    expect(screen.getAllByText('My UI')).not.toHaveLength(0);
    expect(screen.getByText('Assigned: Alex')).toBeInTheDocument();
    expect(screen.getByText('Has notes')).toBeInTheDocument();
    expect(screen.getByText('Has image')).toBeInTheDocument();
  });

  it('sends selected filters and search text to the submissions API', async () => {
    const user = userEvent.setup();
    renderDashboard();

    await screen.findByText('Campus Forum');

    await user.selectOptions(screen.getByLabelText('Status'), 'approved');
    await user.selectOptions(screen.getByLabelText('Category'), 'kudos');
    await user.selectOptions(screen.getByLabelText('Newsletter'), 'myui');
    await user.type(screen.getByPlaceholderText(/search headlines/i), 'forum');
    await user.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(listSubmissionsMock).toHaveBeenLastCalledWith({
        status: 'approved',
        category: 'kudos',
        target_newsletter: 'myui',
        search: 'forum',
        limit: 200,
      });
    });
  });

  it('loads valid publish dates and date-bounded submissions in calendar mode', async () => {
    const user = userEvent.setup();
    renderDashboard();

    await screen.findByText('Campus Forum');

    await user.click(screen.getByRole('button', { name: 'Calendar' }));

    const now = new Date();
    const from = toISODate(new Date(now.getFullYear(), now.getMonth(), 1));
    const to = toISODate(new Date(now.getFullYear(), now.getMonth() + 1, 0));

    await waitFor(() => {
      expect(getValidDatesMock).toHaveBeenCalledWith(from, to);
      expect(listSubmissionsMock).toHaveBeenLastCalledWith({
        status: undefined,
        category: undefined,
        target_newsletter: undefined,
        search: undefined,
        limit: 200,
        date_from: from,
        date_to: to,
      });
    });
    expect(screen.getByText(/click a date to see scheduled submissions/i)).toBeInTheDocument();
  });

  it('shows the empty state when no submissions match', async () => {
    listSubmissionsMock.mockResolvedValueOnce({ Items: [], Total: 0 });

    renderDashboard();

    expect(await screen.findByText('No submissions found.')).toBeInTheDocument();
    expect(screen.getByText('Submit an announcement using the Submit page.')).toBeInTheDocument();
  });

  it('shows load errors without replacing the filters', async () => {
    listSubmissionsMock.mockRejectedValueOnce(new Error('Network is unavailable'));

    renderDashboard();

    expect(await screen.findByText('Network is unavailable')).toBeInTheDocument();
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByLabelText('Category')).toBeInTheDocument();
    expect(screen.getByLabelText('Newsletter')).toBeInTheDocument();
  });

  const actionCases: Array<[SubmissionStatus, string]> = [
    ['new', 'Run AI Edit'],
    ['ai_edited', 'Review Edit'],
    ['in_review', 'Finalize'],
    ['approved', 'Schedule'],
    ['published', 'View'],
  ];

  it.each(actionCases)('shows the %s status action as "%s"', async (status, action) => {
    listSubmissionsMock.mockResolvedValueOnce({
      Items: [
        makeSubmission({
          Status: status,
          Target_Newsletter: 'both' satisfies TargetNewsletter,
        }),
      ],
      Total: 1,
    });

    renderDashboard();

    expect(await screen.findByRole('button', { name: action })).toBeInTheDocument();
  });
});
