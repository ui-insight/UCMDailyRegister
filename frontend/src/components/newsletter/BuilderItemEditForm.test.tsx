import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { prepareBodyForEditing } from '../../utils/bodyLinks';
import BuilderItemEditForm, { type BuilderItemEditDraft } from './BuilderItemEditForm';

vi.mock('./OriginalEntryPanel', () => ({ default: () => null }));

function Harness({ initial, onSave }: { initial: BuilderItemEditDraft; onSave: () => void }) {
  const [draft, setDraft] = useState(initial);
  return (
    <>
      <BuilderItemEditForm
        itemId="item-1"
        submissionId="submission-1"
        draft={draft}
        onDraftChange={(change) => setDraft(change)}
        saving={false}
        onCancel={() => {}}
        onSave={onSave}
      />
      <output data-testid="body">{draft.Body}</output>
    </>
  );
}

describe('BuilderItemEditForm', () => {
  it('puts a link\'s missing words back into the body so a headline edit can be saved (#521)', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    // A link appended by an older editor build is removed from the body on
    // load, leaving the link unattached.
    const editable = prepareBodyForEditing(
      'Join us Friday.\n<a href="https://example.edu/social">Register for the social</a>',
    );
    render(
      <Harness
        initial={{ Item_Id: 'item-1', Headline: 'Staff social', Body: editable.body, Links: editable.links }}
        onSave={onSave}
      />,
    );

    expect(screen.getByTestId('body')).toHaveTextContent(/^Join us Friday\.$/);
    await user.click(screen.getByRole('button', { name: 'Add these words to the body' }));

    expect(screen.getByTestId('body')).toHaveTextContent('Join us Friday. Register for the social');
    await user.click(screen.getByRole('button', { name: /save/i }));
    expect(onSave).toHaveBeenCalledTimes(1);
  });
});
