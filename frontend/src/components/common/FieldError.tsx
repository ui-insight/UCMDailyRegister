import type { FieldErrors } from '../../utils/formValidation';

export default function FieldError({ errors, id }: { errors: FieldErrors; id: string }) {
  return errors[id] ? <p id={`${id}-error`} className="mt-1 text-sm text-status-error-800">
    {errors[id].message}
  </p> : null;
}
