/** Client validation describes the field, never copies its entered value into diagnostics. */
export interface FieldProblem { label: string; message: string }
export type FieldErrors = Record<string, FieldProblem>;

export function addFieldError(errors: FieldErrors, form: HTMLFormElement, id: string, message: string) {
  const field = form.elements.namedItem(id);
  if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)) return;
  errors[id] = { label: field.labels?.[0]?.textContent?.trim() || 'This field', message };
}

export function collectFormErrors(form: HTMLFormElement): FieldErrors {
  const errors: FieldErrors = {};
  for (const field of Array.from(form.elements)) {
    if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)
      || !field.willValidate || !field.id) continue;
    let message = '';
    if (field.required && !field.value.trim()) message = 'Please complete this field.';
    else if (field.validity.typeMismatch) message = field.type === 'email'
      ? 'Enter a valid email address.' : 'Enter a complete web address, such as https://example.edu.';
    else if (!field.validity.valid) message = field.validationMessage;
    if (message) addFieldError(errors, form, field.id, message);
  }
  return errors;
}

export function fieldErrorProps(errors: FieldErrors, id: string, instructions?: string) {
  return {
    'aria-invalid': errors[id] ? true as const : undefined,
    'aria-describedby': [instructions, errors[id] ? `${id}-error` : undefined].filter(Boolean).join(' ') || undefined,
  };
}
