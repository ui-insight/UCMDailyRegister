import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import NewsletterTargetSelect from './NewsletterTargetSelect';

describe('NewsletterTargetSelect', () => {
  it('emits the selected newsletter target', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<NewsletterTargetSelect value="tdr" onChange={onChange} />);

    await user.click(screen.getByRole('button', { name: /my ui/i }));

    expect(onChange).toHaveBeenCalledWith('myui');
  });

  it('prevents choosing disabled targets', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <NewsletterTargetSelect
        value="tdr"
        onChange={onChange}
        disabledTargets={['both']}
      />,
    );

    const bothButton = screen.getByRole('button', { name: /both newsletters/i });
    expect(bothButton).toBeDisabled();

    await user.click(bothButton);

    expect(onChange).not.toHaveBeenCalled();
  });
});
