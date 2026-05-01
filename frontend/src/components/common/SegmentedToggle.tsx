import { cx } from './utils';

interface SegmentedToggleOption<T extends string> {
  value: T;
  label: string;
}

export default function SegmentedToggle<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  className,
}: {
  options: SegmentedToggleOption<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
  className?: string;
}) {
  return (
    <div
      className={cx('inline-flex overflow-hidden rounded-md border border-gray-300', className)}
      role="group"
      aria-label={ariaLabel}
    >
      {options.map((option, index) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cx(
            'px-3 py-1.5 text-xs font-medium transition-colors',
            index > 0 && 'border-l border-gray-300',
            value === option.value
              ? 'bg-ui-gold-500 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50',
          )}
          aria-pressed={value === option.value}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
