import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  addScheduleRequest,
  getSubmission,
  rescheduleScheduleOccurrence,
  skipScheduleOccurrence,
  updateSubmission,
} from '../api/submissions';
import { listEditVersions, saveEditorFinal, triggerAIEdit } from '../api/aiEdits';
import { ApiError } from '../api/client';
import type { AIEditResponse, EditVersion } from '../types/aiEdit';
import type { Submission } from '../types/submission';
import EditPage from './EditPage';

vi.mock('../api/submissions', () => ({
  addScheduleRequest: vi.fn(),
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

const getSubmissionMock = vi.mocked(getSubmission);
const listEditVersionsMock = vi.mocked(listEditVersions);
const saveEditorFinalMock = vi.mocked(saveEditorFinal);
const triggerAIEditMock = vi.mocked(triggerAIEdit);
const updateSubmissionMock = vi.mocked(updateSubmission);
const addScheduleRequestMock = vi.mocked(addScheduleRequest);
const skipScheduleOccurrenceMock = vi.mocked(skipScheduleOccurrence);
const rescheduleScheduleOccurrenceMock = vi.mocked(rescheduleScheduleOccurrence);

function renderEditPage() {
  return render(
    <MemoryRouter initialEntries={['/edit/submission-1']}>
      <Routes>
        <Route path="/edit/:id" element={<EditPage />} />
        <Route path="/dashboard" element={<div>Dashboard route</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function makeSubmission(overrides: Partial<Submission> = {}): Submission {
  return {
    Id: 'submission-1',
    Category: 'faculty_staff',
    Target_Newsletter: 'tdr',
    Original_Headline: 'Original campus headline',
    Original_Body: 'Original body copy for the newsletter.',
    Submitter_Name: 'Jane Submitter',
    Submitter_Email: 'jane@example.edu',
    Submitter_Notes: null,
    Assigned_Editor: 'Alex Editor',
    Editorial_Notes: 'Check the event time.',
    Survey_End_Date: null,
    Has_Image: false,
    Image_Path: null,
    Status: 'in_review',
    Show_In_SLC_Calendar: false,
    Event_Classification: null,
    Approved_Version_Id: null,
    Working_Version_Id: null,
    Staff_Revision_Id: null,
    Edited_Headline: null,
    Created_At: '2026-04-01T12:00:00Z',
    Updated_At: '2026-04-01T12:00:00Z',
    Links: [],
    Schedule_Requests: [],
    Occurrence_Dates: [],
    ...overrides,
  };
}

function makeVersion(overrides: Partial<EditVersion> = {}): EditVersion {
  return {
    Id: 'version-1',
    Submission_Id: 'submission-1',
    Version_Type: 'ai_suggested',
    Headline: 'AI campus headline',
    Body: 'AI edited body copy.',
    Headline_Case: 'sentence_case',
    Flags: null,
    Changes_Made: null,
    AI_Provider: 'openai',
    AI_Model: 'gpt-test',
    Policy_Fingerprint: '2026-11-04:000000000000',
    Editor_Instructions: null,
    Created_At: '2026-04-01T13:00:00Z',
    ...overrides,
  };
}

function makeAIResponse(overrides: Partial<AIEditResponse> = {}): AIEditResponse {
  return {
    Submission_Id: 'submission-1',
    Newsletter_Type: 'tdr',
    Edited_Headline: 'AI campus headline',
    Edited_Body: 'AI edited body copy.',
    Headline_Case: 'sentence_case',
    Changes_Made: ['Tightened the lede'],
    Flags: [
      {
        type: 'info',
        rule_key: 'clarity',
        message: 'Consider adding a contact link.',
      },
    ],
    Embedded_Links: [],
    Confidence: 0.91,
    AI_Provider: 'openai',
    AI_Model: 'gpt-test',
    Policy_Fingerprint: '2026-11-04:000000000000',
    Headline_Diff: {
      segments: [
        {
          type: 'replace',
          original: 'Original campus headline',
          modified: 'AI campus headline',
        },
      ],
      change_count: 1,
      similarity_ratio: 0.6,
    },
    Body_Diff: {
      segments: [
        {
          type: 'replace',
          original: 'Original body copy for the newsletter.',
          modified: 'AI edited body copy.',
        },
      ],
      change_count: 1,
      similarity_ratio: 0.5,
    },
    Edit_Version_Id: 'version-1',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  getSubmissionMock.mockResolvedValue(makeSubmission());
  listEditVersionsMock.mockResolvedValue([]);
  saveEditorFinalMock.mockResolvedValue(makeVersion({ Version_Type: 'editor_final' }));
  triggerAIEditMock.mockResolvedValue(makeAIResponse());
  updateSubmissionMock.mockResolvedValue(makeSubmission({ Status: 'approved' }));
  addScheduleRequestMock.mockResolvedValue({
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
  });
  skipScheduleOccurrenceMock.mockResolvedValue({
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
    Excluded_Dates: ['2026-04-15'],
    Occurrence_Dates: [],
  });
  rescheduleScheduleOccurrenceMock.mockResolvedValue({
    Id: 'schedule-1',
    Requested_Date: '2026-04-22',
    Second_Requested_Date: null,
    Repeat_Count: 1,
    Repeat_Note: null,
    Is_Flexible: false,
    Flexible_Deadline: null,
    Recurrence_Type: 'once',
    Recurrence_Interval: 1,
    Recurrence_End_Date: null,
    Excluded_Dates: [],
    Occurrence_Dates: ['2026-04-22'],
  });
});

describe('EditPage', () => {
  it('loads a submission and shows the original text by default', async () => {
    renderEditPage();

    expect(screen.getByText('Loading submission...')).toBeInTheDocument();
    expect(await screen.findByText('Original campus headline')).toBeInTheDocument();
    expect(screen.getByText('Original body copy for the newsletter.')).toBeInTheDocument();
    expect(screen.getByText('ID: submission-1')).toBeInTheDocument();
    expect(screen.getByText('Jane Submitter')).toBeInTheDocument();
    expect(getSubmissionMock).toHaveBeenCalledWith('submission-1');
    expect(listEditVersionsMock).toHaveBeenCalledWith('submission-1');
  });

  it('opens the working revision the backend names', async () => {
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-final' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Id: 'version-ai',
        Version_Type: 'ai_suggested',
        Headline: 'AI campus headline',
        Body: 'AI body.',
      }),
      makeVersion({
        Id: 'version-final',
        Version_Type: 'editor_final',
        Headline: 'Final editor headline',
        Body: 'Final editor body.',
      }),
    ]);

    renderEditPage();

    expect(await screen.findByDisplayValue('Final editor headline')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Final editor body.')).toBeInTheDocument();
  });

  it('opens the approved revision even when a newer final exists', async () => {
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Status: 'approved',
      Approved_Version_Id: 'version-approved',
      Working_Version_Id: 'version-approved',
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Id: 'version-approved',
        Version_Type: 'editor_final',
        Headline: 'Approved headline',
        Body: 'Approved body.',
        Created_At: '2026-04-01T13:00:00Z',
      }),
      makeVersion({
        Id: 'version-later',
        Version_Type: 'editor_final',
        Headline: 'Later headline',
        Body: 'Later body.',
        Created_At: '2026-04-01T13:00:00Z',
      }),
    ]);

    renderEditPage();

    expect(await screen.findByDisplayValue('Approved headline')).toBeInTheDocument();
    expect(screen.queryByDisplayValue('Later body.')).not.toBeInTheDocument();
  });

  it('runs an AI edit and displays the returned suggestion', async () => {
    const user = userEvent.setup();
    const aiVersion = makeVersion();
    listEditVersionsMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([aiVersion]);

    renderEditPage();

    await screen.findByText('Original campus headline');
    await user.click(screen.getByRole('button', { name: /tdr/i }));

    await waitFor(() => {
      expect(triggerAIEditMock).toHaveBeenCalledWith('submission-1', 'tdr');
    });
    expect(await screen.findByText('AI campus headline')).toBeInTheDocument();
    expect(screen.getByText('AI edited body copy.')).toBeInTheDocument();
    expect(screen.getByText('91%')).toBeInTheDocument();
    expect(screen.getByText('Tightened the lede')).toBeInTheDocument();
    expect(screen.getByText('AI edit complete')).toBeInTheDocument();
  });

  it('edits and approves an AI suggestion directly from Live View', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: 'AI working headline',
        Body: 'AI working body.',
        Headline_Case: 'title_case',
      }),
    ]);

    renderEditPage();

    await screen.findByText('AI working headline');
    await user.click(screen.getByRole('button', { name: 'Live View' }));

    const liveEdit = screen.getByRole('region', { name: 'AI live edit' });
    const headline = within(liveEdit).getByPlaceholderText('Enter headline...');
    const body = within(liveEdit).getByPlaceholderText('Enter body text...');

    await user.clear(headline);
    await user.type(headline, 'Editor-improved AI headline');
    await user.clear(body);
    await user.type(body, 'Editor-improved AI body.');
    await user.click(within(liveEdit).getByRole('button', { name: /save and approve/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Editor-improved AI headline',
        Body: 'Editor-improved AI body.',
        Headline_Case: 'title_case',
        Approve_For_Newsletter: true,
        Base_Staff_Revision_Id: null,
      });
    });
  });

  it('keeps Live View changes when continuing to Final Edit', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: 'AI working headline',
        Body: 'AI working body.',
      }),
    ]);

    renderEditPage();

    await screen.findByText('AI working headline');
    await user.click(screen.getByRole('button', { name: 'Live View' }));

    const liveEdit = screen.getByRole('region', { name: 'AI live edit' });
    const body = within(liveEdit).getByPlaceholderText('Enter body text...');
    await user.clear(body);
    await user.type(body, 'Changes made before final review.');
    await user.click(screen.getByRole('button', { name: /use ai suggestion in final edit/i }));

    const finalEdit = screen.getByRole('region', { name: 'Final edit' });
    expect(within(finalEdit).getByDisplayValue('Changes made before final review.'))
      .toBeInTheDocument();
    expect(within(finalEdit).getByText('Starting point: AI suggestion')).toBeInTheDocument();
  });

  it('keeps the AI Live View open after saving an editor draft', async () => {
    const user = userEvent.setup();
    const aiVersion = makeVersion({
      Headline: 'AI working headline',
      Body: 'AI working body.',
    });
    const savedDraft = makeVersion({
      Id: 'version-final',
      Version_Type: 'editor_final',
      Headline: 'AI working headline',
      Body: 'Draft revised in Live View.',
    });
    getSubmissionMock
      .mockResolvedValueOnce(makeSubmission({ Working_Version_Id: 'version-1' }))
      .mockResolvedValueOnce(makeSubmission({ Working_Version_Id: 'version-final' }));
    listEditVersionsMock
      .mockResolvedValueOnce([aiVersion])
      .mockResolvedValueOnce([aiVersion, savedDraft]);

    renderEditPage();

    await screen.findByText('AI working headline');
    await user.click(screen.getByRole('button', { name: 'Live View' }));
    const body = screen.getByPlaceholderText('Enter body text...');
    await user.clear(body);
    await user.type(body, 'Draft revised in Live View.');
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    expect(await screen.findByText('Draft saved. Submission remains in review')).toBeInTheDocument();
    const liveEdit = screen.getByRole('region', { name: 'AI live edit' });
    expect(within(liveEdit).getByDisplayValue('Draft revised in Live View.')).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Final edit' })).not.toBeInTheDocument();
  });

  it('does not overwrite a saved draft when switching to Live View', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-final' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: 'AI working headline',
        Body: 'AI working body.',
      }),
      makeVersion({
        Id: 'version-final',
        Version_Type: 'editor_final',
        Headline: 'Draft headline kept by the editor',
        Body: 'Draft body kept by the editor.',
      }),
    ]);

    renderEditPage();

    await screen.findByDisplayValue('Draft body kept by the editor.');
    await user.click(screen.getByRole('button', { name: 'AI Suggested' }));
    await user.click(screen.getByRole('button', { name: 'Live View' }));

    const liveEdit = screen.getByRole('region', { name: 'AI live edit' });
    expect(within(liveEdit).getByDisplayValue('Draft body kept by the editor.')).toBeInTheDocument();
    expect(within(liveEdit).queryByDisplayValue('AI working body.')).not.toBeInTheDocument();
  });

  it('edits and approves a body-only Jobs suggestion directly from Live View', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-1',
      Category: 'job_opportunity',
      Status: 'ai_edited',
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: '',
        Body: 'Administrative specialist III, College of Engineering',
      }),
    ]);

    renderEditPage();

    await screen.findByText('Administrative specialist III, College of Engineering');
    await user.click(screen.getByRole('button', { name: 'Live View' }));

    const liveEdit = screen.getByRole('region', { name: 'AI live edit' });
    expect(within(liveEdit).queryByPlaceholderText('Enter headline...')).not.toBeInTheDocument();
    const body = within(liveEdit).getByPlaceholderText('Enter body text...');
    await user.type(body, ', Boise');
    await user.click(within(liveEdit).getByRole('button', { name: /save and approve/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: '',
        Body: 'Administrative specialist III, College of Engineering, Boise',
        Headline_Case: 'sentence_case',
        Approve_For_Newsletter: true,
        Base_Staff_Revision_Id: null,
      });
    });
  });

  it('keeps CTA links synchronized while editing an AI suggestion in Live View', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-1',
      Links: [
        {
          Id: 'link-1',
          Url: 'https://example.com/register',
          Anchor_Text: 'Register now',
          Display_Order: 0,
        },
      ],
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: 'AI event headline',
        Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
      }),
    ]);

    renderEditPage();

    await screen.findByText('AI event headline');
    await user.click(screen.getByRole('button', { name: 'Live View' }));

    const liveEdit = screen.getByRole('region', { name: 'AI live edit' });
    const body = within(liveEdit).getByPlaceholderText('Enter body text...');
    expect(body).toHaveValue('Reserve a seat. Register now.');

    await user.clear(body);
    await user.type(body, 'Reserve a seat. Sign up today.');
    await user.click(within(liveEdit).getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'AI event headline',
        Body: 'Reserve a seat. <a href="https://example.com/register">Sign up today</a>.',
        Headline_Case: 'sentence_case',
        Approve_For_Newsletter: false,
        Base_Staff_Revision_Id: null,
        Links: [
          {
            Url: 'https://example.com/register',
            Anchor_Text: 'Sign up today',
            Display_Order: 0,
          },
        ],
      });
    });
  });

  it('reviews and approves the latest AI version through Final Edit', async () => {
    const user = userEvent.setup();
    const aiVersion = makeVersion({
      Headline: 'Accepted AI headline',
      Body: 'Accepted AI body.',
      Headline_Case: 'title_case',
    });
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([aiVersion]);

    renderEditPage();

    await screen.findByText('Accepted AI headline');
    expect(screen.queryByRole('button', { name: /accept ai edit/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /use ai suggestion in final edit/i }));
    expect(screen.getByDisplayValue('Accepted AI headline')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Accepted AI body.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /save and approve/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Accepted AI headline',
        Body: 'Accepted AI body.',
        Headline_Case: 'title_case',
        Approve_For_Newsletter: true,
        Base_Staff_Revision_Id: null,
      });
    });
    expect(
      await screen.findByText('Final version saved and approved for newsletter'),
    ).toBeInTheDocument();
    expect(updateSubmissionMock).not.toHaveBeenCalledWith(
      'submission-1',
      expect.objectContaining({ Status: 'approved' }),
    );
  });

  it('reviews, edits and approves a body-only Jobs AI version', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-1',
      Category: 'job_opportunity',
      Status: 'ai_edited',
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: '',
        Body: 'Administrative specialist III, College of Engineering',
      }),
    ]);

    renderEditPage();

    await screen.findByText('Administrative specialist III, College of Engineering');
    await user.click(screen.getByRole('button', { name: /use ai suggestion in final edit/i }));

    const finalEdit = screen.getByRole('region', { name: 'Final edit' });
    expect(within(finalEdit).queryByPlaceholderText('Enter headline...')).not.toBeInTheDocument();
    expect(screen.queryByText('No AI suggestion is available for final editing.')).not.toBeInTheDocument();

    const body = within(finalEdit).getByPlaceholderText('Enter body text...');
    await user.clear(body);
    await user.type(body, 'Administrative specialist III, College of Engineering, Boise');
    await user.tab();
    await user.click(within(finalEdit).getByRole('button', { name: /save and approve/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: '',
        Body: 'Administrative specialist III, College of Engineering, Boise',
        Headline_Case: 'sentence_case',
        Approve_For_Newsletter: true,
        Base_Staff_Revision_Id: null,
      });
    });
  });

  it('opens a newly generated body-only Jobs suggestion before versions reload', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Category: 'job_opportunity',
      Status: 'ai_edited',
    }));
    listEditVersionsMock.mockResolvedValue([]);
    triggerAIEditMock.mockResolvedValue(makeAIResponse({
      Edited_Headline: '',
      Edited_Body: 'Academic advisor, College of Business and Economics',
    }));

    renderEditPage();

    await screen.findByText('Original campus headline');
    await user.click(screen.getByRole('button', { name: /tdr/i }));
    await screen.findByText('Academic advisor, College of Business and Economics');
    await user.click(screen.getByRole('button', { name: /use ai suggestion in final edit/i }));

    const finalEdit = screen.getByRole('region', { name: 'Final edit' });
    expect(within(finalEdit).getByPlaceholderText('Enter body text...')).toHaveValue(
      'Academic advisor, College of Business and Economics',
    );
    expect(screen.queryByText('No AI suggestion is available for final editing.')).not.toBeInTheDocument();
  });

  it('uses the original submission when an editor bypasses an existing AI suggestion', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: 'Unreviewed AI headline',
        Body: 'Unreviewed AI body.',
        Headline_Case: 'title_case',
      }),
    ]);

    renderEditPage();

    await screen.findByText('Unreviewed AI headline');
    await user.click(screen.getByRole('button', { name: 'Original' }));
    await user.click(screen.getByRole('button', { name: /use original in final edit/i }));

    const finalEdit = screen.getByRole('region', { name: 'Final edit' });
    expect(within(finalEdit).getByText('Starting point: Original submission')).toBeInTheDocument();
    expect(within(finalEdit).getByDisplayValue('Original campus headline')).toBeInTheDocument();
    expect(
      within(finalEdit).getByDisplayValue('Original body copy for the newsletter.'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /save and approve/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Original campus headline',
        Body: 'Original body copy for the newsletter.',
        Headline_Case: undefined,
        Approve_For_Newsletter: true,
        Base_Staff_Revision_Id: null,
      });
    });
  });

  describe('an AI result never replaces unsaved Final Edit text (#511)', () => {
    async function typeInFinalEdit(user: ReturnType<typeof userEvent.setup>, text: string) {
      await user.click(screen.getByRole('button', { name: 'Final Edit' }));
      const body = screen.getByPlaceholderText('Enter body text...');
      await user.clear(body);
      await user.type(body, text);
      await user.tab();
    }

    it('keeps text typed before an AI edit, and replaces it only when confirmed', async () => {
      const user = userEvent.setup();
      listEditVersionsMock
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([makeVersion()]);
      renderEditPage();
      await screen.findByText('Original campus headline');

      await typeInFinalEdit(user, 'Staff wording in progress.');
      await user.click(screen.getByRole('button', { name: /tdr/i }));

      expect(await screen.findByText(/Your unsaved Final Edit changes were kept/)).toBeInTheDocument();
      // The result is on the AI Suggested tab.
      expect(screen.getByText('AI edited body copy.')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: 'Final Edit' }));
      expect(screen.getByPlaceholderText('Enter body text...')).toHaveValue('Staff wording in progress.');

      await user.click(screen.getByRole('button', { name: 'AI Suggested' }));
      await user.click(screen.getByRole('button', { name: 'Use AI Suggestion in Final Edit' }));
      const dialog = await screen.findByRole('dialog');
      expect(dialog).toHaveTextContent('Replace your Final Edit changes?');
      await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
      await user.click(screen.getByRole('button', { name: 'Final Edit' }));
      expect(screen.getByPlaceholderText('Enter body text...')).toHaveValue('Staff wording in progress.');

      await user.click(screen.getByRole('button', { name: 'AI Suggested' }));
      await user.click(screen.getByRole('button', { name: 'Use AI Suggestion in Final Edit' }));
      await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Replace changes' }));
      expect(await screen.findByPlaceholderText('Enter body text...')).toHaveValue('AI edited body copy.');
    });

    it('keeps text typed while the AI is still running', async () => {
      const user = userEvent.setup();
      let finish: (value: AIEditResponse) => void = () => {};
      triggerAIEditMock.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
      renderEditPage();
      await screen.findByText('Original campus headline');

      await user.click(screen.getByRole('button', { name: /tdr/i }));
      await typeInFinalEdit(user, 'Typed while the AI ran.');
      finish(makeAIResponse());

      expect(await screen.findByText(/Your unsaved Final Edit changes were kept/)).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Final Edit' }));
      expect(screen.getByPlaceholderText('Enter body text...')).toHaveValue('Typed while the AI ran.');
    });

    it('asks before Continue without AI replaces typed text', async () => {
      const user = userEvent.setup();
      renderEditPage();
      await screen.findByText('Original campus headline');

      await typeInFinalEdit(user, 'Typed wording.');
      await user.click(screen.getByRole('button', { name: 'Original' }));
      await user.click(screen.getByRole('button', { name: 'Continue without AI' }));
      expect(await screen.findByRole('dialog')).toHaveTextContent('Replacing them with the original submission');
    });
  });

  it('saves and approves manual final edits with one action', async () => {
    const user = userEvent.setup();

    renderEditPage();

    await screen.findByText('Original campus headline');
    await user.click(screen.getByRole('button', { name: /final edit/i }));

    const headline = screen.getByPlaceholderText('Enter headline...');
    const body = screen.getByPlaceholderText('Enter body text...');

    await user.clear(headline);
    await user.type(headline, 'Manual final headline');
    await user.tab();
    await user.clear(body);
    await user.type(body, 'Manual final body.');
    await user.tab();
    await user.click(screen.getByRole('button', { name: /save and approve/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Manual final headline',
        Body: 'Manual final body.',
        Headline_Case: undefined,
        Approve_For_Newsletter: true,
        Base_Staff_Revision_Id: null,
      });
    });
    expect(
      await screen.findByText('Final version saved and approved for newsletter'),
    ).toBeInTheDocument();
  });

  it('keeps the immutable original beside the editable final version', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Headline: 'AI working headline',
        Body: 'AI working body.',
      }),
    ]);

    renderEditPage();

    await screen.findByText('AI working headline');
    await user.click(screen.getByRole('button', { name: /use ai suggestion in final edit/i }));

    const original = screen.getByRole('region', { name: 'Original submission' });
    const finalEdit = screen.getByRole('region', { name: 'Final edit' });
    expect(within(original).getByText('Original campus headline')).toBeInTheDocument();
    expect(within(original).getByText('Original body copy for the newsletter.')).toBeInTheDocument();
    expect(within(finalEdit).getByDisplayValue('AI working headline')).toBeInTheDocument();
    expect(within(finalEdit).getByDisplayValue('AI working body.')).toBeInTheDocument();
  });

  it('contains long unbroken original text inside its final-edit grid column', async () => {
    const user = userEvent.setup();
    const longUrl = `https://example.com/register/${'unbroken'.repeat(40)}`;
    const longHeadlineToken = `headline${'token'.repeat(40)}`;
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Original_Headline: longHeadlineToken,
      Original_Body: `Register at ${longUrl}`,
    }));
    listEditVersionsMock.mockResolvedValue([]);

    renderEditPage();

    await screen.findByText(/Register at https:\/\/example\.com\/register\//);
    await user.click(screen.getByRole('button', { name: 'Final Edit' }));

    const original = screen.getByRole('region', { name: 'Original submission' });
    const originalBody = within(original).getByText(/Register at https:\/\/example\.com\/register\//);
    const originalHeadline = within(original).getByText(new RegExp(longHeadlineToken.slice(0, 20)));
    expect(original).toHaveClass('min-w-0');
    expect(originalBody).toHaveClass('break-words');
    expect(originalHeadline).toHaveClass('break-words');
  });

  it('wraps long unbroken text in the original tab view', async () => {
    const longUrl = `https://example.com/register/${'unbroken'.repeat(40)}`;
    const longHeadlineToken = `headline${'token'.repeat(40)}`;
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Original_Headline: longHeadlineToken,
      Original_Body: `Register at ${longUrl}`,
    }));
    listEditVersionsMock.mockResolvedValue([]);

    renderEditPage();

    const body = await screen.findByText(/Register at https:\/\/example\.com\/register\//);
    const headline = screen.getByText(new RegExp(longHeadlineToken.slice(0, 20)));
    expect(body).toHaveClass('break-words');
    expect(headline).toHaveClass('break-words');
  });

  it('lists submitted links in display order inside the original reference panel', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Links: [
        {
          Id: 'link-2',
          Url: 'https://example.com/details',
          Anchor_Text: null,
          Display_Order: 1,
        },
        {
          Id: 'link-1',
          Url: 'https://example.com/register',
          Anchor_Text: 'Register now',
          Display_Order: 0,
        },
      ],
    }));
    listEditVersionsMock.mockResolvedValue([]);

    renderEditPage();

    await screen.findByText('Original campus headline');
    await user.click(screen.getByRole('button', { name: 'Final Edit' }));

    const original = screen.getByRole('region', { name: 'Original submission' });
    expect(within(original).getByText('Submitted links')).toBeInTheDocument();
    const links = within(original).getAllByRole('listitem');
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveTextContent('Register now — https://example.com/register');
    expect(links[1]).toHaveTextContent('https://example.com/details');
  });

  it('shows live CTA links while keeping destination fields separately editable', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-1',
      Links: [
        {
          Id: 'link-1',
          Url: 'https://example.com/register',
          Anchor_Text: 'Register now',
          Display_Order: 0,
        },
      ],
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Version_Type: 'editor_final',
        Headline: 'Final event headline',
        Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
      }),
    ]);

    renderEditPage();

    const preview = await screen.findByRole('region', { name: 'Newsletter body preview' });
    expect(within(preview).getByRole('link', { name: 'Register now' })).toHaveAttribute(
      'href',
      'https://example.com/register',
    );
    expect(screen.getByPlaceholderText('Enter body text...')).toHaveValue(
      'Reserve a seat. Register now.',
    );
    expect(screen.getByPlaceholderText('Enter body text...')).not.toHaveValue(
      expect.stringContaining('<a'),
    );

    await user.click(screen.getAllByRole('button', { name: 'Switch to email link' })[0]);
    await user.type(screen.getByLabelText('Email address'), 'events@uidaho.edu');
    const linkText = screen.getByLabelText("Link text (person's name or email address)");
    await user.clear(linkText);
    await user.type(linkText, 'UCM events');
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Final event headline',
        Body: 'Reserve a seat. <a href="mailto:events@uidaho.edu">UCM events</a>.',
        Headline_Case: 'sentence_case',
        Approve_For_Newsletter: false,
        Base_Staff_Revision_Id: null,
        Links: [
          {
            Url: 'mailto:events@uidaho.edu',
            Anchor_Text: 'UCM events',
            Display_Order: 0,
          },
        ],
      });
    });
  });

  it('keeps link metadata synchronized when CTA text is edited in the body', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-1',
      Links: [
        {
          Id: 'link-1',
          Url: 'https://example.com/register',
          Anchor_Text: 'Register now',
          Display_Order: 0,
        },
      ],
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Version_Type: 'editor_final',
        Headline: 'Final event headline',
        Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
      }),
    ]);

    renderEditPage();

    const body = await screen.findByPlaceholderText('Enter body text...');
    await user.clear(body);
    await user.type(body, 'Reserve a seat. Sign up today.');
    await user.tab();
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Final event headline',
        Body: (
          'Reserve a seat. '
          + '<a href="https://example.com/register">Sign up today</a>.'
        ),
        Headline_Case: 'sentence_case',
        Approve_For_Newsletter: false,
        Base_Staff_Revision_Id: null,
        Links: [
          {
            Url: 'https://example.com/register',
            Anchor_Text: 'Sign up today',
            Display_Order: 0,
          },
        ],
      });
    });
  });

  it('updates the live link preview while body text is being typed', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-1',
      Links: [
        {
          Id: 'link-1',
          Url: 'https://example.com/register',
          Anchor_Text: 'Register now',
          Display_Order: 0,
        },
      ],
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Version_Type: 'editor_final',
        Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
      }),
    ]);

    renderEditPage();

    const preview = await screen.findByRole('region', { name: 'Newsletter body preview' });
    const body = screen.getByPlaceholderText('Enter body text...');
    await user.type(body, ' Updated');

    expect(preview).toHaveTextContent('Reserve a seat. Register now. Updated');
  });

  it('blocks a save that would silently drop a link, then saves once it is cleared', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-1',
      Links: [
        {
          Id: 'link-1',
          Url: 'https://example.com/register',
          Anchor_Text: 'Register now',
          Display_Order: 0,
        },
      ],
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Version_Type: 'editor_final',
        Headline: 'Final event headline',
        Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
      }),
    ]);

    renderEditPage();

    const body = await screen.findByPlaceholderText('Enter body text...');
    await user.clear(body);
    await user.type(body, 'Reserve a seat.');
    await user.tab();
    expect(screen.getByRole('status')).toHaveTextContent("These words aren't in the body");
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    expect(await screen.findByText(/Link text "Register now" isn't in the body/)).toBeInTheDocument();
    expect(saveEditorFinalMock).not.toHaveBeenCalled();

    await user.clear(screen.getAllByLabelText('URL')[0]);
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Final event headline',
        Body: 'Reserve a seat.',
        Headline_Case: 'sentence_case',
        Approve_For_Newsletter: false,
        Base_Staff_Revision_Id: null,
        Links: [],
      });
    });
  });

  it('restores a removed link by retyping its words, without duplicating them (#397)', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Version_Type: 'editor_final',
        Headline: 'Final event headline',
        Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
      }),
    ]);

    renderEditPage();

    const body = await screen.findByPlaceholderText('Enter body text...');
    await user.clear(body);
    await user.type(body, 'Reserve a seat.');
    await user.tab();
    expect(screen.getByRole('status')).toHaveTextContent("These words aren't in the body");

    await user.type(body, ' Register now.');
    await user.tab();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
        Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
        Links: [{ Url: 'https://example.com/register', Anchor_Text: 'Register now', Display_Order: 0 }],
      }));
    });
  });

  describe('restoring a removed link (#397)', () => {
    const registerLink = {
      Id: 'link-1',
      Url: 'https://example.com/register',
      Anchor_Text: 'Register now',
      Display_Order: 0,
    };

    /** After Save Draft, the page reloads what the server now holds. */
    function serverSaves(headline: string) {
      saveEditorFinalMock.mockImplementation(async (_id, data) => {
        const saved = makeVersion({
          Id: 'version-saved',
          Version_Type: 'editor_final',
          Headline: headline,
          Body: data.Body,
        });
        getSubmissionMock.mockResolvedValue(makeSubmission({
          Working_Version_Id: 'version-saved',
          Staff_Revision_Id: 'version-saved',
          Links: (data.Links ?? []).map((link, index) => ({
            Id: `saved-${index}`,
            Url: link.Url,
            Anchor_Text: link.Anchor_Text ?? null,
            Display_Order: link.Display_Order ?? index,
          })),
        }));
        listEditVersionsMock.mockResolvedValue([saved]);
        return saved;
      });
    }

    it('puts the link words back with one click and keeps them through Save Draft and reload', async () => {
      const user = userEvent.setup();
      getSubmissionMock.mockResolvedValue(makeSubmission({
        Working_Version_Id: 'version-1',
        Links: [registerLink],
      }));
      listEditVersionsMock.mockResolvedValue([
        makeVersion({
          Version_Type: 'editor_final',
          Headline: 'Final event headline',
          Body: 'Reserve a seat. <a href="https://example.com/register">Register now</a>.',
        }),
      ]);
      serverSaves('Final event headline');

      renderEditPage();

      const body = await screen.findByPlaceholderText('Enter body text...');
      await user.clear(body);
      await user.type(body, 'Reserve a seat.');
      await user.tab();
      const link1 = screen.getByRole('group', { name: 'Link 1' });
      expect(within(link1).getByRole('status')).toHaveTextContent("These words aren't in the body");

      await user.click(within(link1).getByRole('button', { name: 'Add these words to the body' }));
      expect(body).toHaveValue('Reserve a seat. Register now');
      expect(within(link1).queryByRole('status')).not.toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: /save draft/i }));

      const savedBody = 'Reserve a seat. <a href="https://example.com/register">Register now</a>';
      await waitFor(() => {
        expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
          Body: savedBody,
          Links: [{ Url: 'https://example.com/register', Anchor_Text: 'Register now', Display_Order: 0 }],
        }));
      });

      // Reloaded from the saved version: words and link are still attached, once.
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter body text...')).toHaveValue('Reserve a seat. Register now');
      });
      expect(within(screen.getByRole('group', { name: 'Link 1' })).queryByRole('status'))
        .not.toBeInTheDocument();
      const preview = screen.getByRole('region', { name: 'Newsletter body preview' });
      expect(within(preview).getByRole('link', { name: 'Register now' }))
        .toHaveAttribute('href', 'https://example.com/register');

      await user.click(screen.getByRole('button', { name: /save draft/i }));
      await waitFor(() => expect(saveEditorFinalMock).toHaveBeenCalledTimes(2));
      expect(saveEditorFinalMock).toHaveBeenLastCalledWith('submission-1', expect.objectContaining({
        Body: savedBody,
        Base_Staff_Revision_Id: 'version-saved',
      }));
    });

    it('links words staff choose in the body when the AI dropped the link', async () => {
      const user = userEvent.setup();
      getSubmissionMock.mockResolvedValue(makeSubmission({
        Working_Version_Id: 'version-1',
        Links: [registerLink],
      }));
      listEditVersionsMock.mockResolvedValue([
        makeVersion({ Body: 'Reserve a seat for the fall forum today.' }),
      ]);

      renderEditPage();

      await screen.findByRole('button', { name: 'Final Edit' });
      await user.click(screen.getByRole('button', { name: 'Final Edit' }));
      const link1 = screen.getByRole('group', { name: 'Link 1' });
      expect(within(link1).getByLabelText('URL')).toHaveValue('https://example.com/register');
      expect(within(link1).getByRole('status')).toHaveTextContent("These words aren't in the body");

      const words = within(link1).getByLabelText(/Words to link the URL to/);
      await user.clear(words);
      await user.type(words, 'Reserve a seat');
      await user.tab();
      expect(screen.getByPlaceholderText('Enter body text...'))
        .toHaveValue('Reserve a seat for the fall forum today.');
      await user.click(screen.getByRole('button', { name: /save draft/i }));

      await waitFor(() => {
        expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
          Body: '<a href="https://example.com/register">Reserve a seat</a> for the fall forum today.',
          Links: [{ Url: 'https://example.com/register', Anchor_Text: 'Reserve a seat', Display_Order: 0 }],
        }));
      });
    });
  });

  it('keeps a link on its mention when staff type the same words earlier', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Version_Type: 'editor_final',
        Headline: 'Final event headline',
        Body: 'Questions? <a href="https://example.com/fair">Learn more</a>.',
      }),
    ]);

    renderEditPage();

    const body = await screen.findByPlaceholderText('Enter body text...');
    await user.type(body, 'Learn more about the fair. ', {
      initialSelectionStart: 0,
      initialSelectionEnd: 0,
    });
    await user.tab();
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
        Body: 'Learn more about the fair. Questions? <a href="https://example.com/fair">Learn more</a>.',
      }));
    });
  });

  it('lets staff choose which mention of repeated words gets the link', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({ Working_Version_Id: 'version-1' }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({
        Version_Type: 'editor_final',
        Headline: 'Library hours',
        Body: '<a href="mailto:library@uidaho.edu">The Library</a> is open late. Email the Library with questions.',
      }),
    ]);

    renderEditPage();

    const picker = await screen.findByLabelText(/These words appear 2 times/);
    const options = within(picker).getAllByRole('option');
    expect(options.map((option) => option.textContent)).toEqual([
      '1st: [The Library] is open late. Email the…',
      '2nd: …Library is open late. Email [the Library] with questions.',
    ]);
    expect(picker).toHaveValue('0');

    await user.selectOptions(picker, options[1]);
    expect(screen.getByRole('region', { name: 'Newsletter body preview' })).toContainHTML(
      'Email <a',
    );
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
        Body: 'The Library is open late. Email <a href="mailto:library@uidaho.edu">the Library</a> with questions.',
      }));
    });
  });

  it('sends the staff revision the view was loaded with', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
      Working_Version_Id: 'version-final',
      Staff_Revision_Id: 'version-final',
    }));
    listEditVersionsMock.mockResolvedValue([
      makeVersion({ Id: 'version-final', Version_Type: 'editor_final', Body: 'Saved body.' }),
    ]);

    renderEditPage();
    await screen.findByDisplayValue('Saved body.');
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
        Base_Staff_Revision_Id: 'version-final',
      }));
    });
  });

  describe('when someone else saved first', () => {
    const conflict = new ApiError(409, {
      message: 'Someone saved a newer version while you were editing.',
      Status: 'approved',
      Current_Revision: {
        Id: 'version-theirs',
        Headline: 'Their approved headline',
        Body: 'Their approved body.',
        Approved: true,
      },
    });

    async function saveIntoConflict(user: ReturnType<typeof userEvent.setup>) {
      getSubmissionMock.mockResolvedValue(makeSubmission({
        Working_Version_Id: 'version-mine',
        Staff_Revision_Id: 'version-mine',
      }));
      listEditVersionsMock.mockResolvedValue([
        makeVersion({ Id: 'version-mine', Version_Type: 'editor_final', Body: 'My earlier body.' }),
      ]);
      saveEditorFinalMock.mockRejectedValueOnce(conflict);
      renderEditPage();
      const body = await screen.findByPlaceholderText('Enter body text...');
      await user.clear(body);
      await user.type(body, 'My unsaved body.');
      await user.click(screen.getByRole('button', { name: /save draft/i }));
      return screen.findByRole('region', { name: 'Save conflict' });
    }

    it('shows their version beside the unsaved text without losing it', async () => {
      const user = userEvent.setup();
      const panel = await saveIntoConflict(user);

      expect(panel).toHaveTextContent('Nothing was saved');
      expect(within(panel).getByText('Newer saved version (approved)')).toBeInTheDocument();
      expect(within(panel).getByText('Their approved body.')).toBeInTheDocument();
      expect(within(panel).getByText('My unsaved body.')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Enter body text...')).toHaveValue('My unsaved body.');
    });

    it('saves the unsaved text over theirs only when asked', async () => {
      const user = userEvent.setup();
      const panel = await saveIntoConflict(user);

      await user.click(within(panel).getByRole('button', { name: 'Save mine instead' }));

      await waitFor(() => {
        expect(saveEditorFinalMock).toHaveBeenLastCalledWith('submission-1', expect.objectContaining({
          Body: 'My unsaved body.',
          Base_Staff_Revision_Id: 'version-theirs',
          Approve_For_Newsletter: false,
        }));
      });
      await waitFor(() => {
        expect(screen.queryByRole('region', { name: 'Save conflict' })).not.toBeInTheDocument();
      });
    });

    it('discards the unsaved text and reloads their version', async () => {
      const user = userEvent.setup();
      const panel = await saveIntoConflict(user);
      const loadsBefore = getSubmissionMock.mock.calls.length;

      await user.click(within(panel).getByRole('button', { name: 'Discard mine and load theirs' }));

      await waitFor(() => {
        expect(getSubmissionMock.mock.calls.length).toBeGreaterThan(loadsBefore);
      });
      expect(screen.queryByRole('region', { name: 'Save conflict' })).not.toBeInTheDocument();
      expect(saveEditorFinalMock).toHaveBeenCalledTimes(1);
    });
  });

  it('keeps the explicit draft action distinct from approval', async () => {
    const user = userEvent.setup();

    renderEditPage();

    await screen.findByText('Original campus headline');
    await user.click(screen.getByRole('button', { name: /final edit/i }));
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Original campus headline',
        Body: 'Original body copy for the newsletter.',
        Headline_Case: undefined,
        Approve_For_Newsletter: false,
        Base_Staff_Revision_Id: null,
      });
    });
    expect(
      await screen.findByText('Draft saved. Submission remains in review'),
    ).toBeInTheDocument();
  });

  describe('link fields (#505)', () => {
    const threeLinks = {
      Working_Version_Id: 'version-1',
      Links: [
        { Id: 'link-1', Url: 'https://example.com/register', Anchor_Text: 'Register now', Display_Order: 0 },
        { Id: 'link-2', Url: 'mailto:ana@example.edu', Anchor_Text: 'Ana Lopez', Display_Order: 1 },
        { Id: 'link-3', Url: 'mailto:events@example.edu', Anchor_Text: 'events@example.edu', Display_Order: 2 },
      ],
    };
    const linkedBody = 'Join us Friday. <a href="https://example.com/register">Register now</a>. '
      + 'Contact <a href="mailto:ana@example.edu">Ana Lopez</a> or '
      + '<a href="mailto:events@example.edu">events@example.edu</a>.';

    beforeEach(() => {
      getSubmissionMock.mockResolvedValue(makeSubmission(threeLinks));
      listEditVersionsMock.mockResolvedValue([
        makeVersion({ Version_Type: 'editor_final', Headline: 'Final headline', Body: linkedBody }),
      ]);
    });

    it('turns an email link into a web link when a web address is typed in its field', async () => {
      const user = userEvent.setup();
      renderEditPage();

      const email = (await screen.findAllByLabelText('Email address'))[0];
      await user.clear(email);
      await user.type(email, 'https://example.com/ana');
      expect(within(screen.getByRole('group', { name: 'Link 2' })).getByLabelText('URL'))
        .toHaveValue('https://example.com/ana');
      await user.click(screen.getByRole('button', { name: /save draft/i }));

      await waitFor(() => {
        expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
          Body: expect.stringContaining('<a href="https://example.com/ana">Ana Lopez</a>'),
          Links: [
            { Url: 'https://example.com/register', Anchor_Text: 'Register now', Display_Order: 0 },
            { Url: 'https://example.com/ana', Anchor_Text: 'Ana Lopez', Display_Order: 1 },
            { Url: 'mailto:events@example.edu', Anchor_Text: 'events@example.edu', Display_Order: 2 },
          ],
        }));
      });
    });

    it('blocks a save that would drop a link whose destination is not https or email', async () => {
      const user = userEvent.setup();
      renderEditPage();

      const url = (await screen.findAllByLabelText('URL'))[0];
      await user.clear(url);
      await user.type(url, 'www.example.com/tickets');
      expect(screen.getByText(/Web links must start with https:\/\//)).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: /save draft/i }));

      expect(await screen.findByText(
        /Link destination "www\.example\.com\/tickets" isn't a web address starting with https:\/\//,
      )).toBeInTheDocument();
      expect(saveEditorFinalMock).not.toHaveBeenCalled();
    });

    it('keeps a changed URL and new link text after the body was edited', async () => {
      const user = userEvent.setup();
      renderEditPage();

      const body = await screen.findByPlaceholderText('Enter body text...');
      await user.clear(body);
      await user.type(body, 'Join us Friday. Contact Ana Lopez or events@example.edu.');
      await user.tab();
      const link1 = screen.getByRole('group', { name: 'Link 1' });
      await user.clear(within(link1).getByLabelText('URL'));
      await user.type(within(link1).getByLabelText('URL'), 'https://example.com/tickets');
      const cta = within(link1).getByLabelText(/Words to link the URL to/);
      await user.clear(cta);
      await user.type(cta, 'Buy tickets');
      await user.tab();
      await user.click(screen.getByRole('button', { name: /save draft/i }));

      await waitFor(() => {
        expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
          Body: 'Join us Friday. Contact <a href="mailto:ana@example.edu">Ana Lopez</a> or '
            + '<a href="mailto:events@example.edu">events@example.edu</a>. '
            + '<a href="https://example.com/tickets">Buy tickets</a>',
          Links: expect.arrayContaining([
            { Url: 'https://example.com/tickets', Anchor_Text: 'Buy tickets', Display_Order: 0 },
          ]),
        }));
      });
    });

    it('lets staff add a fourth link and remove one', async () => {
      const user = userEvent.setup();
      renderEditPage();

      await screen.findByRole('group', { name: 'Link 3' });
      await user.click(screen.getByRole('button', { name: 'Remove link 3' }));
      expect(screen.queryByRole('group', { name: 'Link 3' })).not.toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Add a link' }));
      await user.click(screen.getByRole('button', { name: 'Add a link' }));
      const link3 = screen.getByRole('group', { name: 'Link 3' });
      await user.type(within(link3).getByLabelText('URL'), 'https://example.com/map');
      await user.type(within(link3).getByLabelText(/Words to link the URL to/), 'Join us Friday');
      await user.tab();
      const link4 = screen.getByRole('group', { name: 'Link 4' });
      await user.click(within(link4).getByRole('button', { name: 'Switch to email link' }));
      await user.type(within(link4).getByLabelText('Email address'), 'events@example.edu');
      await user.type(within(link4).getByLabelText(/Link text/), 'UCM events');
      await user.tab();
      await user.click(screen.getByRole('button', { name: /save draft/i }));

      await waitFor(() => {
        expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', expect.objectContaining({
          Body: '<a href="https://example.com/map">Join us Friday</a>. '
            + '<a href="https://example.com/register">Register now</a>. '
            + 'Contact <a href="mailto:ana@example.edu">Ana Lopez</a> or events@example.edu. '
            + '<a href="mailto:events@example.edu">UCM events</a>',
          Links: [
            { Url: 'https://example.com/register', Anchor_Text: 'Register now', Display_Order: 0 },
            { Url: 'mailto:ana@example.edu', Anchor_Text: 'Ana Lopez', Display_Order: 1 },
            { Url: 'https://example.com/map', Anchor_Text: 'Join us Friday', Display_Order: 2 },
            { Url: 'mailto:events@example.edu', Anchor_Text: 'UCM events', Display_Order: 3 },
          ],
        }));
      });
    });
  });

  it('shows load errors and lets staff return to the dashboard', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockRejectedValueOnce(new Error('Submission not found'));

    renderEditPage();

    expect(await screen.findByText('Submission not found')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /back to dashboard/i }));

    expect(screen.getByText('Dashboard route')).toBeInTheDocument();
  });
});
