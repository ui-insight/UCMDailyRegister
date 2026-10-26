import { useRef, useState } from 'react';
import ConfirmDialog from './ConfirmDialog';

interface ConfirmAction {
  title: string;
  description: string;
  confirmLabel: string;
  action: () => Promise<unknown>;
}

/** Capture the intended record and serialize confirmation and its network action. */
export default function useConfirmAction() {
  const [pending, setPending] = useState<ConfirmAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const locked = useRef(false);
  const requestConfirmation = (next: ConfirmAction) => {
    if (locked.current) return;
    locked.current = true;
    setError('');
    setPending(next);
  };
  const cancel = () => {
    if (busy) return;
    setPending(null);
    locked.current = false;
  };
  const executing = useRef(false);
  const execute = async () => {
    if (!pending || executing.current) return;
    executing.current = true;
    setBusy(true);
    setError('');
    try {
      await pending.action();
      setPending(null);
      locked.current = false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The change could not be saved. Try again.');
    } finally {
      executing.current = false;
      setBusy(false);
    }
  };
  return {
    requestConfirmation,
    confirmationDialog: <ConfirmDialog open={pending !== null}
      title={pending?.title ?? ''} description={pending?.description ?? ''}
      confirmLabel={pending?.confirmLabel} destructive busy={busy} error={error}
      onConfirm={() => void execute()} onCancel={cancel} />,
  };
}
