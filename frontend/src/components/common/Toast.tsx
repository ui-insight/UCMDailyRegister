import { cx } from './utils';

export type ToastTone = 'success' | 'error' | 'info';

export interface ToastMessage {
  message: string;
  tone?: ToastTone;
}

const toneClasses: Record<ToastTone, string> = {
  success: 'bg-status-success-800 text-white',
  error: 'bg-status-error-800 text-white',
  info: 'bg-ui-clearwater-800 text-white',
};

export default function Toast({
  toast,
  onDismiss,
}: {
  toast: ToastMessage | null;
  onDismiss?: () => void;
}) {
  if (!toast) return null;

  return (
    <div
      role="status"
      className={cx(
        'fixed right-4 top-4 z-50 rounded-lg px-4 py-2 text-sm shadow-lg',
        toneClasses[toast.tone ?? 'success'],
      )}
    >
      <div className="flex items-center gap-3">
        <span>{toast.message}</span>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="text-white/70 hover:text-white"
            aria-label="Dismiss notification"
          >
            &times;
          </button>
        )}
      </div>
    </div>
  );
}
