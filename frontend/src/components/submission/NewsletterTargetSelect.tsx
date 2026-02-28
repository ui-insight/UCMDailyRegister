import type { TargetNewsletter } from '../../types/submission';

const TARGETS: { value: TargetNewsletter; label: string; description: string }[] = [
  { value: 'tdr', label: 'The Daily Register', description: 'Faculty & Staff' },
  { value: 'myui', label: 'My UI', description: 'Students' },
  { value: 'both', label: 'Both Newsletters', description: 'Faculty, Staff & Students' },
];

interface Props {
  value: TargetNewsletter;
  onChange: (value: TargetNewsletter) => void;
}

export default function NewsletterTargetSelect({ value, onChange }: Props) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Target Newsletter
      </label>
      <div className="flex gap-3">
        {TARGETS.map((target) => (
          <button
            key={target.value}
            type="button"
            onClick={() => onChange(target.value)}
            className={`flex-1 rounded-lg border-2 p-3 text-left transition-colors ${
              value === target.value
                ? 'border-ui-gold-500 bg-ui-gold-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="text-sm font-medium text-gray-900">{target.label}</div>
            <div className="text-xs text-gray-500">{target.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
