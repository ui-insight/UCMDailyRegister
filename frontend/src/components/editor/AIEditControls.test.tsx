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
        onReviewFinalEdit={vi.fn()}
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

  it('routes an AI suggestion through final review without a separate accept action', async () => {
    const user = userEvent.setup();
    const onReviewFinalEdit = vi.fn();

    render(
      <AIEditControls
        onTriggerEdit={vi.fn()}
        onReviewFinalEdit={onReviewFinalEdit}
        loading={false}
        hasAIEdit
        targetNewsletter="tdr"
        confidence={0.84}
      />,
    );

    expect(screen.getByText('84%')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /accept ai edit/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /continue to final edit/i }));

    expect(onReviewFinalEdit).toHaveBeenCalledOnce();
  });

  it('sends targeted editor feedback when revising an AI edit', async () => {
    const user = userEvent.setup();
    const onTriggerEdit = vi.fn();

    render(
      <AIEditControls
        onTriggerEdit={onTriggerEdit}
        onReviewFinalEdit={vi.fn()}
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
