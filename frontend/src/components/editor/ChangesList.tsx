interface ChangesListProps {
  changes: string[];
}

export default function ChangesList({ changes }: ChangesListProps) {
  if (changes.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic p-3 bg-gray-50 rounded">
        No changes recorded
      </div>
    );
  }

  return (
    <ul className="space-y-1.5">
      {changes.map((change, i) => (
        <li key={i} className="flex items-start gap-2 text-sm">
          <span className="text-green-500 mt-0.5 shrink-0">&bull;</span>
          <span className="text-gray-700">{change}</span>
        </li>
      ))}
    </ul>
  );
}
