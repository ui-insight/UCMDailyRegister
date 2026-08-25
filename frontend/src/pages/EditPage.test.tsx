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

  it('edits and approves an AI suggestion directly from Live View', async () => {
    const user = userEvent.setup();
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
      });
    });
  });

  it('keeps Live View changes when continuing to Final Edit', async () => {
    const user = userEvent.setup();
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

  it('edits and approves a body-only Jobs suggestion directly from Live View', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
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
      });
    });
  });

  it('keeps CTA links synchronized while editing an AI suggestion in Live View', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
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
      });
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
      });
    });
    expect(
      await screen.findByText('Final version saved and approved for newsletter'),
    ).toBeInTheDocument();
  });

  it('keeps the immutable original beside the editable final version', async () => {
    const user = userEvent.setup();
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

  it('does not preserve a removed CTA as hidden link metadata', async () => {
    const user = userEvent.setup();
    getSubmissionMock.mockResolvedValue(makeSubmission({
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
    await user.click(screen.getByRole('button', { name: /save draft/i }));

    await waitFor(() => {
      expect(saveEditorFinalMock).toHaveBeenCalledWith('submission-1', {
        Headline: 'Final event headline',
        Body: 'Reserve a seat.',
        Headline_Case: 'sentence_case',
        Approve_For_Newsletter: false,
        Links: [],
      });
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
      });
    });
    expect(
      await screen.findByText('Draft saved. Submission remains in review'),
    ).toBeInTheDocument();
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
