import { useCallback, useRef, useState } from 'react';
import type { ToastMessage, ToastTone } from './Toast';

export default function useToast() {
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const timerRef = useRef<number | null>(null);

  const showToast = useCallback((message: string, tone: ToastTone = 'success') => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }
    setToast({ message, tone });
    timerRef.current = window.setTimeout(() => {
      setToast(null);
      timerRef.current = null;
    }, 3000);
  }, []);

  const dismissToast = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setToast(null);
  }, []);

  return { toast, showToast, dismissToast };
}
