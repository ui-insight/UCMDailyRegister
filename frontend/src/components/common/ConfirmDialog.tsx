import { useRef } from 'react';
import Button from './Button';
import Modal from './Modal';

export default function ConfirmDialog({ open, title, description, confirmLabel = 'Confirm',
  cancelLabel = 'Cancel', destructive = false, busy = false, error = '', onConfirm, onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  busy?: boolean;
  error?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelButton = useRef<HTMLButtonElement>(null);
  return <Modal open={open} title={title} description={description} onCancel={onCancel}
    initialFocusRef={cancelButton} busy={busy}>
    {error && <p role="alert" className="mt-3 text-sm text-status-error-800">{error}</p>}
    {busy && <p role="status" className="mt-3 text-sm text-gray-600">Saving the change…</p>}
    <div className="mt-5 flex justify-end gap-2">
      <Button ref={cancelButton} variant="ghost" disabled={busy} onClick={onCancel}>{cancelLabel}</Button>
      <Button variant={destructive ? 'destructive' : 'primary'} disabled={busy} onClick={onConfirm}>
        {busy ? 'Saving…' : confirmLabel}
      </Button>
    </div>
  </Modal>;
}
