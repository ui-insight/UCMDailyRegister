import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useIdentity } from '../../auth/useAuth';
import { setSubmitterRole } from '../../utils/submitterRole';
import Sidebar from './Sidebar';

vi.mock('../../auth/useAuth', () => ({
  useIdentity: vi.fn(),
}));

const useIdentityMock = vi.mocked(useIdentity);

function renderSidebar() {
  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>,
  );
}

describe('Sidebar', () => {
  beforeEach(() => {
    localStorage.clear();
    useIdentityMock.mockReturnValue(null);
  });

  it('links anonymous submitters home instead of offering a mode switch', () => {
    setSubmitterRole('public');
    renderSidebar();

    expect(screen.getByText('Submitter View')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'UCM News home' })).toHaveAttribute('href', '/');
    expect(screen.queryByText('Current Mode')).not.toBeInTheDocument();
    expect(screen.queryByText('Switch mode')).not.toBeInTheDocument();
  });

  it('shows the signed-in name and a sign-out button', () => {
    setSubmitterRole('staff');
    useIdentityMock.mockReturnValue({
      subject: 'synthetic-subject',
      name: 'Synthetic Editor',
      role: 'staff',
      exp: 4_000_000_000,
    });
    renderSidebar();

    expect(screen.getByText('Synthetic Editor')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'UCM News home' })).not.toBeInTheDocument();
  });
});
