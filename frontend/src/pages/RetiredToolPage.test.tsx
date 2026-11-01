import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { RETIRED_TOOL_PATHS } from '../utils/retiredTools';
import RetiredToolPage from './RetiredToolPage';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        {RETIRED_TOOL_PATHS.map((retiredPath) => (
          <Route key={retiredPath} path={retiredPath} element={<RetiredToolPage />} />
        ))}
      </Routes>
    </MemoryRouter>,
  );
}

describe('RetiredToolPage', () => {
  it.each(['/slc-calendar', '/slc-triage', '/slc-digest', '/submit-slc-event'])(
    'explains that the SLC calendar is gone at %s',
    (path) => {
      renderAt(path);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'The SLC events calendar is no longer part of UCM News',
      );
    },
  );

  it('explains that Event Services triage is gone', () => {
    renderAt('/ops-triage');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Event Services triage is no longer part of UCM News',
    );
  });

  it('says the data was kept and links back into UCM News', () => {
    renderAt('/slc-calendar');
    expect(screen.getByText(/Nothing you entered has been deleted/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to UCM News' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Submit a newsletter item' })).toHaveAttribute(
      'href',
      '/submit',
    );
  });
});
