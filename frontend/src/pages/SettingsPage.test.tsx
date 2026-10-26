import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import SettingsPage from './SettingsPage';
import * as schedule from '../api/schedule';

vi.mock('../api/client', () => ({ apiFetch: vi.fn(async (path: string) => path === '/schedule/configs' ? [] : null) }));
vi.mock('../api/schedule', () => ({
  getBlackoutDates: vi.fn(), getModeOverrides: vi.fn(), getCustomDates: vi.fn(),
  createBlackoutDate: vi.fn(), createModeOverride: vi.fn(), createCustomDate: vi.fn(),
  deleteBlackoutDate: vi.fn(), deleteModeOverride: vi.fn(), deleteCustomDate: vi.fn(),
}));
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('IntersectionObserver', class { observe() {} disconnect() {} });
  vi.mocked(schedule.getBlackoutDates).mockResolvedValue([{ Id: 'blackout', Blackout_Date: '2026-11-01', Newsletter_Type: null, Description: 'Synthetic closure', Is_Active: true }]);
  vi.mocked(schedule.getModeOverrides).mockResolvedValue([{ Id: 'override', Newsletter_Type: 'tdr', Override_Mode: 'winter_break', Start_Date: '2026-12-01', End_Date: '2026-12-02', Description: 'Synthetic override' }]);
  vi.mocked(schedule.getCustomDates).mockResolvedValue([{ Id: 'custom', Newsletter_Type: 'myui', Publish_Date: '2026-11-02', Description: 'Synthetic date' }]);
  vi.mocked(schedule.deleteBlackoutDate).mockResolvedValue(undefined);
  vi.mocked(schedule.deleteModeOverride).mockResolvedValue(undefined);
  vi.mocked(schedule.deleteCustomDate).mockResolvedValue(undefined);
});
afterEach(() => vi.unstubAllGlobals());

it.each([
  ['Remove blackout 2026-11-01', 'Remove blackout', 'deleteBlackoutDate', 'blackout', 'allows scheduling'],
  ['Remove TDR override 2026-12-01 to 2026-12-02', 'Remove override', 'deleteModeOverride', 'override', 'Normal schedule rules'],
  ['Remove MYUI publication date 2026-11-02', 'Remove date', 'deleteCustomDate', 'custom', 'Add the date again'],
] as const)('reviews %s and allows cancellation before any write', async (name, confirm, method, id, consequence) => {
  const user = userEvent.setup();
  render(<SettingsPage />);
  const invoker = await screen.findByRole('button', { name });
  await user.click(invoker);
  expect(screen.getByRole('dialog')).toHaveTextContent(consequence);
  expect(schedule[method]).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(invoker).toHaveFocus();
  expect(schedule[method]).not.toHaveBeenCalled();
  await user.click(invoker);
  await user.click(screen.getByRole('button', { name: confirm }));
  await waitFor(() => expect(schedule[method]).toHaveBeenCalledExactlyOnceWith(id));
  await waitFor(() => expect(screen.queryByRole('button', { name })).not.toBeInTheDocument());
});

it('announces a rejected deletion and keeps the affected record available', async () => {
  const user = userEvent.setup();
  vi.mocked(schedule.deleteBlackoutDate).mockRejectedValue(new Error('Synthetic deletion unavailable'));
  render(<SettingsPage />);
  const invoker = await screen.findByRole('button', { name: 'Remove blackout 2026-11-01' });
  await user.click(invoker);
  await user.click(screen.getByRole('button', { name: 'Remove blackout' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic deletion unavailable');
  expect(invoker).toBeInTheDocument();
  expect(invoker).toHaveFocus();
  expect(schedule.deleteBlackoutDate).toHaveBeenCalledTimes(1);
});
