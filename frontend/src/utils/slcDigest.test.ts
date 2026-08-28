import { describe, expect, it } from 'vitest';
import type { Submission } from '../types/submission';
import {
  buildDefaultPreamble,
  buildDigestDays,
  buildDigestHtml,
  buildDigestText,
  defaultDigestWeekStart,
  formatWeekRange,
  parseBodyFields,
  toDigestEvent,
  truncateDescription,
  weekStartOf,
} from './slcDigest';

function makeSubmission(overrides: Partial<Submission> = {}): Submission {
  return {
    Id: 'sub-1',
    Category: 'slc_event',
    Target_Newsletter: 'none',
    Original_Headline: 'Screen on the Green',
    Original_Body: [
      'Source date: 9/9/2026',
      'Start time: 7:00 PM',
      'Location: Tower Lawn',
      'Category: Student Affairs|Dept. of Student Involvement',
      'Description: Bring your blankets for an outdoor movie night on the lawn.',
      'Event page: https://events.uidaho.edu/screen-on-the-green',
      'Source: U of I events calendar (Trumba)',
    ].join('\n'),
    Submitter_Name: 'SLC event triage',
    Submitter_Email: 'slc-triage@uidaho.edu',
    Submitter_Notes: null,
    Assigned_Editor: null,
    Editorial_Notes: null,
    Survey_End_Date: null,
    Has_Image: false,
    Image_Path: null,
    Status: 'approved',
    Show_In_SLC_Calendar: true,
    Event_Classification: 'signature',
    Created_At: '2026-09-01T00:00:00Z',
    Updated_At: '2026-09-01T00:00:00Z',
    Links: [],
    Schedule_Requests: [],
    Occurrence_Dates: ['2026-09-09'],
    ...overrides,
  };
}

describe('weekStartOf / defaultDigestWeekStart', () => {
  it('returns the Monday of the containing week', () => {
    expect(weekStartOf(new Date('2026-09-09T12:00:00'))).toBe('2026-09-07'); // Wed
    expect(weekStartOf(new Date('2026-09-07T12:00:00'))).toBe('2026-09-07'); // Mon
    expect(weekStartOf(new Date('2026-09-13T12:00:00'))).toBe('2026-09-07'); // Sun
  });

  it('defaults the digest to next week', () => {
    expect(defaultDigestWeekStart(new Date('2026-09-09T12:00:00'))).toBe('2026-09-14');
  });
});

describe('formatWeekRange', () => {
  it('formats a same-month week', () => {
    expect(formatWeekRange('2026-09-07')).toBe('September 7 – 13, 2026');
  });

  it('spells out both months when the week crosses one', () => {
    expect(formatWeekRange('2026-09-28')).toBe('September 28 – October 4, 2026');
  });

  it('spells out both years when the week crosses one', () => {
    expect(formatWeekRange('2026-12-28')).toBe('December 28, 2026 – January 3, 2027');
  });
});

describe('parseBodyFields / toDigestEvent', () => {
  it('extracts details and the event link from a promoted Trumba body', () => {
    const event = toDigestEvent(makeSubmission());
    expect(event.time).toBe('7:00 PM');
    expect(event.location).toBe('Tower Lawn');
    expect(event.url).toBe('https://events.uidaho.edu/screen-on-the-green');
    expect(event.description).toBe(
      'Bring your blankets for an outdoor movie night on the lawn.',
    );
    expect(event.category).toBe('Student Affairs');
    expect(event.sponsor).toBeNull();
    expect(event.classification).toBe('signature');
  });

  it('matches labels case-insensitively (manual submit form writes "Start Time")', () => {
    const event = toDigestEvent(
      makeSubmission({
        Original_Body:
          'Event: Donor dinner\nLocation: 1912 Center\nStart Time: 6 p.m.'
          + '\nSponsor: Office of the President\nTicketed: Yes',
      }),
    );
    expect(event.time).toBe('6 p.m.');
    expect(event.location).toBe('1912 Center');
    expect(event.sponsor).toBe('Office of the President');
    expect(event.ticketed).toBe('Yes');
    expect(event.url).toBeNull();
    expect(event.description).toBeNull();
  });

  it('keeps URL values intact despite the colon in https://', () => {
    const fields = parseBodyFields('Event page: https://example.edu/a?b=1');
    expect(fields.get('event page')).toBe('https://example.edu/a?b=1');
  });

  it('prefers a submission link over the body event page', () => {
    const event = toDigestEvent(
      makeSubmission({
        Links: [
          { Id: 'l1', Url: 'https://uidaho.edu/preferred', Anchor_Text: null, Display_Order: 0 },
        ],
      }),
    );
    expect(event.url).toBe('https://uidaho.edu/preferred');
  });
});

describe('buildDigestDays', () => {
  it('places multi-day events on every occurrence day within the week', () => {
    const days = buildDigestDays(
      [
        makeSubmission({
          Id: 'multi',
          Occurrence_Dates: ['2026-09-08', '2026-09-09', '2026-09-10'],
        }),
      ],
      '2026-09-07',
    );
    expect(days.map((d) => d.date)).toEqual(['2026-09-08', '2026-09-09', '2026-09-10']);
    expect(days.every((d) => d.events.length === 1)).toBe(true);
  });

  it('drops occurrences outside the selected week and omits empty days', () => {
    const days = buildDigestDays(
      [
        makeSubmission({ Id: 'in', Occurrence_Dates: ['2026-09-11'] }),
        makeSubmission({ Id: 'out', Occurrence_Dates: ['2026-09-14'] }),
      ],
      '2026-09-07',
    );
    expect(days).toHaveLength(1);
    expect(days[0].date).toBe('2026-09-11');
    expect(days[0].events.map((e) => e.submission.Id)).toEqual(['in']);
  });

  it('orders a day by time with all-day events first', () => {
    const days = buildDigestDays(
      [
        makeSubmission({
          Id: 'evening',
          Original_Headline: 'Evening concert',
          Original_Body: 'Start time: 7:30 PM',
          Occurrence_Dates: ['2026-09-09'],
        }),
        makeSubmission({
          Id: 'morning',
          Original_Headline: 'Morning forum',
          Original_Body: 'Start time: 9:00 AM',
          Occurrence_Dates: ['2026-09-09'],
        }),
        makeSubmission({
          Id: 'allday',
          Original_Headline: 'Art exhibit',
          Original_Body: 'Start time: All day',
          Occurrence_Dates: ['2026-09-09'],
        }),
      ],
      '2026-09-07',
    );
    expect(days[0].events.map((e) => e.submission.Id)).toEqual([
      'allday',
      'morning',
      'evening',
    ]);
  });
});

describe('truncateDescription', () => {
  it('returns short text unchanged', () => {
    expect(truncateDescription('A short blurb.')).toBe('A short blurb.');
  });

  it('cuts long text at a word boundary with an ellipsis', () => {
    const truncated = truncateDescription('word '.repeat(100).trim());
    expect(truncated.length).toBeLessThanOrEqual(241);
    expect(truncated.endsWith('word…')).toBe(true);
  });
});

describe('buildDefaultPreamble', () => {
  it('summarizes the week with classification counts, deduping multi-day events', () => {
    const days = buildDigestDays(
      [
        makeSubmission({
          Id: 'multi-strategic',
          Event_Classification: 'strategic',
          Occurrence_Dates: ['2026-09-08', '2026-09-09'],
        }),
        makeSubmission({
          Id: 'signature',
          Occurrence_Dates: ['2026-09-10'],
        }),
        makeSubmission({
          Id: 'plain',
          Event_Classification: null,
          Occurrence_Dates: ['2026-09-11'],
        }),
      ],
      '2026-09-07',
    );
    const preamble = buildDefaultPreamble('2026-09-07', days);
    expect(preamble).toContain('Good morning,');
    expect(preamble).toContain('week of September 7 – 13, 2026');
    expect(preamble).toContain(
      'It features 3 events, including 1 strategic event and 1 signature event.',
    );
  });

  it('omits the classification clause when nothing is classified', () => {
    const days = buildDigestDays(
      [makeSubmission({ Event_Classification: null, Occurrence_Dates: ['2026-09-09'] })],
      '2026-09-07',
    );
    expect(buildDefaultPreamble('2026-09-07', days)).toContain('It features 1 event.');
  });
});

describe('buildDigestHtml / buildDigestText', () => {
  const submissions = [
    makeSubmission({
      Original_Headline: 'Vandals <Kickoff> & Rally',
      Occurrence_Dates: ['2026-09-09'],
    }),
  ];

  it('renders day headings, linked titles, and the classification tag inline-styled', () => {
    const html = buildDigestHtml('2026-09-07', buildDigestDays(submissions, '2026-09-07'));
    expect(html).toContain('Week of September 7 – 13, 2026');
    expect(html).toContain('Wednesday, September 9');
    expect(html).toContain('href="https://events.uidaho.edu/screen-on-the-green"');
    expect(html).toContain('[Signature]');
    expect(html).toContain('7:00 PM · Tower Lawn · Student Affairs');
    expect(html).toContain('Bring your blankets for an outdoor movie night on the lawn.');
    expect(html).toContain('>Event page</a>');
    expect(html).toContain('Vandals &lt;Kickoff&gt; &amp; Rally');
    expect(html).not.toContain('<Kickoff>');
    expect(html).not.toContain('class=');
  });

  it('includes the preamble as escaped paragraphs', () => {
    const html = buildDigestHtml(
      '2026-09-07',
      buildDigestDays(submissions, '2026-09-07'),
      'Good morning,\n\nA <warm> welcome to the week.',
    );
    expect(html).toContain('<p style="margin:0 0 12px;">Good morning,</p>');
    expect(html).toContain('A &lt;warm&gt; welcome to the week.');
    expect(html).not.toContain('<warm>');
  });

  it('renders the plain-text fallback with the preamble, details, and URLs', () => {
    const text = buildDigestText(
      '2026-09-07',
      buildDigestDays(submissions, '2026-09-07'),
      'Good morning,\n\nHere is the week ahead.',
    );
    expect(text).toContain('SENIOR LEADERSHIP COUNCIL EVENTS');
    expect(text).toContain('Good morning,\n\nHere is the week ahead.');
    expect(text).toContain('WEDNESDAY, SEPTEMBER 9');
    expect(text).toContain('Vandals <Kickoff> & Rally [Signature]');
    expect(text).toContain('7:00 PM · Tower Lawn · Student Affairs');
    expect(text).toContain('Bring your blankets for an outdoor movie night on the lawn.');
    expect(text).toContain('https://events.uidaho.edu/screen-on-the-green');
  });
});
