import { useState } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import useConfirmAction from './useConfirmAction';

function Fixture({ action }: { action: () => Promise<unknown> }) {
  const { requestConfirmation, confirmationDialog } = useConfirmAction();
  return <>
    <button onClick={() => requestConfirmation({ title: 'Remove synthetic record?',
      description: 'The saved record will be removed. Recreate it to restore it.',
      confirmLabel: 'Remove record', action })}>Review removal</button>
    {confirmationDialog}
  </>;
}

it('cancels without writing, locks duplicate requests, and cannot dismiss an in-flight save', async () => {
  const user = userEvent.setup();
  let finish!: () => void;
  const action = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
  const { container } = render(<Fixture action={action} />);
  const invoker = screen.getByRole('button', { name: 'Review removal' });
  await user.click(invoker);
  await user.keyboard('{Escape}');
  expect(action).not.toHaveBeenCalled();
  expect(invoker).toHaveFocus();
  await user.click(invoker);
  const confirm = screen.getByRole('button', { name: 'Remove record' });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  expect(action).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent('Saving');
  await user.keyboard('{Escape}{Tab}');
  expect(screen.getByRole('dialog')).toHaveFocus();
  expect(container).toHaveAttribute('inert');
  await act(async () => finish());
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(invoker).toHaveFocus();
});

it('announces a failed save, keeps the record-specific review, and permits a retry', async () => {
  const user = userEvent.setup();
  const action = vi.fn().mockRejectedValueOnce(new Error('Synthetic service unavailable'))
    .mockResolvedValueOnce(undefined);
  render(<Fixture action={action} />);
  await user.click(screen.getByRole('button', { name: 'Review removal' }));
  await user.click(screen.getByRole('button', { name: 'Remove record' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic service unavailable');
  expect(screen.getByRole('dialog')).toHaveAccessibleName('Remove synthetic record?');
  await user.click(screen.getByRole('button', { name: 'Remove record' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(action).toHaveBeenCalledTimes(2);
});

it('returns focus to main content when a successful removal deletes its invoker', async () => {
  const user = userEvent.setup();
  function RemovalFixture() {
    const [present, setPresent] = useState(true);
    const { requestConfirmation, confirmationDialog } = useConfirmAction();
    return <main aria-label="Synthetic workspace">
      {present && <button onClick={() => requestConfirmation({ title: 'Remove item?',
        description: 'Recreate the item to restore it.', confirmLabel: 'Remove item',
        action: async () => setPresent(false) })}>Review item</button>}
      {confirmationDialog}
    </main>;
  }
  render(<RemovalFixture />);
  await user.click(screen.getByRole('button', { name: 'Review item' }));
  await user.click(screen.getByRole('button', { name: 'Remove item' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(screen.getByRole('main')).toHaveFocus();
});
