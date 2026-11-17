import { describe, expect, it } from 'vitest';
import {
  compareSectionItems,
  planAdjacentMove,
  planSubmissionMove,
  type PositionUpdate,
  type SectionOrderItem,
} from './builderOrder';

function submission(Id: string, Position: number, Section_Id = 'news'): SectionOrderItem {
  return { Id, Section_Id, Position, Final_Headline: `Story ${Id}`, Kind: 'submission' };
}

function imported(Id: string, Position: number, Section_Id = 'news'): SectionOrderItem {
  return { Id, Section_Id, Position, Final_Headline: `Import ${Id}`, Kind: 'recurring_message' };
}

/** Ids of a section in the order the updates put them. */
function orderOf(updates: PositionUpdate[], ids: string[]): string[] {
  const positions = new Map(updates.map((update) => [update.Id, update.Position]));
  return ids
    .filter((id) => positions.has(id))
    .sort((left, right) => (positions.get(left) ?? 0) - (positions.get(right) ?? 0));
}

describe('planSubmissionMove (#510)', () => {
  const abc = [submission('A', 0), submission('B', 1), submission('C', 2)];

  it('drops a downward drag where the indicator shows', () => {
    // Lower half of B: the indicator sits between B and C, index 2.
    const updates = planSubmissionMove(abc, 'A', 'news', 2);
    expect(orderOf(updates, ['A', 'B', 'C'])).toEqual(['B', 'A', 'C']);
  });

  it('drops a downward drag past the last card at the end', () => {
    const updates = planSubmissionMove(abc, 'A', 'news', 3);
    expect(orderOf(updates, ['A', 'B', 'C'])).toEqual(['B', 'C', 'A']);
  });

  it('drops an upward drag where the indicator shows', () => {
    const updates = planSubmissionMove(abc, 'C', 'news', 1);
    expect(orderOf(updates, ['A', 'B', 'C'])).toEqual(['A', 'C', 'B']);
  });

  it('changes nothing when dropped on its own slot', () => {
    // Before itself (lower half of the card above) or before the next card.
    expect(planSubmissionMove(abc, 'B', 'news', 1)).toEqual([]);
    expect(planSubmissionMove(abc, 'B', 'news', 2)).toEqual([]);
    expect(planSubmissionMove(abc, 'C', 'news', 3)).toEqual([]);
  });

  it('moves to another section and renumbers both', () => {
    const items = [...abc, submission('X', 0, 'kudos'), submission('Y', 1, 'kudos')];
    const updates = planSubmissionMove(items, 'B', 'kudos', 1);
    expect(updates).toEqual([
      { Id: 'A', Position: 0, Section_Id: 'news' },
      { Id: 'C', Position: 1, Section_Id: 'news' },
      { Id: 'X', Position: 0, Section_Id: 'kudos' },
      { Id: 'B', Position: 1, Section_Id: 'kudos' },
      { Id: 'Y', Position: 2, Section_Id: 'kudos' },
    ]);
  });

  it('keeps imported items in place and sends their positions too (#509)', () => {
    // news: A, event E, B
    const items = [submission('A', 0), imported('E', 1), submission('B', 2)];
    const updates = planSubmissionMove(items, 'A', 'news', 2);
    expect(updates).toEqual([
      { Id: 'E', Position: 0 },
      { Id: 'B', Position: 1, Section_Id: 'news' },
      { Id: 'A', Position: 2, Section_Id: 'news' },
    ]);
  });

  it('puts a submission after the last submission, before trailing imports', () => {
    const items = [
      submission('A', 0, 'kudos'),
      imported('E', 1, 'kudos'),
      submission('M', 0),
    ];
    const updates = planSubmissionMove(items, 'M', 'kudos', Number.MAX_SAFE_INTEGER);
    expect(orderOf(updates, ['A', 'E', 'M'])).toEqual(['A', 'M', 'E']);
  });

  it('puts a submission at the end of a section that has only imports', () => {
    const items = [imported('E', 0, 'events'), submission('M', 0)];
    const updates = planSubmissionMove(items, 'M', 'events', 0);
    expect(orderOf(updates, ['E', 'M'])).toEqual(['E', 'M']);
  });
});

describe('planAdjacentMove', () => {
  it('moves past an imported item next to it', () => {
    const items = [submission('A', 0), imported('E', 1), submission('B', 2)];
    expect(orderOf(planAdjacentMove(items, 'B', 'up'), ['A', 'E', 'B'])).toEqual(['A', 'B', 'E']);
    expect(orderOf(planAdjacentMove(items, 'A', 'down'), ['A', 'E', 'B'])).toEqual(['E', 'A', 'B']);
  });

  it('does nothing at either end', () => {
    const items = [submission('A', 0), submission('B', 1)];
    expect(planAdjacentMove(items, 'A', 'up')).toEqual([]);
    expect(planAdjacentMove(items, 'B', 'down')).toEqual([]);
  });
});

describe('compareSectionItems', () => {
  it('breaks a position tie by headline, then Id, as the export does', () => {
    const items = [
      { ...submission('2', 0), Final_Headline: 'Zulu' },
      { ...imported('1', 0), Final_Headline: 'alpha' },
      { ...imported('0', 0), Final_Headline: 'Alpha' },
    ];
    // Code-point order: uppercase before lowercase, as Python sorts.
    expect([...items].sort(compareSectionItems).map((item) => item.Final_Headline))
      .toEqual(['Alpha', 'Zulu', 'alpha']);
  });
});
