import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';

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

export default function Modal({ open, title, description, children, onCancel,
  initialFocusRef, busy = false, wide = false,
}: {
  open: boolean;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  onCancel: () => void;
  initialFocusRef?: RefObject<HTMLElement | null>;
  busy?: boolean;
  wide?: boolean;
}) {
  const [portal] = useState(() => document.createElement('div'));
  const dialog = useRef<HTMLDivElement>(null);
  const cancelHandler = useRef(onCancel);
  const dismissBlocked = useRef(busy);
  const titleId = useId();
  const descriptionId = useId();
  useEffect(() => { cancelHandler.current = onCancel; dismissBlocked.current = busy; }, [onCancel, busy]);
  useEffect(() => {
    if (!open) return;
    const invoker = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!dialogs.length) originalOverflow = document.body.style.overflow;
    document.body.append(portal);
    dialogs.push(portal);
    isolateTopDialog();
    document.body.style.overflow = 'hidden';
    const focusInside = () => {
      const target = initialFocusRef?.current
        ?? dialog.current?.querySelector<HTMLElement>('[data-dialog-initial-focus]')
        ?? dialog.current;
      if (target?.matches(':disabled')) dialog.current?.focus();
      else target?.focus();
    };
    focusInside();
    const focusable = () => Array.from(dialog.current?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)',
    ) ?? []).filter((element) => !element.closest('[hidden], [inert]')
      && getComputedStyle(element).display !== 'none');
    const keydown = (event: KeyboardEvent) => {
      if (dialogs.at(-1) !== portal) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        if (!dismissBlocked.current) cancelHandler.current();
      } else if (event.key === 'Tab') {
        const controls = focusable();
        if (!controls.length) { event.preventDefault(); dialog.current?.focus(); return; }
        const first = controls[0];
        const last = controls.at(-1);
        if (!controls.includes(document.activeElement as HTMLElement)
          || (event.shiftKey && document.activeElement === first)
          || (!event.shiftKey && document.activeElement === last)) {
          event.preventDefault();
          (event.shiftKey ? last : first)?.focus();
        }
      }
    };
    const containFocus = (event: FocusEvent) => {
      if (dialogs.at(-1) === portal && !portal.contains(event.target as Node)) {
        focusInside();
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
      else if (!dialogs.length) {
        const main = document.querySelector<HTMLElement>('main');
        if (main) {
          const previous = main.getAttribute('tabindex');
          main.setAttribute('tabindex', '-1');
          main.focus();
          main.addEventListener('blur', () => {
            if (previous === null) main.removeAttribute('tabindex');
            else main.setAttribute('tabindex', previous);
          }, { once: true });
        }
      }
    };
  }, [open, portal, initialFocusRef]);
  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-40 flex items-center justify-center overflow-y-auto bg-gray-900/30 p-4">
      <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined} aria-busy={busy || undefined}
        tabIndex={-1}
        className={`max-h-[calc(100dvh-2rem)] w-full overflow-y-auto rounded-lg bg-white p-5 text-gray-900 shadow-xl ${wide ? 'max-w-lg' : 'max-w-md'}`}>
        <h2 id={titleId} className="text-base font-semibold text-gray-900">{title}</h2>
        {description && <div id={descriptionId} className="mt-2 text-sm text-gray-600">{description}</div>}
        {children}
      </div>
    </div>, portal,
  );
}
