import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getFeedbackGitHubExport,
  listFeedback,
  retryFeedbackNotification,
  updateFeedback,
} from '../api/feedback';
import type { ProductFeedback } from '../types/feedback';
import FeedbackPage from './FeedbackPage';

vi.mock('../api/feedback', () => ({
  getFeedbackGitHubExport: vi.fn(),
  listFeedback: vi.fn(),
  retryFeedbackNotification: vi.fn(),
  updateFeedback: vi.fn(),
}));

vi.mock('../utils/submitterRole', () => ({
  getSubmitterRole: () => 'staff',
}));

const getFeedbackGitHubExportMock = vi.mocked(getFeedbackGitHubExport);
const listFeedbackMock = vi.mocked(listFeedback);
const retryFeedbackNotificationMock = vi.mocked(retryFeedbackNotification);
const updateFeedbackMock = vi.mocked(updateFeedback);

function makeFeedback(overrides: Partial<ProductFeedback> = {}): ProductFeedback {
  return {
    Id: 'feedback-1',
    Feedback_Type: 'bug',
    Summary: 'Dashboard filter is confusing',
    Details: 'I expected the filter to keep my selection.',
    Contact_Email: 'editor@uidaho.edu',
    Submitter_Role: 'staff',
    Route: '/dashboard',
    App_Environment: 'test',
    Host: 'localhost:5173',
    Browser: 'vitest',
    Viewport: '1280x720',
    Status: 'new',
    GitHub_URL: null,
    Notification_Status: 'disabled',
    Notification_Attempts: 0,
    Notification_Sent_At: null,
    Notification_Last_Error: null,
    Created_At: '2026-07-20T12:00:00Z',
    Updated_At: '2026-07-20T12:00:00Z',
    ...overrides,
  };
}

function renderFeedbackPage() {
  return render(
    <MemoryRouter>
      <FeedbackPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  listFeedbackMock.mockResolvedValue([makeFeedback()]);
  retryFeedbackNotificationMock.mockResolvedValue(makeFeedback());
  updateFeedbackMock.mockResolvedValue(makeFeedback());
  getFeedbackGitHubExportMock.mockResolvedValue({ Title: 'Bug', Body: 'Details' });
});

describe('FeedbackPage notification state', () => {
  it('explains disabled external alerts without offering a retry', async () => {
    renderFeedbackPage();

    expect(await screen.findAllByText('Alerts off')).not.toHaveLength(0);
    expect(screen.getByText(/external alerts are disabled while UCM confirms/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /retry notification/i })).not.toBeInTheDocument();
  });

  it('shows a delivery failure and lets staff retry it', async () => {
    const user = userEvent.setup();
    const failed = makeFeedback({
      Notification_Status: 'failed',
      Notification_Attempts: 1,
      Notification_Last_Error: 'Approved channel is temporarily unavailable',
    });
    const sent = makeFeedback({
      Notification_Status: 'sent',
      Notification_Attempts: 2,
      Notification_Sent_At: '2026-07-20T12:05:00Z',
    });
    listFeedbackMock
      .mockResolvedValueOnce([failed])
      .mockResolvedValueOnce([sent]);
    retryFeedbackNotificationMock.mockResolvedValueOnce(sent);

    renderFeedbackPage();

    expect(await screen.findAllByText('Delivery failed')).not.toHaveLength(0);
    expect(screen.getByText('Approved channel is temporarily unavailable')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Retry notification' }));

    await waitFor(() => {
      expect(retryFeedbackNotificationMock).toHaveBeenCalledWith('feedback-1');
      expect(screen.getAllByText('Alert sent')).not.toHaveLength(0);
    });
  });
});
