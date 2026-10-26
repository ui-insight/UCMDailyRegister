import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import Button from './Button';

import css from '../../index.css?raw';
function luminance(hex: string) {
  const linear = hex.slice(1).match(/../g)!.map((part) => {
    const channel = parseInt(part, 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
}
function color(token: string) {
  if (token === 'white') return '#FFFFFF';
  const value = css.match(new RegExp(`--color-${token}:\\s*(#[A-Fa-f0-9]{6})`))?.[1];
  if (!value) throw new Error(`Missing theme token ${token}`);
  return value;
}
it.each(['primary', 'success'] as const)('%s text meets the AA normal-text floor in default and hover states', (variant) => {
  render(<Button variant={variant}>Synthetic action</Button>);
  const classes = screen.getByRole('button').className.split(' ');
  const foreground = classes.find((token) => token.startsWith('text-') && token !== 'text-sm')!.slice(5);
  const base = classes.find((token) => token.startsWith('bg-'))!.slice(3);
  const hover = classes.find((token) => token.startsWith('hover:bg-'))?.slice(9) ?? base;
  for (const background of [base, hover]) {
    const [dark, light] = [luminance(color(foreground)), luminance(color(background))].sort((a, b) => a - b);
    expect((light + 0.05) / (dark + 0.05)).toBeGreaterThanOrEqual(4.5);
  }
});

it('supports keyboard activation and skips disabled controls', async () => {
  const user = userEvent.setup();
  const action = vi.fn();
  render(<><Button disabled onClick={action}>Unavailable</Button><Button onClick={action}>Available</Button></>);
  await user.tab();
  expect(screen.getByRole('button', { name: 'Available' })).toHaveFocus();
  await user.keyboard('{Enter} ');
  expect(action).toHaveBeenCalledTimes(2);
  await user.click(screen.getByRole('button', { name: 'Unavailable' }));
  expect(action).toHaveBeenCalledTimes(2);
});
