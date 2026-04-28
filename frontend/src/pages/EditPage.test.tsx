import { render, screen, waitFor } from '@testing-library/react';
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

  it('prefers the latest editor final version when one exists', async () => {
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

  it('accepts the latest AI version as the final edit', async () => {
    const user = userEvent.setup();
    const aiVersion = makeVersion({
      Headline: 'Accepted AI headline',
      Body: 'Accepted AI body.',
      Headline_Case: 'title_case',
    });
    listEditVersionsMock.mockResolvedValue([aiVersion]);

    renderEditPage();

    await screen.findByText('Accepted AI headline');
    await user.click(screen.getByRole('button', { name: /accept ai edit/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Accepted AI headline',
        Body: 'Accepted AI body.',
        Headline_Case: 'title_case',
      });
    });
    expect(await screen.findByText('Edit accepted and finalized')).toBeInTheDocument();
  });

  it('saves manual final edits from the editor tab', async () => {
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
    await user.click(screen.getByRole('button', { name: /save final version/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Manual final headline',
        Body: 'Manual final body.',
        Headline_Case: undefined,
      });
    });
    expect(await screen.findByText('Final version saved')).toBeInTheDocument();
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
