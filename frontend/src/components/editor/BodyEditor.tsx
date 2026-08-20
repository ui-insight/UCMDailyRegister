interface BodyEditorProps {
  value: string;
  onChange: (value: string) => void;
  onCommit?: (previousValue: string, nextValue: string) => void;
  disabled?: boolean;
}

export default function BodyEditor({
  value,
  onChange,
  onCommit,
  disabled = false,
}: BodyEditorProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">Body</label>
      <textarea
        value={value}
        onFocus={(e) => {
          e.currentTarget.dataset.initialValue = e.currentTarget.value;
        }}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => onCommit?.(
          e.currentTarget.dataset.initialValue ?? '',
          e.currentTarget.value,
        )}
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
