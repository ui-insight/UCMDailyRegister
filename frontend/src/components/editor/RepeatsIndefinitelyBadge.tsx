/**
 * Label for a schedule UCM staff set to repeat with no end date (#538), so
 * standing items are easy to find and review in schedule and calendar views.
 */
export default function RepeatsIndefinitelyBadge({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-block px-1.5 py-0.5 text-xs font-normal bg-ui-clearwater-50 text-ui-clearwater-800 rounded ${className}`.trim()}
    >
      Repeats indefinitely
    </span>
  );
}
