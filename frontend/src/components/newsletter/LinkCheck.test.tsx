import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import LinkCheck from './LinkCheck';

describe('LinkCheck', () => {
  it('renders nothing for an item without links or problems', () => {
    const { container } = render(<LinkCheck body="Plain copy." findings={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('lists each link with an openable destination', () => {
    render(
      <LinkCheck
        body={'See <a href="https://www.uidaho.edu/events/fair">the fair page</a> or email '
          + '<a href="mailto:events@uidaho.edu">Events</a>.'}
        findings={[]}
      />,
    );
    const list = screen.getByRole('list', { name: 'Links in this item' });
    const destinations = within(list).getAllByRole('link');
    expect(destinations.map((link) => link.textContent)).toEqual([
      'www.uidaho.edu/events/fair',
      'events@uidaho.edu',
    ]);
    expect(destinations[0]).toHaveAttribute('href', 'https://www.uidaho.edu/events/fair');
    expect(destinations[0]).toHaveAttribute('target', '_blank');
    expect(destinations[1]).not.toHaveAttribute('target');
  });

  it('explains each problem the backend found', () => {
    render(
      <LinkCheck
        body="Buy tickets."
        findings={[
          {
            Kind: 'tracking_link',
            Text: 'Buy tickets',
            Href: 'https://urldefense.com/v3/__https://tix.example.com__',
            Suggested_Href: 'https://tix.example.com',
          },
          { Kind: 'unsafe_link', Text: 'here', Href: 'http://example.com', Suggested_Href: null },
          { Kind: 'bare_url', Text: null, Href: 'https://uidaho.edu/x', Suggested_Href: null },
          { Kind: 'missing_submitted_link', Text: null, Href: 'https://uidaho.edu/r', Suggested_Href: null },
        ]}
      />,
    );
    const problems = within(screen.getByRole('list', { name: 'Link problems' }))
      .getAllByRole('listitem')
      .map((item) => item.textContent);
    expect(problems).toEqual([
      '⚠ "Buy tickets" goes through an email security wrapper. Real address: https://tix.example.com',
      "⚠ \"here\" won't be clickable in Word: http://example.com isn't a secure web or email address.",
      '⚠ Web address written out as text: https://uidaho.edu/x. Link descriptive words instead.',
      "⚠ A submitted link isn't in this copy: https://uidaho.edu/r",
    ]);
  });
});
