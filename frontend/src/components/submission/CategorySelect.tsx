import type { AllowedValue } from '../../types/allowedValue';
import type { SubmissionCategory } from '../../types/submission';

interface Props {
  categories: AllowedValue[];
  isLoading?: boolean;
  value: SubmissionCategory;
  onChange: (value: SubmissionCategory) => void;
}

export default function CategorySelect({
  categories,
  isLoading = false,
  value,
  onChange,
}: Props) {
  return (
    <div>
      <label
        htmlFor="submission-category"
        className="block text-sm font-medium text-gray-700 mb-1"
      >
        Announcement Type
      </label>
      <select
        id="submission-category"
        value={value}
        onChange={(e) => onChange(e.target.value as SubmissionCategory)}
        disabled={isLoading || categories.length === 0}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
      >
        {categories.map((cat) => (
          <option key={cat.Code} value={cat.Code}>
            {cat.Label}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-gray-400">
        {isLoading
          ? 'Loading available announcement types...'
          : 'Options vary by target newsletter.'}
      </p>
    </div>
  );
}
