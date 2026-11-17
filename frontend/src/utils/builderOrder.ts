/**
 * Order of items within a Builder section (#509, #510).
 *
 * Submissions and imported items (events, jobs, recurring messages, academic
 * dates) share one position sequence per section. Staff move submissions;
 * imported items have no move controls but keep their place in the sequence.
 */

export interface SectionOrderItem {
  Id: string;
  Section_Id: string;
  Position: number;
  Final_Headline: string;
  Kind: string;
}

export interface PositionUpdate {
  Id: string;
  Position: number;
  /** Sent for submissions only; imported items stay in their section. */
  Section_Id?: string;
}

function compareText(left: string, right: string): number {
  // Code-point order, as Python compares strings on the backend.
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

/**
 * Mirrors `section_order_key` in backend/app/services/newsletter_service.py,
 * which orders the Word export: position, then headline, then Id. Positions
 * are unique once a section is renumbered; the rest only breaks old ties.
 */
export function compareSectionItems(left: SectionOrderItem, right: SectionOrderItem): number {
  return left.Position - right.Position
    || compareText(left.Final_Headline, right.Final_Headline)
    || compareText(left.Id, right.Id);
}

export function sortSectionItems<T extends SectionOrderItem>(items: T[]): T[] {
  return [...items].sort(compareSectionItems);
}

function itemsIn<T extends SectionOrderItem>(items: T[], sectionId: string): T[] {
  return sortSectionItems(items.filter((item) => item.Section_Id === sectionId));
}

function renumbered(items: SectionOrderItem[], sectionId: string): PositionUpdate[] {
  return items.map((item, index) => (
    item.Kind === 'submission'
      ? { Id: item.Id, Position: index, Section_Id: sectionId }
      : { Id: item.Id, Position: index }
  ));
}

function sameOrder(left: SectionOrderItem[], right: SectionOrderItem[]): boolean {
  return left.length === right.length && left.every((item, index) => item.Id === right[index].Id);
}

/**
 * Positions after dropping a submission where the drop indicator shows.
 *
 * `targetSubmissionIndex` counts the target section's submission cards as
 * displayed, including the dragged card when it is in that section: the
 * submission goes before the card at that index, or after the last
 * submission when the index is past the end. Placing it relative to that
 * card, not by index into a list without the dragged card, is what keeps a
 * downward drag from landing one slot low (#510).
 *
 * Returns every item's new position in the affected sections, or an empty
 * list when nothing would change.
 */
export function planSubmissionMove(
  allItems: SectionOrderItem[],
  itemId: string,
  targetSectionId: string,
  targetSubmissionIndex: number,
): PositionUpdate[] {
  const dragged = allItems.find((item) => item.Id === itemId && item.Kind === 'submission');
  if (!dragged) return [];
  const sourceSectionId = dragged.Section_Id;

  const target = itemsIn(allItems, targetSectionId);
  const targetSubmissions = target.filter((item) => item.Kind === 'submission');
  const index = Math.max(0, targetSubmissionIndex);
  const anchor = index < targetSubmissions.length ? targetSubmissions[index] : undefined;
  if (anchor?.Id === itemId) return [];

  const rest = target.filter((item) => item.Id !== itemId);
  let insertAt: number;
  if (anchor) {
    insertAt = rest.findIndex((item) => item.Id === anchor.Id);
  } else {
    const lastSubmission = [...rest].reverse().find((item) => item.Kind === 'submission');
    insertAt = lastSubmission
      ? rest.findIndex((item) => item.Id === lastSubmission.Id) + 1
      : rest.length;
  }
  const nextTarget = [...rest];
  nextTarget.splice(insertAt, 0, dragged);

  if (sourceSectionId === targetSectionId) {
    return sameOrder(nextTarget, target) ? [] : renumbered(nextTarget, targetSectionId);
  }
  const nextSource = itemsIn(allItems, sourceSectionId).filter((item) => item.Id !== itemId);
  return [
    ...renumbered(nextSource, sourceSectionId),
    ...renumbered(nextTarget, targetSectionId),
  ];
}

/**
 * Positions after moving a submission one slot up or down in its section,
 * past whatever item is next to it. Empty when it is already at that end.
 */
export function planAdjacentMove(
  allItems: SectionOrderItem[],
  itemId: string,
  direction: 'up' | 'down',
): PositionUpdate[] {
  const item = allItems.find((candidate) => candidate.Id === itemId);
  if (!item) return [];
  const section = itemsIn(allItems, item.Section_Id);
  const index = section.findIndex((candidate) => candidate.Id === itemId);
  const swapIndex = direction === 'up' ? index - 1 : index + 1;
  if (swapIndex < 0 || swapIndex >= section.length) return [];
  const next = [...section];
  [next[index], next[swapIndex]] = [next[swapIndex], next[index]];
  return renumbered(next, item.Section_Id);
}
