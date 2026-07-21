import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import RichBody from './RichBody';

describe('RichBody', () => {
  it('renders https and email anchors as live links', () => {
    render(
      <RichBody text={'Read <a href="https://example.com">the guide</a> or <a href="mailto:help@uidaho.edu">email UCM</a>.'} />,
    );

    expect(screen.getByRole('link', { name: 'the guide' })).toHaveAttribute(
      'href',
      'https://example.com',
    );
    expect(screen.getByRole('link', { name: 'email UCM' })).toHaveAttribute(
      'href',
      'mailto:help@uidaho.edu',
    );
  });

  it('renders unsafe anchors as plain text', () => {
    render(<RichBody text={'Do not <a href="javascript:alert(1)">open this</a>.'} />);

    expect(screen.queryByRole('link', { name: 'open this' })).not.toBeInTheDocument();
    expect(screen.getByText(/open this/)).toBeInTheDocument();
  });
});
