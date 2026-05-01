import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import AIEditControls from './AIEditControls';

describe('AIEditControls', () => {
  it('offers each eligible newsletter edit path before an AI edit exists', async () => {
    const user = userEvent.setup();
    const onTriggerEdit = vi.fn();

    render(
      <AIEditControls
        onTriggerEdit={onTriggerEdit}
        onAcceptEdit={vi.fn()}
        onRejectEdit={vi.fn()}
        loading={false}
        hasAIEdit={false}
        targetNewsletter="both"
      />,
    );

    await user.click(screen.getByRole('button', { name: /tdr/i }));
    await user.click(screen.getByRole('button', { name: /my ui/i }));

    expect(onTriggerEdit).toHaveBeenNthCalledWith(1, 'tdr');
    expect(onTriggerEdit).toHaveBeenNthCalledWith(2, 'myui');
  });

  it('shows review actions and confidence after an AI edit exists', async () => {
    const user = userEvent.setup();
    const onAcceptEdit = vi.fn();
    const onRejectEdit = vi.fn();

    render(
      <AIEditControls
        onTriggerEdit={vi.fn()}
        onAcceptEdit={onAcceptEdit}
        onRejectEdit={onRejectEdit}
        loading={false}
        hasAIEdit
        targetNewsletter="tdr"
        confidence={0.84}
      />,
    );

    expect(screen.getByText('84%')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /accept ai edit/i }));
    await user.click(screen.getByRole('button', { name: /edit manually/i }));

    expect(onAcceptEdit).toHaveBeenCalledOnce();
    expect(onRejectEdit).toHaveBeenCalledOnce();
  });

  it('sends targeted editor feedback when revising an AI edit', async () => {
    const user = userEvent.setup();
    const onTriggerEdit = vi.fn();

    render(
      <AIEditControls
        onTriggerEdit={onTriggerEdit}
        onAcceptEdit={vi.fn()}
        onRejectEdit={vi.fn()}
        loading={false}
        hasAIEdit
        targetNewsletter="tdr"
      />,
    );

    await user.type(screen.getByLabelText(/editor feedback/i), 'Tighten the first sentence.');
    await user.click(screen.getByRole('button', { name: /revise tdr/i }));

    expect(onTriggerEdit).toHaveBeenCalledWith('tdr', 'Tighten the first sentence.');
    expect(screen.queryByRole('button', { name: /re-run tdr/i })).not.toBeInTheDocument();
  });
});
