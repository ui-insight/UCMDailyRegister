import type { AIFlag } from '../../types/aiEdit';

interface FlagListProps {
  flags: AIFlag[];
}

const FLAG_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  error: { bg: 'bg-red-50', border: 'border-red-200', icon: 'text-red-500' },
  warning: { bg: 'bg-ui-gold-50', border: 'border-ui-gold-200', icon: 'text-ui-gold-500' },
  info: { bg: 'bg-blue-50', border: 'border-blue-200', icon: 'text-blue-500' },
};

const FLAG_ICONS: Record<string, string> = {
  error: '\u2718',    // heavy ballot X
  warning: '\u26A0',  // warning sign
  info: '\u2139',     // information source
};

export default function FlagList({ flags }: FlagListProps) {
  if (flags.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic p-3 bg-gray-50 rounded">
        No flags raised
      </div>
    );
  }

  // Group by severity
  const errors = flags.filter((f) => f.type === 'error');
  const warnings = flags.filter((f) => f.type === 'warning');
  const infos = flags.filter((f) => f.type === 'info');
  const sorted = [...errors, ...warnings, ...infos];

  return (
    <div className="space-y-2">
      {sorted.map((flag, i) => {
        const style = FLAG_STYLES[flag.type] || FLAG_STYLES.info;
        return (
          <div
            key={i}
            className={`flex items-start gap-2 p-2.5 rounded border text-sm ${style.bg} ${style.border}`}
          >
            <span className={`text-base leading-none mt-0.5 ${style.icon}`}>
              {FLAG_ICONS[flag.type]}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-gray-800">{flag.message}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Rule: {flag.rule_key}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
