/**
 * Sidebar actions on the Edit page must not wipe unsaved Final Edit work (#489).
 *
 * SubmissionMeta is replaced by plain buttons that call each handler EditPage
 * passes it, so every schedule and newsletter action is one click here; its own
 * date pickers and confirmations are covered in SubmissionMeta.test.tsx.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  addScheduleRequest,
  deleteScheduleRequest,
  getSubmission,
  rescheduleScheduleOccurrence,
  skipScheduleOccurrence,
  updateSubmission,
} from '../api/submissions';
import { listEditVersions, saveEditorFinal } from '../api/aiEdits';
import type { EditVersion } from '../types/aiEdit';
import type { Submission, SubmissionScheduleRequest, TargetNewsletter } from '../types/submission';
import EditPage from './EditPage';

vi.mock('../api/submissions', () => ({
  addScheduleRequest: vi.fn(),
  deleteScheduleRequest: vi.fn(),
  getSubmission: vi.fn(),
  rescheduleScheduleOccurrence: vi.fn(),
  skipScheduleOccurrence: vi.fn(),
  updateSubmission: vi.fn(),
}));

vi.mock('../api/aiEdits', () => ({
  listEditVersions: vi.fn(),
  saveEditorFinal: vi.fn(),
  triggerAIEdit: vi.fn(),
}));

vi.mock('../utils/submitterRole', () => ({
  getSubmitterRole: () => 'staff',
}));

vi.mock('../components/editor/SubmissionMeta', () => ({
  default: (props: {
    submission: Submission;
    onChangeNewsletter?: (target: TargetNewsletter) => void;
    onSkipOccurrence?: (scheduleId: string, date: string) => Promise<void>;
    onRescheduleOccurrence?: (scheduleId: string, date: string, newDate: string) => Promise<void>;
    onAddScheduleDate?: (newsletter: 'tdr' | 'myui', date: string) => Promise<void>;
    onRemoveScheduleRequest?: (scheduleId: string) => Promise<void>;
  }) => (
    <div aria-label="Submission details" role="region">
      <p>Target: {props.submission.Target_Newsletter}</p>
      <p>Runs: {props.submission.Schedule_Requests.map((r) => r.Requested_Date).join(', ') || 'none'}</p>
      <button type="button" onClick={() => props.onChangeNewsletter?.('myui')}>Change newsletter</button>
      <button type="button" onClick={() => void props.onSkipOccurrence?.('schedule-1', '2026-04-15')}>Skip occurrence</button>
      <button
        type="button"
        onClick={() => void props.onRescheduleOccurrence?.('schedule-1', '2026-04-15', '2026-04-22')}
      >
        Move occurrence
      </button>
      <button type="button" onClick={() => void props.onAddScheduleDate?.('tdr', '2026-04-29')}>Add run date</button>
      <button type="button" onClick={() => void props.onRemoveScheduleRequest?.('schedule-1')}>Remove run date</button>
    </div>
  ),
}));

const getSubmissionMock = vi.mocked(getSubmission);
const listEditVersionsMock = vi.mocked(listEditVersions);
const saveEditorFinalMock = vi.mocked(saveEditorFinal);
const updateSubmissionMock = vi.mocked(updateSubmission);

function schedule(overrides: Partial<SubmissionScheduleRequest> = {}): SubmissionScheduleRequest {
  return {
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
    Repeats_Indefinitely: false,
    Excluded_Dates: [],
    Occurrence_Dates: ['2026-04-15'],
    ...overrides,
  };
}

function makeSubmission(overrides: Partial<Submission> = {}): Submission {
  return {
    Id: 'submission-1',
    Category: 'faculty_staff',
    Target_Newsletter: 'tdr',
    Original_Headline: 'Original campus headline',
    Original_Body: 'Original body copy.',
    Submitter_Name: 'Jane Submitter',
    Submitter_Email: 'jane@example.edu',
    Submitter_Notes: null,
    Assigned_Editor: 'Alex Editor',
    Editorial_Notes: null,
    Survey_End_Date: null,
    Has_Image: false,
    Image_Path: null,
    Status: 'in_review',
    Show_In_SLC_Calendar: false,
    Event_Classification: null,
    Approved_Version_Id: null,
    Working_Version_Id: 'version-saved',
    Staff_Revision_Id: 'version-saved',
    Edited_Headline: null,
    Created_At: '2026-04-01T12:00:00Z',
    Updated_At: '2026-04-01T12:00:00Z',
    Links: [
      { Id: 'link-1', Url: 'https://example.com/register', Anchor_Text: 'Register now', Display_Order: 0 },
    ],
    Schedule_Requests: [schedule()],
    Occurrence_Dates: ['2026-04-15'],
    ...overrides,
  };
}

const savedVersion: EditVersion = {
  Id: 'version-saved',
  Submission_Id: 'submission-1',
  Version_Type: 'editor_final',
  Headline: 'Saved headline',
  Body: 'Saved body. <a href="https://example.com/register">Register now</a>.',
  Headline_Case: 'sentence_case',
  Flags: null,
  Changes_Made: null,
  AI_Provider: null,
  AI_Model: null,
  Policy_Fingerprint: null,
  Editor_Instructions: null,
  Created_At: '2026-04-01T13:00:00Z',
};

function renderEditPage() {
  return render(
    <MemoryRouter initialEntries={['/edit/submission-1']}>
      <Routes>
        <Route path="/edit/:id" element={<EditPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Unsaved work in every Final Edit field: headline, body, a link URL, a new link. */
async function makeUnsavedEdits(user: ReturnType<typeof userEvent.setup>) {
  const headline = await screen.findByPlaceholderText('Enter headline...');
  await user.clear(headline);
  await user.type(headline, 'Unsaved headline');
  const body = screen.getByPlaceholderText('Enter body text...');
  await user.clear(body);
  await user.type(body, 'Unsaved body. Register now. Campus map.');
  await user.tab();
  const link1 = screen.getByRole('group', { name: 'Link 1' });
  await user.clear(within(link1).getByLabelText('URL'));
  await user.type(within(link1).getByLabelText('URL'), 'https://example.com/tickets');
  await user.click(screen.getByRole('button', { name: 'Add a link' }));
  const link2 = screen.getByRole('group', { name: 'Link 2' });
  await user.click(within(link2).getByRole('button', { name: 'Switch to email link' }));
  await user.type(within(link2).getByLabelText('Email address'), 'maps@example.edu');
  await user.type(within(link2).getByLabelText(/Link text/), 'Campus map');
  await user.tab();
}

function expectUnsavedEditsKept() {
  expect(screen.getByPlaceholderText('Enter headline...')).toHaveValue('Unsaved headline');
  expect(screen.getByPlaceholderText('Enter body text...')).toHaveValue(
    'Unsaved body. Register now. Campus map.',
  );
  expect(within(screen.getByRole('group', { name: 'Link 1' })).getByLabelText('URL'))
    .toHaveValue('https://example.com/tickets');
  const link2 = screen.getByRole('group', { name: 'Link 2' });
  expect(within(link2).getByLabelText('Email address')).toHaveValue('maps@example.edu');
  expect(within(link2).getByLabelText(/Link text/)).toHaveValue('Campus map');
}

const unsavedPayload = {
  Headline: 'Unsaved headline',
  Body: 'Unsaved body. <a href="https://example.com/tickets">Register now</a>. '
    + '<a href="mailto:maps@example.edu">Campus map</a>.',
  Links: [
    { Url: 'https://example.com/tickets', Anchor_Text: 'Register now', Display_Order: 0 },
    { Url: 'mailto:maps@example.edu', Anchor_Text: 'Campus map', Display_Order: 1 },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  getSubmissionMock.mockResolvedValue(makeSubmission());
  listEditVersionsMock.mockResolvedValue([savedVersion]);
  saveEditorFinalMock.mockResolvedValue(savedVersion);
  updateSubmissionMock.mockResolvedValue(makeSubmission());
  vi.mocked(addScheduleRequest).mockResolvedValue(schedule({ Id: 'schedule-2', Requested_Date: '2026-04-29' }));
  vi.mocked(deleteScheduleRequest).mockResolvedValue(undefined);
  vi.mocked(skipScheduleOccurrence).mockResolvedValue(schedule({ Excluded_Dates: ['2026-04-15'] }));
  vi.mocked(rescheduleScheduleOccurrence).mockResolvedValue(schedule({ Requested_Date: '2026-04-22' }));
});

describe('EditPage sidebar actions keep unsaved Final Edit work (#489)', () => {
  const sidebarActions: Array<{
    name: string;
    run: (user: ReturnType<typeof userEvent.setup>) => Promise<void>;
    serverAfter: Partial<Submission>;
    shows: string;
  }> = [
    {
      name: 'changing the newsletter',
      run: (user) => user.click(screen.getByRole('button', { name: 'Change newsletter' })),
      serverAfter: { Target_Newsletter: 'myui' },
      shows: 'Target: myui',
    },
    {
      name: 'skipping an occurrence',
      run: (user) => user.click(screen.getByRole('button', { name: 'Skip occurrence' })),
      serverAfter: { Schedule_Requests: [], Occurrence_Dates: [] },
      shows: 'Runs: none',
    },
    {
      name: 'moving an occurrence',
      run: (user) => user.click(screen.getByRole('button', { name: 'Move occurrence' })),
      serverAfter: { Schedule_Requests: [schedule({ Requested_Date: '2026-04-22' })] },
      shows: 'Runs: 2026-04-22',
    },
    {
      name: 'adding a run date',
      run: (user) => user.click(screen.getByRole('button', { name: 'Add run date' })),
      serverAfter: {
        Schedule_Requests: [schedule(), schedule({ Id: 'schedule-2', Requested_Date: '2026-04-29' })],
      },
      shows: 'Runs: 2026-04-15, 2026-04-29',
    },
    {
      name: 'removing a run date',
      run: (user) => user.click(screen.getByRole('button', { name: 'Remove run date' })),
      serverAfter: { Schedule_Requests: [], Occurrence_Dates: [] },
      shows: 'Runs: none',
    },
    {
      name: 'marking the submission pending info',
      run: async (user) => {
        await user.click(screen.getByRole('button', { name: 'Request More Info' }));
        await user.click(screen.getByRole('button', { name: 'Yes, mark pending' }));
      },
      serverAfter: { Status: 'pending_info' },
      shows: 'pending info',
    },
  ];

  it.each(sidebarActions)('keeps typed text and link edits after $name', async ({ run, serverAfter, shows }) => {
    const user = userEvent.setup();
    renderEditPage();
    await makeUnsavedEdits(user);

    // The server now holds a newer submission and an unchanged saved version.
    getSubmissionMock.mockResolvedValue(makeSubmission(serverAfter));
    await run(user);

    expect(await screen.findByText(shows)).toBeInTheDocument();
    expectUnsavedEditsKept();

    await user.click(screen.getByRole('button', { name: /save draft/i }));
    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
        ...unsavedPayload,
        Base_Staff_Revision_Id: 'version-saved',
      }));
    });
  });

  it('keeps typed text and link edits after marking info received', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Status: 'pending_info' }));
    renderEditPage();
    await makeUnsavedEdits(user);

    getSubmissionMock.mockResolvedValue(makeSubmission({ Status: 'in_review' }));
    await user.click(screen.getByRole('button', { name: 'Mark Info Received' }));

    expect(await screen.findByText('in review')).toBeInTheDocument();
    expectUnsavedEditsKept();
  });

  it('saves against the revision the text was loaded from, not one a refresh brought in', async () => {
    const user = userEvent.setup();
    renderEditPage();
    await makeUnsavedEdits(user);

    // Someone else saved meanwhile; the refresh must not hide that from the save.
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Target_Newsletter: 'myui',
      Staff_Revision_Id: 'version-theirs',
      Working_Version_Id: 'version-theirs',
    }));
    await user.click(screen.getByRole('button', { name: 'Change newsletter' }));
    await screen.findByText('Target: myui');
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
        Base_Staff_Revision_Id: 'version-saved',
      }));
    });
  });

  it('keeps unsaved editorial workflow notes after a sidebar action', async () => {
    const user = userEvent.setup();
    renderEditPage();
    const notes = await screen.findByLabelText('Internal Notes');
    await user.type(notes, 'Call the submitter Tuesday.');

    getSubmissionMock.mockResolvedValue(makeSubmission({ Target_Newsletter: 'myui' }));
    await user.click(screen.getByRole('button', { name: 'Change newsletter' }));

    expect(await screen.findByText('Target: myui')).toBeInTheDocument();
    expect(screen.getByLabelText('Internal Notes')).toHaveValue('Call the submitter Tuesday.');
  });
});
