import type { SubmissionCategory } from '../../types/submission';

const CATEGORIES: { value: SubmissionCategory; label: string }[] = [
  { value: 'faculty_staff', label: 'Faculty or Staff Announcement' },
  { value: 'student', label: 'Student Announcement' },
  { value: 'job_opportunity', label: 'Job Opportunity' },
  { value: 'kudos', label: 'Acknowledgments and Kudos' },
  { value: 'in_memoriam', label: 'In Memoriam' },
];

interface Props {
  value: SubmissionCategory;
  onChange: (value: SubmissionCategory) => void;
}

export default function CategorySelect({ value, onChange }: Props) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Announcement Type
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as SubmissionCategory)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
      >
        {CATEGORIES.map((cat) => (
          <option key={cat.value} value={cat.value}>
            {cat.label}
          </option>
        ))}
      </select>
    </div>
  );
}
