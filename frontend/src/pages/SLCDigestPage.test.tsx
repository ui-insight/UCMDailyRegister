import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { listSubmissions } from '../api/submissions';
import type { Submission } from '../types/submission';
import { getSubmitterRole } from '../utils/submitterRole';
import { addDaysToISODate } from '../utils/date';
import { defaultDigestWeekStart } from '../utils/slcDigest';
import SLCDigestPage from './SLCDigestPage';

vi.mock('../api/submissions', () => ({
  listSubmissions: vi.fn(),
}));

vi.mock('../utils/submitterRole', () => ({
  getSubmitterRole: vi.fn(),
}));

const listSubmissionsMock = vi.mocked(listSubmissions);
const getSubmitterRoleMock = vi.mocked(getSubmitterRole);

const nextWeekMonday = defaultDigestWeekStart();

function makeSubmission(overrides: Partial<Submission> = {}): Submission {
  return {
    Id: 'sub-1',
    Category: 'slc_event',
    Target_Newsletter: 'none',
    Original_Headline: 'Screen on the Green',
    Original_Body: [
      'Start time: 7:00 PM',
      'Location: Tower Lawn',
      'Event page: https://events.uidaho.edu/screen-on-the-green',
    ].join('\n'),
    Submitter_Name: 'SLC event triage',
    Submitter_Email: 'slc-triage@uidaho.edu',
    Submitter_Notes: null,
    Assigned_Editor: null,
    Editorial_Notes: null,
    Survey_End_Date: null,
    Has_Image: false,
    Image_Path: null,
    Status: 'approved',
    Show_In_SLC_Calendar: true,
    Event_Classification: 'strategic',
    Created_At: '2026-09-01T00:00:00Z',
    Updated_At: '2026-09-01T00:00:00Z',
    Links: [],
    Schedule_Requests: [],
    Occurrence_Dates: [addDaysToISODate(nextWeekMonday, 2)],
    ...overrides,
  };
}

function renderDigestPage() {
  return render(
    <MemoryRouter>
      <SLCDigestPage />
    </MemoryRouter>,
  );
}

class FakeClipboardItem {
  data: Record<string, Blob>;

  constructor(data: Record<string, Blob>) {
    this.data = data;
  }
}

describe('SLCDigestPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSubmitterRoleMock.mockReturnValue('slc');
    listSubmissionsMock.mockResolvedValue({ Items: [makeSubmission()], Total: 1 });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('blocks viewers without the slc or staff role', () => {
    getSubmitterRoleMock.mockReturnValue('public');
    renderDigestPage();
    expect(screen.getByText('Restricted page')).toBeInTheDocument();
    expect(listSubmissionsMock).not.toHaveBeenCalled();
  });

  it('fetches SLC calendar events for next week by default', async () => {
    renderDigestPage();
    await waitFor(() => {
      expect(listSubmissionsMock).toHaveBeenCalledWith({
        slc_calendar_only: true,
        date_from: nextWeekMonday,
        date_to: addDaysToISODate(nextWeekMonday, 6),
        limit: 200,
      });
    });
    expect(await screen.findByText('Screen on the Green')).toBeInTheDocument();
    expect(screen.getByText('7:00 PM · Tower Lawn')).toBeInTheDocument();
    expect(screen.getByText('strategic')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Screen on the Green' })).toHaveAttribute(
      'href',
      'https://events.uidaho.edu/screen-on-the-green',
    );
  });

  it('navigates to the previous week and refetches', async () => {
    renderDigestPage();
    await screen.findByText('Screen on the Green');

    await userEvent.click(screen.getByRole('button', { name: 'Previous week' }));

    await waitFor(() => {
      expect(listSubmissionsMock).toHaveBeenLastCalledWith({
        slc_calendar_only: true,
        date_from: addDaysToISODate(nextWeekMonday, -7),
        date_to: addDaysToISODate(nextWeekMonday, -1),
        limit: 200,
      });
    });
  });

  it('shows an empty state when the week has no SLC events', async () => {
    listSubmissionsMock.mockResolvedValue({ Items: [], Total: 0 });
    renderDigestPage();
    expect(await screen.findByText('No SLC events this week')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy for email' })).toBeDisabled();
  });

  it('prefills an editable preamble that summarizes the week', async () => {
    renderDigestPage();
    await screen.findByText('Screen on the Green');

    const textarea = screen.getByLabelText('Email preamble') as HTMLTextAreaElement;
    expect(textarea.value).toContain(
      'It features 1 event, including 1 strategic event.',
    );
  });

  it('copies the digest as rich text with the preamble and confirms', async () => {
    const write = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('ClipboardItem', FakeClipboardItem);
    Object.defineProperty(navigator, 'clipboard', {
      value: { write, writeText: vi.fn() },
      configurable: true,
    });

    renderDigestPage();
    await screen.findByText('Screen on the Green');

    await userEvent.click(screen.getByRole('button', { name: 'Copy for email' }));

    await waitFor(() => expect(write).toHaveBeenCalledTimes(1));
    const item = write.mock.calls[0][0][0] as FakeClipboardItem;
    const html = await item.data['text/html'].text();
    expect(html).toContain('href="https://events.uidaho.edu/screen-on-the-green"');
    expect(html).toContain('Good morning,');
    expect(await item.data['text/plain'].text()).toContain('Screen on the Green');
    expect(
      await screen.findByText('Copied — paste into your Outlook email'),
    ).toBeInTheDocument();
  });

  it('copies an edited preamble and resets it to the suggested text', async () => {
    const write = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('ClipboardItem', FakeClipboardItem);
    Object.defineProperty(navigator, 'clipboard', {
      value: { write, writeText: vi.fn() },
      configurable: true,
    });

    renderDigestPage();
    await screen.findByText('Screen on the Green');

    const textarea = screen.getByLabelText('Email preamble');
    await userEvent.clear(textarea);
    await userEvent.type(textarea, 'A custom note from Cami.');

    await userEvent.click(screen.getByRole('button', { name: 'Copy for email' }));
    await waitFor(() => expect(write).toHaveBeenCalledTimes(1));
    const item = write.mock.calls[0][0][0] as FakeClipboardItem;
    expect(await item.data['text/plain'].text()).toContain(
      'A custom note from Cami.',
    );

    await userEvent.click(
      screen.getByRole('button', { name: 'Reset to suggested text' }),
    );
    expect(
      (screen.getByLabelText('Email preamble') as HTMLTextAreaElement).value,
    ).toContain('Good morning,');
  });

  it('strikes canceled events in the preview and keeps them out of the copy', async () => {
    listSubmissionsMock.mockResolvedValue({
      Items: [
        makeSubmission(),
        makeSubmission({
          Id: 'sub-canceled',
          Original_Headline: 'Canceled Gala',
          Original_Body: ['Canceled: yes', 'Start time: 6:00 PM'].join('\n'),
          Event_Classification: null,
        }),
      ],
      Total: 2,
    });
    const write = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('ClipboardItem', FakeClipboardItem);
    Object.defineProperty(navigator, 'clipboard', {
      value: { write, writeText: vi.fn() },
      configurable: true,
    });

    renderDigestPage();
    await screen.findByText('Canceled Gala');

    expect(screen.getByText('Canceled — not emailed')).toBeInTheDocument();
    expect(screen.getByText(/1 event this week/)).toBeInTheDocument();
    expect(
      (screen.getByLabelText('Email preamble') as HTMLTextAreaElement).value,
    ).toContain('It features 1 event');

    await userEvent.click(screen.getByRole('button', { name: 'Copy for email' }));
    await waitFor(() => expect(write).toHaveBeenCalledTimes(1));
    const item = write.mock.calls[0][0][0] as FakeClipboardItem;
    expect(await item.data['text/html'].text()).not.toContain('Canceled Gala');
    expect(await item.data['text/plain'].text()).not.toContain('Canceled Gala');
  });

  it('falls back to plain text when rich clipboard writes are unavailable', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderDigestPage();
    await screen.findByText('Screen on the Green');

    await userEvent.click(screen.getByRole('button', { name: 'Copy for email' }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    expect(writeText.mock.calls[0][0]).toContain('SENIOR LEADERSHIP COUNCIL EVENTS');
    expect(
      await screen.findByText(
        'Copied as plain text (this browser cannot copy formatting)',
      ),
    ).toBeInTheDocument();
  });
});
