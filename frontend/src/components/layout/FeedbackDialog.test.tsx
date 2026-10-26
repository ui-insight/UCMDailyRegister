import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import FeedbackDialog from './FeedbackDialog';
import type { FeedbackContext } from '../../utils/feedback';

vi.mock('../../api/feedback', () => ({ createFeedback: vi.fn() }));

it('contains focus and preserves an unfinished report across Escape and reopening', async () => {
  const user = userEvent.setup();
  function Fixture() {
    const [open, setOpen] = useState(false);
    return <><button onClick={() => setOpen(true)}>Report issue</button>
      <FeedbackDialog open={open} context={{} as FeedbackContext} onClose={() => setOpen(false)} />
    </>;
  }
  const { container } = render(<Fixture />);
  const invoker = screen.getByRole('button', { name: 'Report issue' });
  await user.click(invoker);
  const summary = screen.getByLabelText('Short summary');
  expect(summary).toHaveFocus();
  await user.type(summary, 'Synthetic test report');
  await user.type(screen.getByLabelText('Details'), 'Synthetic steps to reproduce');
  expect(container).toHaveAttribute('inert');
  screen.getByRole('button', { name: 'Submit Feedback' }).focus();
  await user.tab();
  expect(screen.getByRole('button', { name: 'Bug' })).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(invoker).toHaveFocus();
  expect(container).not.toHaveAttribute('inert');
  await user.click(invoker);
  expect(screen.getByLabelText('Short summary')).toHaveValue('Synthetic test report');
  expect(screen.getByLabelText('Details')).toHaveValue('Synthetic steps to reproduce');
});
