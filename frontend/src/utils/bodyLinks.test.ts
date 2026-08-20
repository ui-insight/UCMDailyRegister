import { describe, expect, it } from 'vitest';
import {
  buildLinkedBody,
  prepareBodyForEditing,
  synchronizeBodyWithLinkLabel,
  synchronizeLinksWithBodyChange,
} from './bodyLinks';

describe('body link editing', () => {
  it('repairs the duplicated anchor pattern from Joy\'s dev submission', () => {
    const editable = prepareBodyForEditing(
      'Participants receive a book. Sign up, or email '
        + '<a href="mailto:nikkihodge@uidaho.edu">Nikki Hodge</a>.\n'
        + '<a href="https://example.com/study">sign up</a>',
      [
        {
          Url: 'https://example.com/study',
          Anchor_Text: 'sign up',
          Display_Order: 1,
        },
      ],
    );

    expect(editable.body).toBe('Participants receive a book. Sign up, or email Nikki Hodge.');
    expect(editable.links).toEqual([
      {
        Url: 'mailto:nikkihodge@uidaho.edu',
        Anchor_Text: 'Nikki Hodge',
        Display_Order: 0,
      },
      {
        Url: 'https://example.com/study',
        Anchor_Text: 'sign up',
        Display_Order: 1,
      },
    ]);

    const rebuilt = buildLinkedBody(editable.body, editable.links);
    expect(rebuilt).toContain('<a href="https://example.com/study">Sign up</a>');
    expect(rebuilt.match(/sign up/gi)).toHaveLength(1);
    expect(rebuilt).not.toMatch(/\n<a href="https:\/\/example\.com\/study">/);
  });

  it('deduplicates embedded and stored links by normalized destination', () => {
    const editable = prepareBodyForEditing(
      'Read <a href="https://example.com/details">event details</a>.',
      [
        {
          Url: 'https://example.com/details',
          Anchor_Text: 'Learn more',
          Display_Order: 0,
        },
      ],
    );

    expect(editable.links).toHaveLength(1);
    expect(editable.links[0].Anchor_Text).toBe('event details');
  });

  it('deduplicates equivalent destinations when one URL contains encoded spaces', () => {
    const editable = prepareBodyForEditing(
      'Additional details are available on the '
        + '<a href="https://example.com/Inside%20UI/details">committee page</a>.',
      [
        {
          Url: 'https://example.com/Inside UI/details',
          Anchor_Text: 'University Curriculum Committee Inside U of I page',
          Display_Order: 0,
        },
      ],
    );

    expect(editable.links).toEqual([
      {
        Url: 'https://example.com/Inside%20UI/details',
        Anchor_Text: 'committee page',
        Display_Order: 0,
      },
    ]);
    expect(buildLinkedBody(editable.body, editable.links)).toBe(
      'Additional details are available on the '
        + '<a href="https://example.com/Inside%20UI/details">committee page</a>.',
    );
  });

  it('places unmatched stored CTA text into the editable body exactly once', () => {
    const editable = prepareBodyForEditing(
      'Explore the university sustainability initiatives.',
      [
        {
          Url: 'https://example.com/stars',
          Anchor_Text: 'Review the STARS Gold rating',
          Display_Order: 0,
        },
      ],
    );

    expect(editable.body).toBe(
      'Explore the university sustainability initiatives.\nReview the STARS Gold rating',
    );
    expect(buildLinkedBody(editable.body, editable.links)).toBe(
      'Explore the university sustainability initiatives.\n'
        + '<a href="https://example.com/stars">Review the STARS Gold rating</a>',
    );
  });

  it('replaces link text in place when its link field is edited', () => {
    expect(synchronizeBodyWithLinkLabel(
      'Reserve a seat. Register now.',
      'Register now',
      'UCM events',
    )).toBe('Reserve a seat. UCM events.');
  });

  it('updates link metadata when its exact body segment is edited', () => {
    expect(synchronizeLinksWithBodyChange(
      'Reserve a seat. Register now.',
      'Reserve a seat. Sign up today.',
      [{ Url: 'https://example.com/register', Anchor_Text: 'Register now' }],
    )).toEqual([
      { Url: 'https://example.com/register', Anchor_Text: 'Sign up today' },
    ]);
  });
});
