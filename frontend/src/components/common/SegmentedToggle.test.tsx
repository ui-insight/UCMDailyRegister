import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import SegmentedToggle from './SegmentedToggle';

it('exposes the group, announces selection, and supports native keyboard activation', async () => {
  const user = userEvent.setup();
  function Fixture() {
    const [value, setValue] = useState('all');
    return <SegmentedToggle options={[{value:'all',label:'All'}, {value:'review',label:'Review'}]}
      value={value} onChange={setValue} ariaLabel="Synthetic queue" />;
  }
  render(<Fixture />);
  expect(screen.getByRole('group', { name: 'Synthetic queue' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'true');
  await user.tab();
  await user.tab();
  await user.keyboard(' ');
  expect(screen.getByRole('button', { name: 'Review' })).toHaveFocus();
  expect(screen.getByRole('button', { name: 'Review' })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'false');
});
