import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listAllowedValues } from '../../api/allowedValues';
import { getValidDates } from '../../api/schedule';
import { createSubmission } from '../../api/submissions';
import type { AllowedValue } from '../../types/allowedValue';
import type { Submission } from '../../types/submission';
import SubmissionForm from './SubmissionForm';

const submitterRoleMock = vi.hoisted(() => ({
  value: 'public',
}));

vi.mock('../../api/allowedValues', () => ({
  listAllowedValues: vi.fn(),
}));

vi.mock('../../api/schedule', () => ({
  getValidDates: vi.fn(),
}));

vi.mock('../../api/submissions', () => ({
  createSubmission: vi.fn(),
}));

vi.mock('../../utils/submitterRole', () => ({
  getSubmitterRole: () => submitterRoleMock.value,
}));

const listAllowedValuesMock = vi.mocked(listAllowedValues);
const getValidDatesMock = vi.mocked(getValidDates);
const createSubmissionMock = vi.mocked(createSubmission);

const allowedCategories: AllowedValue[] = [
  {
    Id: 'faculty_staff',
    Value_Group: 'Submission_Category',
    Code: 'faculty_staff',
    Label: 'Faculty or Staff Announcement',
    Display_Order: 1,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: null,
  },
  {
    Id: 'student',
    Value_Group: 'Submission_Category',
    Code: 'student',
    Label: 'Student Announcement',
    Display_Order: 2,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: null,
  },
  {
    Id: 'survey',
    Value_Group: 'Submission_Category',
    Code: 'survey',
    Label: 'Survey',
    Display_Order: 3,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: null,
  },
  {
    Id: 'job_opportunity',
    Value_Group: 'Submission_Category',
    Code: 'job_opportunity',
    Label: 'Job Opportunity',
    Display_Order: 4,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: null,
  },
];

function makeSubmission(overrides: Partial<Submission> = {}): Submission {
  return {
    Id: 'submission-1',
    Category: 'faculty_staff',
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
    Status: 'new',
    Show_In_SLC_Calendar: false,
    Event_Classification: null,
    Created_At: '2026-04-28T12:00:00Z',
    Updated_At: '2026-04-28T12:00:00Z',
    Links: [],
    Schedule_Requests: [],
    Occurrence_Dates: [],
    ...overrides,
  };
}

async function fillStandardAnnouncement(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Headline'), 'Campus forum');
  await user.type(screen.getByLabelText('Body Text'), 'Join us for a campus-wide forum.');
  await user.type(screen.getAllByLabelText('URL')[0], 'https://www.uidaho.edu/forum');
  await user.type(screen.getAllByLabelText(/words to link/i)[0], 'forum details');
  await user.type(screen.getByLabelText('Preferred run date'), '2026-05-05');
  await user.type(screen.getByLabelText('Additional Notes for Editors'), 'Please review timing.');
  await user.type(screen.getByLabelText('Your Name'), 'Jane Submitter');
  await user.type(screen.getByLabelText('Email Address'), 'jane@example.edu');
}

beforeEach(() => {
  vi.clearAllMocks();
  submitterRoleMock.value = 'public';
  listAllowedValuesMock.mockResolvedValue(allowedCategories);
  getValidDatesMock.mockResolvedValue({
    dates: [
      { date: '2026-05-04', newsletters: ['myui'] },
      { date: '2026-05-05', newsletters: ['tdr'] },
      { date: '2026-05-06', newsletters: ['tdr'] },
    ],
    blackout_dates: [],
  });
  createSubmissionMock.mockResolvedValue(makeSubmission());
});

describe('SubmissionForm', () => {
  it('submits a standard announcement with links and scheduling notes', async () => {
    const user = userEvent.setup();
    render(<SubmissionForm />);

    await screen.findByRole('option', { name: 'Faculty or Staff Announcement' });
    await fillStandardAnnouncement(user);
    await user.click(screen.getByRole('button', { name: /submit announcement/i }));

    await waitFor(() => {
      expect(createSubmissionMock).toHaveBeenCalledWith({
        Category: 'faculty_staff',
        Target_Newsletter: 'tdr',
        Original_Headline: 'Campus forum',
        Original_Body: 'Join us for a campus-wide forum.',
        Submitter_Name: 'Jane Submitter',
        Submitter_Email: 'jane@example.edu',
        Submitter_Notes: 'Please review timing.',
        Survey_End_Date: undefined,
        Links: [
          {
            Url: 'https://www.uidaho.edu/forum',
            Anchor_Text: 'forum details',
          },
        ],
        Schedule_Requests: [
          {
            Requested_Date: '2026-05-05',
            Second_Requested_Date: undefined,
            Repeat_Count: 1,
            Repeat_Note: undefined,
            Is_Flexible: undefined,
            Flexible_Deadline: undefined,
            Recurrence_Type: 'once',
            Recurrence_Interval: 1,
            Recurrence_End_Date: undefined,
          },
        ],
      });
    });
    expect(await screen.findByText(/submission received/i)).toBeInTheDocument();
  });

  it('submits separate TDR and My UI run dates when both newsletters are selected', async () => {
    const user = userEvent.setup();
    render(<SubmissionForm />);

    await screen.findByRole('option', { name: 'Faculty or Staff Announcement' });
    await user.click(screen.getByRole('button', { name: /both newsletters/i }));
    await user.type(screen.getByLabelText('Headline'), 'Campus forum');
    await user.type(screen.getByLabelText('Body Text'), 'Join us for a campus-wide forum.');
    await user.type(screen.getByLabelText(/daily register run date/i), '2026-05-05');
    await user.type(screen.getByLabelText(/my ui run date/i), '2026-05-04');
    await user.type(screen.getByLabelText('Your Name'), 'Jane Submitter');
    await user.type(screen.getByLabelText('Email Address'), 'jane@example.edu');
    await user.click(screen.getByRole('button', { name: /submit announcement/i }));

    await waitFor(() => {
      expect(createSubmissionMock).toHaveBeenCalledWith(
        expect.objectContaining({
          Target_Newsletter: 'both',
          Schedule_Requests: [
            expect.objectContaining({
              Requested_Date: '2026-05-05',
              Second_Requested_Date: '2026-05-04',
              Repeat_Count: 2,
            }),
          ],
        }),
      );
    });
  });

  it('blocks submission when the selected run date is not valid', async () => {
    const user = userEvent.setup();
    render(<SubmissionForm />);

    await screen.findByRole('option', { name: 'Faculty or Staff Announcement' });
    await user.type(screen.getByLabelText('Headline'), 'Campus forum');
    await user.type(screen.getByLabelText('Body Text'), 'Join us for a campus-wide forum.');
    await user.type(screen.getByLabelText('Preferred run date'), '2026-05-03');
    await user.type(screen.getByLabelText('Your Name'), 'Jane Submitter');
    await user.type(screen.getByLabelText('Email Address'), 'jane@example.edu');
    await user.click(screen.getByRole('button', { name: /submit announcement/i }));

    expect(await screen.findByText('Please select a valid run date for the chosen newsletter.')).toBeInTheDocument();
    expect(createSubmissionMock).not.toHaveBeenCalled();
  });

  it('builds the structured job posting payload and forces TDR', async () => {
    const user = userEvent.setup();
    render(<SubmissionForm />);

    await screen.findByRole('option', { name: 'Job Opportunity' });
    await user.selectOptions(screen.getByLabelText('Announcement Type'), 'job_opportunity');
    expect(screen.getByRole('button', { name: /my ui/i })).toBeDisabled();

    await user.type(screen.getByLabelText('Job Posting URL'), 'https://uidaho.peopleadmin.com/postings/123');
    await user.type(screen.getByLabelText('Position Title'), 'Program Coordinator');
    await user.type(screen.getByLabelText('Department'), 'Student Affairs');
    await user.type(screen.getByLabelText('Location(s)'), 'Moscow');
    await user.type(screen.getByLabelText('Preferred run date'), '2026-05-05');
    await user.type(screen.getByLabelText('Your Name'), 'Jane Submitter');
    await user.type(screen.getByLabelText('Email Address'), 'jane@example.edu');
    await user.click(screen.getByRole('button', { name: /submit announcement/i }));

    await waitFor(() => {
      expect(createSubmissionMock).toHaveBeenCalledWith(
        expect.objectContaining({
          Category: 'job_opportunity',
          Target_Newsletter: 'tdr',
          Original_Headline: 'Program Coordinator',
          Original_Body: 'Department: Student Affairs. Location: Moscow. Apply using the linked posting.',
          Links: [
            {
              Url: 'https://uidaho.peopleadmin.com/postings/123',
              Anchor_Text: 'Program Coordinator, Student Affairs, Moscow',
            },
          ],
        }),
      );
    });
  });
});
