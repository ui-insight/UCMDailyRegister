import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import ConfirmDialog from './ConfirmDialog';

it('contains focus, cancels on Escape, and restores the invoking control', async () => {
  const user = userEvent.setup();
  const confirm = vi.fn();
  function Fixture() {
    const [open, setOpen] = useState(false);
    return <>
      <button onClick={() => setOpen(true)}>Remove synthetic item</button>
      <ConfirmDialog open={open} title="Remove item?" description="The item will be removed."
        destructive onCancel={() => setOpen(false)} onConfirm={confirm} />
    </>;
  }
  const { container } = render(<Fixture />);
  const invoker = screen.getByRole('button', { name: 'Remove synthetic item' });
  await user.click(invoker);
  const cancel = screen.getByRole('button', { name: 'Cancel' });
  const accept = screen.getByRole('button', { name: 'Confirm' });
  expect(cancel).toHaveFocus();
  expect(container).toHaveAttribute('inert');
  await user.tab({ shift: true });
  expect(accept).toHaveFocus();
  await user.tab();
  expect(cancel).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(invoker).toHaveFocus();
  expect(container).not.toHaveAttribute('inert');
  expect(confirm).not.toHaveBeenCalled();
});

it('keeps stacked dialogs isolated and restores prior inert state', async () => {
  const user = userEvent.setup();
  const existing = document.createElement('aside');
  existing.setAttribute('inert', '');
  document.body.append(existing);
  function Fixture() {
    const [first, setFirst] = useState(false);
    const [second, setSecond] = useState(false);
    return <>
      <button onClick={() => setFirst(true)}>Open first</button>
      <ConfirmDialog open={first} title="First question" description="First consequence"
        confirmLabel="Open second" onCancel={() => setFirst(false)} onConfirm={() => setSecond(true)} />
      <ConfirmDialog open={second} title="Second question" description="Second consequence"
        cancelLabel="Cancel second" onCancel={() => setSecond(false)} onConfirm={vi.fn()} />
    </>;
  }
  const { container } = render(<Fixture />);
  await user.click(screen.getByRole('button', { name: 'Open first' }));
  const firstDialog = screen.getByRole('dialog', { name: 'First question' });
  const openSecond = screen.getByRole('button', { name: 'Open second' });
  await user.click(openSecond);
  const secondDialog = screen.getByRole('dialog', { name: 'Second question' });
  expect(firstDialog.getAttribute('aria-labelledby')).not.toBe(secondDialog.getAttribute('aria-labelledby'));
  expect(firstDialog.closest('[inert]')).not.toBeNull();
  expect(screen.getByRole('button', { name: 'Cancel second' })).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('dialog', { name: 'Second question' })).not.toBeInTheDocument();
  expect(firstDialog.closest('[inert]')).toBeNull();
  expect(container).toHaveAttribute('inert');
  expect(openSecond).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(container).not.toHaveAttribute('inert');
  expect(existing).toHaveAttribute('inert');
  existing.remove();
});
