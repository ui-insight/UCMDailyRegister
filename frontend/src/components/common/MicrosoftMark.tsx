/** Microsoft's four-square mark, inline so pages need no external assets. */
export default function MicrosoftMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 21 21" className="h-4 w-4 shrink-0">
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  );
}
