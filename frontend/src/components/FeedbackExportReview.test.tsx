import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { getFeedbackGitHubExportPreview, prepareFeedbackGitHubExport } from '../api/feedback';
import FeedbackExportReview from './FeedbackExportReview';

vi.mock('../api/feedback', () => ({
  getFeedbackGitHubExportPreview: vi.fn(), prepareFeedbackGitHubExport: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getFeedbackGitHubExportPreview).mockResolvedValue({
    Title: 'Synthetic example@example.com',
    Body: 'Call 208-555-0100 about the synthetic report.', Warnings: [],
  });
  vi.mocked(prepareFeedbackGitHubExport).mockResolvedValue({
    Title: 'Reviewed issue', Body: 'Safe issue text. Reviewed by staff.',
  });
});

it('requires review before preparing any external link or clipboard copy', async () => {
  const user = userEvent.setup();
  const copy = vi.spyOn(navigator.clipboard, 'writeText');
  render(<FeedbackExportReview feedbackId="synthetic" onClose={vi.fn()} />);
  const title = await screen.findByLabelText('Issue title');
  expect(screen.getByText(/Possible email address/)).toBeInTheDocument();
  expect(screen.getByText(/Possible phone number/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Prepare reviewed export' })).toBeDisabled();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(copy).not.toHaveBeenCalled();
  await user.clear(title);
  await user.type(title, 'Reviewed issue');
  const body = screen.getByLabelText('Issue body and context');
  await user.clear(body);
  await user.type(body, 'Safe issue text.');
  expect(screen.queryByText(/Possible email address/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Possible phone number/)).not.toBeInTheDocument();
  await user.click(screen.getByRole('checkbox'));
  await user.click(screen.getByRole('button', { name: 'Prepare reviewed export' }));
  await waitFor(() => expect(prepareFeedbackGitHubExport).toHaveBeenCalledWith('synthetic', {
    Title: 'Reviewed issue', Body: 'Safe issue text.', Review_Confirmed: true,
  }));
  const link = await screen.findByRole('link', { name: 'Open reviewed draft in GitHub' });
  const url = new URL(link.getAttribute('href')!);
  expect(url.searchParams.get('body')).toBe('Safe issue text. Reviewed by staff.');
  expect(link.getAttribute('href')).not.toContain('example%40example.com');
  await user.click(screen.getByRole('button', { name: 'Copy reviewed text' }));
  expect(copy).toHaveBeenCalledWith('Reviewed issue\n\nSafe issue text. Reviewed by staff.');
  await user.type(body, ' Changed.');
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Copy reviewed text' })).not.toBeInTheDocument();
});

it('preserves edits and prevents external actions when preparation fails', async () => {
  const user = userEvent.setup();
  vi.mocked(prepareFeedbackGitHubExport).mockRejectedValue(new Error('synthetic failure'));
  render(<FeedbackExportReview feedbackId="synthetic" onClose={vi.fn()} />);
  await screen.findByLabelText('Issue title');
  await user.click(screen.getByRole('checkbox'));
  await user.click(screen.getByRole('button', { name: 'Prepare reviewed export' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Your edits are preserved');
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Issue title')).toHaveValue('Synthetic example@example.com');
});
