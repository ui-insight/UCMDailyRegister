import { useState, useEffect } from 'react';

interface BodyEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function BodyEditor({ value, onChange, disabled = false }: BodyEditorProps) {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleBlur = () => {
    onChange(localValue);
  };

  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">Body</label>
      <textarea
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onBlur={handleBlur}
        disabled={disabled}
        rows={8}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                   focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500
                   disabled:bg-gray-50 disabled:text-gray-500 resize-y"
        placeholder="Enter body text..."
      />
    </div>
  );
}
