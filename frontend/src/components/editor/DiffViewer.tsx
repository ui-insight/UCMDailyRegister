import type { TextDiff } from '../../types/aiEdit';

interface DiffViewerProps {
  diff: TextDiff;
  label?: string;
}

export default function DiffViewer({ diff, label }: DiffViewerProps) {
  if (diff.change_count === 0) {
    return (
      <div className="text-sm text-gray-500 italic p-3 bg-gray-50 rounded">
        No changes
      </div>
    );
  }

  return (
    <div>
      {label && (
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium text-gray-500 uppercase">{label}</span>
          <span className="text-xs text-gray-400">
            {diff.change_count} change{diff.change_count !== 1 ? 's' : ''} &middot;{' '}
            {Math.round(diff.similarity_ratio * 100)}% similar
          </span>
        </div>
      )}
      <div className="font-mono text-sm leading-relaxed p-3 bg-gray-50 rounded border">
        {diff.segments.map((seg, i) => {
          switch (seg.type) {
            case 'equal':
              return <span key={i}>{seg.modified} </span>;
            case 'delete':
              return (
                <span
                  key={i}
                  className="bg-red-100 text-red-800 line-through decoration-red-400"
                >
                  {seg.original}{' '}
                </span>
              );
            case 'insert':
              return (
                <span key={i} className="bg-green-100 text-green-800">
                  {seg.modified}{' '}
                </span>
              );
            case 'replace':
              return (
                <span key={i}>
                  <span className="bg-red-100 text-red-800 line-through decoration-red-400">
                    {seg.original}
                  </span>{' '}
                  <span className="bg-green-100 text-green-800">{seg.modified}</span>{' '}
                </span>
              );
            default:
              return <span key={i}>{seg.modified} </span>;
          }
        })}
      </div>
    </div>
  );
}
