import { useState, useEffect } from 'react';

interface HeadlineEditorProps {
  value: string;
  onChange: (value: string) => void;
  headlineCase: 'sentence_case' | 'title_case' | null;
  disabled?: boolean;
}

export default function HeadlineEditor({
  value,
  onChange,
  headlineCase,
  disabled = false,
}: HeadlineEditorProps) {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleBlur = () => {
    onChange(localValue);
  };

  const caseLabel = headlineCase === 'sentence_case'
    ? 'Sentence case'
    : headlineCase === 'title_case'
      ? 'Title case'
      : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="block text-xs font-medium text-gray-700">Headline</label>
        {caseLabel && (
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
            {caseLabel}
          </span>
        )}
      </div>
      <input
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onBlur={handleBlur}
        disabled={disabled}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-medium
                   focus:border-amber-500 focus:ring-1 focus:ring-amber-500
                   disabled:bg-gray-50 disabled:text-gray-500"
        placeholder="Enter headline..."
      />
    </div>
  );
}
