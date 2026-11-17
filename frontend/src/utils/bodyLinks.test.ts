import { describe, expect, it } from 'vitest';
import {
  commitLinkLabel,
  duplicateLinks,
  findMentions,
  invalidLinks,
  linkedBodyForSave,
  linkSaveProblem,
  looksLikeWebAddress,
  resolvedLinkStart,
  unattachedLinks,
  buildLinkedBody,
  normalizedBodyLinks,
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
        Start: editable.body.indexOf('Nikki Hodge'),
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
        Start: editable.body.indexOf('committee page'),
      },
    ]);
    expect(buildLinkedBody(editable.body, editable.links)).toBe(
      'Additional details are available on the '
        + '<a href="https://example.com/Inside%20UI/details">committee page</a>.',
    );
  });

  it('does not inject unmatched stored CTA text into the editable body', () => {
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

    expect(editable.body).toBe('Explore the university sustainability initiatives.');
    expect(buildLinkedBody(editable.body, editable.links)).toBe(
      'Explore the university sustainability initiatives.',
    );
  });

  it('removes a legacy standalone anchor even when its label differs from the prose', () => {
    const editable = prepareBodyForEditing(
      'Discover why U of I is an AASHE STARS Gold-rated university.\n'
        + '<a href="https://example.com/stars">'
        + 'Association for the Advancement of Sustainability STARS Gold rated university'
        + '</a>',
      [
        {
          Url: 'https://example.com/stars',
          Anchor_Text: (
            'Association for the Advancement of Sustainability '
            + 'STARS Gold rated university'
          ),
          Display_Order: 0,
        },
      ],
    );

    expect(editable.body).toBe(
      'Discover why U of I is an AASHE STARS Gold-rated university.',
    );
  });

  it('uses the stored destination when a CTA keeps its text but its URL changes', () => {
    const editable = prepareBodyForEditing(
      'Visit the <a href="https://old.example.com">Inside U of I homepage</a>.',
      [
        {
          Url: 'https://new.example.com',
          Anchor_Text: 'Inside U of I homepage',
          Display_Order: 0,
        },
      ],
    );

    expect(editable.links).toEqual([
      {
        Url: 'https://new.example.com',
        Anchor_Text: 'Inside U of I homepage',
        Display_Order: 0,
        Start: editable.body.indexOf('Inside U of I homepage'),
      },
    ]);
  });

  it('does not resurrect a CTA that an editor removed from the body', () => {
    expect(buildLinkedBody(
      'Reserve a seat.',
      [{ Url: 'https://example.com/register', Anchor_Text: 'Register now' }],
    )).toBe('Reserve a seat.');
  });

  it('drops hidden link metadata when its anchor is absent from the body', () => {
    expect(normalizedBodyLinks(
      [{ Url: 'https://example.com/register', Anchor_Text: 'Register now' }],
      'Reserve a seat.',
    )).toEqual([]);
  });

  it('places a newly named link visibly into the body before serialization', () => {
    expect(synchronizeBodyWithLinkLabel(
      'Reserve a seat.',
      '',
      'Register now',
    )).toBe('Reserve a seat. Register now');
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
      {
        Url: 'https://example.com/register',
        Anchor_Text: 'Sign up today',
        Start: 'Reserve a seat. '.length,
      },
    ]);
  });

  it('keeps a link on the later mention when the same words appear earlier', () => {
    const source = 'Email the Library about hours. Questions? '
      + '<a href="mailto:library@uidaho.edu">Email the Library</a>.';
    const editable = prepareBodyForEditing(source);
    expect(buildLinkedBody(editable.body, editable.links)).toBe(source);
  });

  it('does not move a link when staff type the same words earlier', () => {
    const editable = prepareBodyForEditing('Questions? <a href="https://uidaho.edu/x">Learn more</a>.');
    const nextBody = `Learn more about the fair. ${editable.body}`;
    const links = synchronizeLinksWithBodyChange(editable.body, nextBody, editable.links);
    expect(buildLinkedBody(nextBody, links)).toBe(
      'Learn more about the fair. Questions? <a href="https://uidaho.edu/x">Learn more</a>.',
    );
  });

  it('keeps a link in place when text after it changes', () => {
    const editable = prepareBodyForEditing('Learn more. Then <a href="https://uidaho.edu/x">Learn more</a> again.');
    const nextBody = `${editable.body} Doors open at 6 p.m.`;
    const links = synchronizeLinksWithBodyChange(editable.body, nextBody, editable.links);
    expect(buildLinkedBody(nextBody, links)).toBe(
      'Learn more. Then <a href="https://uidaho.edu/x">Learn more</a> again. Doors open at 6 p.m.',
    );
  });

  it('links the mention staff choose', () => {
    const body = 'The Library is open late. Email the Library with questions.';
    const [first, second] = findMentions(body, 'the Library');
    expect([first, second]).toEqual([0, 'The Library is open late. Email '.length]);
    expect(buildLinkedBody(body, [
      { Url: 'mailto:library@uidaho.edu', Anchor_Text: 'the Library', Start: second },
    ])).toBe(
      'The Library is open late. Email <a href="mailto:library@uidaho.edu">the Library</a> with questions.',
    );
  });

  it('falls back to the first mention when the chosen one no longer matches', () => {
    const body = 'Register today. More text.';
    const link = { Url: 'https://uidaho.edu/r', Anchor_Text: 'Register', Start: 99 };
    expect(resolvedLinkStart(body, link)).toBe(0);
  });

  it('reports links whose words are missing from the body', () => {
    const links = [
      { Url: 'https://uidaho.edu/r', Anchor_Text: 'Register now' },
      { Url: 'https://uidaho.edu/x', Anchor_Text: 'event page' },
      { Url: '', Anchor_Text: 'unused' },
      { Url: 'mailto:', Anchor_Text: 'blank email slot' },
    ];
    expect(unattachedLinks('See the event page.', links)).toEqual([links[0]]);
  });

  // #505: a link whose destination wasn't https or an email address was
  // filtered out on save without a word, leaving blank link fields on reload.
  it('flags destinations that are neither https nor an email address', () => {
    const links = [
      { Url: 'https://uidaho.edu/r', Anchor_Text: 'Register' },
      { Url: 'www.uidaho.edu/events', Anchor_Text: 'events' },
      { Url: 'http://uidaho.edu/old', Anchor_Text: 'old page' },
      { Url: 'mailto:https://uidaho.edu/ana', Anchor_Text: 'Ana Lopez' },
      { Url: 'events@uidaho.edu', Anchor_Text: 'events team' },
      { Url: 'mailto:', Anchor_Text: 'blank email slot' },
      { Url: '', Anchor_Text: 'unused' },
    ];
    expect(invalidLinks(links)).toEqual([links[1], links[2], links[3]]);
    // normalizedBodyLinks drops exactly these, so saving must be blocked first.
    const body = 'Register for events, see the old page, or email Ana Lopez or the events team.';
    expect(normalizedBodyLinks(links, body).map((link) => link.Anchor_Text)).toEqual([
      'Register',
      'events team',
    ]);
    expect(linkSaveProblem(body, links)).toMatch(
      /^Link destination "www\.uidaho\.edu\/events", "http:\/\/uidaho\.edu\/old", "https:\/\/uidaho\.edu\/ana" isn't a web address starting with https:\/\//,
    );
  });

  it('keeps two phrases that link to the same destination (#521)', () => {
    const links = [
      { Url: 'https://uidaho.edu/r', Anchor_Text: 'Register' },
      { Url: 'https://uidaho.edu/r', Anchor_Text: 'sign up' },
    ];
    expect(duplicateLinks(links)).toEqual([]);
    expect(linkSaveProblem('Register or sign up.', links)).toBeNull();
    expect(linkedBodyForSave('Register or sign up.', links)).toBe(
      '<a href="https://uidaho.edu/r">Register</a> or <a href="https://uidaho.edu/r">sign up</a>.',
    );
  });

  it('flags a second link with the same words and destination', () => {
    const links = [
      { Url: 'https://uidaho.edu/r', Anchor_Text: 'Register' },
      { Url: 'https://UIDAHO.edu/r', Anchor_Text: 'register' },
    ];
    expect(duplicateLinks(links)).toEqual([links[1]]);
    expect(linkSaveProblem('Register now. Register later.', links)).toMatch(
      /^Link "register" repeats another link's words and destination/,
    );
  });

  describe('opening and saving without changes keeps the stored body (#521)', () => {
    const roundTrip = (
      stored: string,
      storedLinks: Array<{ Url: string; Anchor_Text: string | null; Display_Order?: number }> = [],
    ) => {
      const editable = prepareBodyForEditing(stored, storedLinks);
      return { editable, saved: linkedBodyForSave(editable.body, editable.links) };
    };

    it('keeps a call-to-action link on its own paragraph', () => {
      const stored = 'Join us Friday for the staff social.\n\n'
        + '<a href="https://example.edu/social">Register for the social</a>';
      const { editable, saved } = roundTrip(stored, [
        { Url: 'https://example.edu/social', Anchor_Text: 'Register for the social', Display_Order: 0 },
      ]);
      expect(editable.body).toBe('Join us Friday for the staff social.\n\nRegister for the social');
      expect(linkSaveProblem(editable.body, editable.links)).toBeNull();
      expect(saved).toBe(stored);
    });

    it('keeps a second link to the same destination', () => {
      const stored = 'Go <a href="https://example.edu/r">register</a> today.\n\n'
        + '<a href="https://example.edu/r">Sign up now</a>';
      const { editable, saved } = roundTrip(stored, [
        { Url: 'https://example.edu/r', Anchor_Text: 'register', Display_Order: 0 },
        { Url: 'https://example.edu/r', Anchor_Text: 'Sign up now', Display_Order: 1 },
      ]);
      expect(editable.links.map((link) => link.Anchor_Text)).toEqual(['register', 'Sign up now']);
      expect(linkSaveProblem(editable.body, editable.links)).toBeNull();
      expect(saved).toBe(stored);
    });

    it.each([
      ['an http:// link', 'http://example.edu/old'],
      ['a mailto: link with a subject', 'mailto:events@example.edu?subject=RSVP'],
    ])('reports %s instead of dropping it', (_label, href) => {
      const { editable } = roundTrip(`Questions? <a href="${href}">Contact the office</a>.`);
      expect(editable.links).toEqual([
        expect.objectContaining({ Url: href, Anchor_Text: 'Contact the office' }),
      ]);
      expect(linkSaveProblem(editable.body, editable.links)).toMatch(/^Link destination .* the link would be lost/);
    });

    it('reports an unsupported stored link that is not in the body', () => {
      const { editable } = roundTrip('Read the update.', [
        { Url: 'http://example.edu/update', Anchor_Text: 'the update', Display_Order: 0 },
      ]);
      expect(linkSaveProblem(editable.body, editable.links)).toMatch(/^Link destination/);
    });

    it('still removes the block older builds appended straight after the prose', () => {
      const { editable } = roundTrip(
        'Join us Friday.\n<a href="https://example.edu/social">Register for the social</a>',
      );
      expect(editable.body).toBe('Join us Friday.');
      expect(editable.links).toEqual([
        expect.objectContaining({ Url: 'https://example.edu/social', Start: undefined }),
      ]);
    });
  });

  it('flags links whose words overlap another link (PR #507 review)', () => {
    const overlapping = [
      { Url: 'https://example.edu/a', Anchor_Text: 'Register now' },
      { Url: 'https://example.edu/b', Anchor_Text: 'now' },
    ];
    expect(linkSaveProblem('Register now', overlapping)).toMatch(/^Link text "now" overlaps/);

    const competing = [
      { Url: 'https://example.edu/a', Anchor_Text: 'Register' },
      { Url: 'https://example.edu/b', Anchor_Text: 'Register' },
    ];
    expect(linkSaveProblem('Register today.', competing)).toMatch(/overlaps another link/);
    // A second mention gives the second link its own words.
    expect(linkSaveProblem('Register today. Register later.', competing)).toBeNull();
  });

  it('has no save problem when every link will be kept', () => {
    expect(linkSaveProblem('Register or email Ana Lopez.', [
      { Url: 'https://uidaho.edu/r', Anchor_Text: 'Register' },
      { Url: 'ana@uidaho.edu', Anchor_Text: 'Ana Lopez' },
      { Url: '', Anchor_Text: '' },
    ])).toBeNull();
  });

  it('tells a typed web address from an email address', () => {
    expect(looksLikeWebAddress('https://uidaho.edu')).toBe(true);
    expect(looksLikeWebAddress(' www.uidaho.edu')).toBe(true);
    expect(looksLikeWebAddress('ana@uidaho.edu')).toBe(false);
    expect(looksLikeWebAddress('ana')).toBe(false);
  });

  it('keeps a link restored from its link field through save and reload (#397)', () => {
    const removed = { Url: 'https://example.com/register', Anchor_Text: 'Register now' };
    // Staff deleted the words from the body; the link fields still hold them.
    const restored = commitLinkLabel('Reserve a seat.', { ...removed, Anchor_Text: '' }, 'Register now');
    const saved = buildLinkedBody(restored.body, [restored.link]);
    expect(saved).toBe('Reserve a seat. <a href="https://example.com/register">Register now</a>');

    const reloaded = prepareBodyForEditing(saved, [{ ...removed, Display_Order: 0 }]);
    expect(reloaded.body).toBe(restored.body);
    expect(linkSaveProblem(reloaded.body, reloaded.links)).toBeNull();
    expect(buildLinkedBody(reloaded.body, reloaded.links)).toBe(saved);
  });

  it('keeps every link in the body for editing, not just the first three', () => {
    const editable = prepareBodyForEditing(
      'See <a href="https://example.com/a">one</a>, <a href="https://example.com/b">two</a>, '
        + '<a href="mailto:c@example.edu">three</a> and <a href="https://example.com/d">four</a>.',
    );
    expect(editable.links.map((link) => link.Anchor_Text)).toEqual(['one', 'two', 'three', 'four']);
    expect(buildLinkedBody(editable.body, editable.links)).toContain(
      '<a href="https://example.com/d">four</a>',
    );
  });
});
