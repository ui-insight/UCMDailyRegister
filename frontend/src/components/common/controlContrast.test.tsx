import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import css from '../../index.css?raw';
import SegmentedToggle from './SegmentedToggle';
import Pill from './Pill';

function luminance(hex: string) {
  const channels = hex.slice(1).match(/../g)!.map((part) => {
    const value = parseInt(part, 16) / 255;
    return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4;
  });
  return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
}
function color(token: string) {
  if (token === 'white') return '#FFFFFF';
  const value = css.match(new RegExp(`--color-${token}:\\s*(#[a-fA-F0-9]{6})`))?.[1];
  if (!value) throw new Error(`Missing color token ${token}`);
  return value;
}
function contrast(foreground: string, background: string) {
  const [dark, light] = [luminance(color(foreground)), luminance(color(background))].sort((a, b) => a - b);
  return (light + .05) / (dark + .05);
}
function textPair(element: HTMLElement) {
  const classes = element.className.split(' ');
  const background = classes.find((name) => name.startsWith('bg-'))!.slice(3);
  const foreground = classes.find((name) => /^text-(ui-|status-|white)/.test(name))!.slice(5);
  return contrast(foreground, background);
}

it('keeps selected segmented-control text above the normal-text contrast floor', () => {
  render(<SegmentedToggle options={[{ value: 'all', label: 'All' }]} value="all" onChange={() => {}} ariaLabel="Filter" />);
  expect(textPair(screen.getByRole('button', { name: 'All' }))).toBeGreaterThanOrEqual(4.5);
});
describe('supported semantic pairings', () => {
  it.each(['info', 'edited', 'warning', 'success', 'attention', 'error', 'muted', 'gold', 'clearwater'] as const)('%s pill retains accessible text contrast', (tone) => {
    render(<Pill tone={tone}>Synthetic status</Pill>);
    expect(textPair(screen.getByText('Synthetic status'))).toBeGreaterThanOrEqual(4.5);
  });
  it.each(['info', 'edited', 'warning', 'success', 'attention', 'error', 'muted'])('%s strong fill supports white text', (tone) => {
    expect(contrast('white', `status-${tone}-800`)).toBeGreaterThanOrEqual(4.5);
  });
});

it('provides sufficient field-boundary contrast on supported light surfaces', () => {
  // The control border is an alias to muted-500. Contrast is measured against
  // white and the muted-100 read-only surface, not inferred from token names.
  expect(css).toContain('--control-border: var(--color-status-muted-500)');
  expect(contrast('status-muted-500', 'white')).toBeGreaterThanOrEqual(3);
  expect(contrast('status-muted-500', 'status-muted-100')).toBeGreaterThanOrEqual(3);
});
