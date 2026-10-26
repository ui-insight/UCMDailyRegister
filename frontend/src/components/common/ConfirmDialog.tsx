import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import Button from './Button';

const dialogs: HTMLElement[] = [];
const originalInert = new Map<HTMLElement, boolean>();
let originalOverflow = '';

function isolateTopDialog() {
  const top = dialogs.at(-1);
  if (!top) {
    originalInert.forEach((inert, element) => element.toggleAttribute('inert', inert));
    originalInert.clear();
    document.body.style.overflow = originalOverflow;
    return;
  }
  for (const child of document.body.children) {
    if (!(child instanceof HTMLElement)) continue;
    if (!originalInert.has(child)) originalInert.set(child, child.hasAttribute('inert'));
    child.toggleAttribute('inert', child !== top || originalInert.get(child) === true);
  }
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [portal] = useState(() => document.createElement('div'));
  const dialog = useRef<HTMLDivElement>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const cancelHandler = useRef(onCancel);
  const titleId = useId();
  const descriptionId = useId();
  useEffect(() => { cancelHandler.current = onCancel; }, [onCancel]);
  useEffect(() => {
    if (!open) return;
    const invoker = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!dialogs.length) originalOverflow = document.body.style.overflow;
    document.body.append(portal);
    dialogs.push(portal);
    isolateTopDialog();
    document.body.style.overflow = 'hidden';
    cancelButton.current?.focus();
    const focusable = () => Array.from(dialog.current?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)',
    ) ?? []).filter((element) => !element.closest('[hidden], [inert]')
      && getComputedStyle(element).display !== 'none');
    const keydown = (event: KeyboardEvent) => {
      if (dialogs.at(-1) !== portal) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        cancelHandler.current();
      } else if (event.key === 'Tab') {
        const controls = focusable();
        const first = controls[0];
        const last = controls.at(-1);
        if ((event.shiftKey && document.activeElement === first)
          || (!event.shiftKey && document.activeElement === last)) {
          event.preventDefault();
          (event.shiftKey ? last : first)?.focus();
        }
      }
    };
    const containFocus = (event: FocusEvent) => {
      if (dialogs.at(-1) === portal && !portal.contains(event.target as Node)) {
        cancelButton.current?.focus();
      }
    };
    document.addEventListener('keydown', keydown, true);
    document.addEventListener('focusin', containFocus);
    return () => {
      document.removeEventListener('keydown', keydown, true);
      document.removeEventListener('focusin', containFocus);
      dialogs.splice(dialogs.indexOf(portal), 1);
      portal.remove();
      isolateTopDialog();
      if (invoker?.isConnected && !invoker.closest('[inert]')) invoker.focus();
    };
  }, [open, portal]);
  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-gray-900/30 px-4">
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
      >
        <h2 id={titleId} className="text-base font-semibold text-gray-900">
          {title}
        </h2>
        <p id={descriptionId} className="mt-2 text-sm text-gray-600">{description}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button ref={cancelButton} variant="ghost" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button variant={destructive ? 'destructive' : 'primary'} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>, portal,
  );
}
