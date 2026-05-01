import type { HTMLAttributes, ReactNode } from 'react';
import { cx } from './utils';

type PillTone = 'info' | 'edited' | 'warning' | 'success' | 'attention' | 'error' | 'muted' | 'gold' | 'clearwater';

interface PillProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: PillTone;
  children: ReactNode;
}

const toneClasses: Record<PillTone, string> = {
  info: 'bg-status-info-100 text-status-info-800',
  edited: 'bg-status-edited-100 text-status-edited-800',
  warning: 'bg-status-warning-100 text-status-warning-800',
  success: 'bg-status-success-100 text-status-success-800',
  attention: 'bg-status-attention-100 text-status-attention-800',
  error: 'bg-status-error-100 text-status-error-800',
  muted: 'bg-status-muted-100 text-status-muted-800',
  gold: 'bg-ui-gold-100 text-ui-gold-800',
  clearwater: 'bg-ui-clearwater-100 text-ui-clearwater-800',
};

export default function Pill({
  tone = 'muted',
  className,
  children,
  ...props
}: PillProps) {
  return (
    <span
      className={cx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
