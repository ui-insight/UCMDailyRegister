import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listOpsEvents } from '../api/opsEvents';
import type { OpsEvent } from '../types/harvestedEvent';
import { getSubmitterRole } from '../utils/submitterRole';
import OpsTriagePage from './OpsTriagePage';

vi.mock('../api/opsEvents', () => ({
  listOpsEvents: vi.fn(),
}));

vi.mock('../utils/submitterRole', () => ({
  getSubmitterRole: vi.fn(),
}));

const listOpsEventsMock = vi.mocked(listOpsEvents);
const getSubmitterRoleMock = vi.mocked(getSubmitterRole);

function renderOpsTriagePage() {
  return render(
    <MemoryRouter>
      <OpsTriagePage />
    </MemoryRouter>,
  );
}

function isoDaysFromNow(days: number, timeSuffix = 'T10:00:00'): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}${timeSuffix}`;
}

function makeOpsEvent(overrides: Partial<OpsEvent> = {}): OpsEvent {
  return {
    Id: 'harvested-1',
    Source_Type: 'trumba',
    Source_Id: '204106464',
    Series_Id: null,
    Source_Url: 'https://www.uidaho.edu/events?trumbaEmbed=view%3Devent%26eventid%3D204106464',
    Title: 'Screen on the Green',
    Description: 'A free, family-friendly outdoor movie night.',
    Location: 'Tower Lawn',
    Event_Start: isoDaysFromNow(2),
    Event_End: isoDaysFromNow(2, 'T12:00:00'),
    All_Day: false,
    Category_Path: 'Student Affairs|Dept. of Student Involvement',
    Is_Canceled: false,
    Ops_Review_Status: 'new',
    First_Seen_At: isoDaysFromNow(0),
    Last_Seen_At: isoDaysFromNow(0),
    ...overrides,
  };
}

describe('OpsTriagePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSubmitterRoleMock.mockReturnValue('ops');
  });

  it.each(['public', 'slc'] as const)(
    'blocks viewers with the %s role',
    (role) => {
      getSubmitterRoleMock.mockReturnValue(role);
      renderOpsTriagePage();
      expect(screen.getByText('Restricted page')).toBeInTheDocument();
      expect(listOpsEventsMock).not.toHaveBeenCalled();
    },
  );

  it.each(['ops', 'staff'] as const)(
    'lists events grouped by week for the %s role',
    async (role) => {
      getSubmitterRoleMock.mockReturnValue(role);
      listOpsEventsMock.mockResolvedValue({
        Items: [
          makeOpsEvent(),
          makeOpsEvent({
            Id: 'harvested-2',
            Source_Id: '111',
            Title: 'Alumni Awards Reception',
            Category_Path: 'Alumni Relations',
            Event_Start: isoDaysFromNow(9),
            Event_End: null,
          }),
        ],
        Total: 2,
      });
      renderOpsTriagePage();

      expect(await screen.findByText('Screen on the Green')).toBeInTheDocument();
      expect(screen.getByText('Alumni Awards Reception')).toBeInTheDocument();
      expect(screen.getAllByText(/Week of /).length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText(/Showing 2 events/)).toBeInTheDocument();
    },
  );

  it('renders location, description, and the Trumba event link', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent()],
      Total: 1,
    });
    renderOpsTriagePage();

    expect(await screen.findByText('Tower Lawn')).toBeInTheDocument();
    expect(
      screen.getByText('A free, family-friendly outdoor movie night.'),
    ).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /Event page/ });
    expect(link).toHaveAttribute(
      'href',
      expect.stringContaining('204106464'),
    );
  });

  it('filters events by top-level category', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [
        makeOpsEvent(),
        makeOpsEvent({
          Id: 'harvested-2',
          Source_Id: '111',
          Title: 'Alumni Awards Reception',
          Category_Path: 'Alumni Relations',
          Event_Start: isoDaysFromNow(9),
        }),
      ],
      Total: 2,
    });
    renderOpsTriagePage();
    await screen.findByText('Screen on the Green');

    await userEvent.selectOptions(
      screen.getByLabelText('Category'),
      'Alumni Relations',
    );

    expect(screen.getByText('Alumni Awards Reception')).toBeInTheDocument();
    expect(screen.queryByText('Screen on the Green')).not.toBeInTheDocument();
  });

  it('marks canceled events', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent({ Is_Canceled: true })],
      Total: 1,
    });
    renderOpsTriagePage();

    expect(await screen.findByText('Canceled')).toBeInTheDocument();
  });

  it('shows an empty state when no events are upcoming', async () => {
    listOpsEventsMock.mockResolvedValue({ Items: [], Total: 0 });
    renderOpsTriagePage();

    expect(await screen.findByText('No upcoming events')).toBeInTheDocument();
  });

  it('surfaces load errors', async () => {
    listOpsEventsMock.mockRejectedValue(new Error('Feed unavailable'));
    renderOpsTriagePage();

    expect(await screen.findByText('Feed unavailable')).toBeInTheDocument();
  });
});
