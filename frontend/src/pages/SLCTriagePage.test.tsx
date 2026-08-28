import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listHarvestedEvents, runHarvest } from '../api/slcEvents';
import type { HarvestedEvent } from '../types/harvestedEvent';
import { getSubmitterRole } from '../utils/submitterRole';
import SLCTriagePage from './SLCTriagePage';

vi.mock('../api/slcEvents', () => ({
  listHarvestedEvents: vi.fn(),
  runHarvest: vi.fn(),
}));

vi.mock('../utils/submitterRole', () => ({
  getSubmitterRole: vi.fn(),
}));

const listHarvestedEventsMock = vi.mocked(listHarvestedEvents);
const runHarvestMock = vi.mocked(runHarvest);
const getSubmitterRoleMock = vi.mocked(getSubmitterRole);

function renderTriagePage() {
  return render(
    <MemoryRouter>
      <SLCTriagePage />
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

function makeHarvestedEvent(overrides: Partial<HarvestedEvent> = {}): HarvestedEvent {
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
    SLC_Review_Status: 'new',
    First_Seen_At: isoDaysFromNow(0),
    Last_Seen_At: isoDaysFromNow(0),
    ...overrides,
  };
}

describe('SLCTriagePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSubmitterRoleMock.mockReturnValue('slc');
  });

  it('blocks viewers without the slc or staff role', () => {
    getSubmitterRoleMock.mockReturnValue('public');
    renderTriagePage();
    expect(screen.getByText('Restricted page')).toBeInTheDocument();
    expect(listHarvestedEventsMock).not.toHaveBeenCalled();
  });

  it('lists harvested events grouped by week for SLC viewers', async () => {
    listHarvestedEventsMock.mockResolvedValue({
      Items: [
        makeHarvestedEvent(),
        makeHarvestedEvent({
          Id: 'harvested-2',
          Source_Id: '111',
          Title: 'Chamber Music Series',
          Category_Path: 'University of Idaho - CLASS',
          Event_Start: isoDaysFromNow(9),
          Event_End: null,
        }),
      ],
      Total: 2,
    });
    renderTriagePage();

    expect(await screen.findByText('Screen on the Green')).toBeInTheDocument();
    expect(screen.getByText('Chamber Music Series')).toBeInTheDocument();
    expect(screen.getAllByText(/Week of /).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Showing 2 events/)).toBeInTheDocument();
  });

  it('filters events by top-level category', async () => {
    listHarvestedEventsMock.mockResolvedValue({
      Items: [
        makeHarvestedEvent(),
        makeHarvestedEvent({
          Id: 'harvested-2',
          Source_Id: '111',
          Title: 'Chamber Music Series',
          Category_Path: 'University of Idaho - CLASS',
          Event_Start: isoDaysFromNow(9),
        }),
      ],
      Total: 2,
    });
    renderTriagePage();
    await screen.findByText('Screen on the Green');

    await userEvent.selectOptions(
      screen.getByLabelText('Category'),
      'Student Affairs',
    );

    expect(screen.getByText('Screen on the Green')).toBeInTheDocument();
    expect(screen.queryByText('Chamber Music Series')).not.toBeInTheDocument();
  });

  it('marks canceled events', async () => {
    listHarvestedEventsMock.mockResolvedValue({
      Items: [makeHarvestedEvent({ Is_Canceled: true })],
      Total: 1,
    });
    renderTriagePage();
    expect(await screen.findByText('Canceled')).toBeInTheDocument();
  });

  it('refreshes the feed and refetches events', async () => {
    listHarvestedEventsMock.mockResolvedValue({ Items: [], Total: 0 });
    runHarvestMock.mockResolvedValue({
      Fetched: 200,
      Created: 12,
      Updated: 3,
      Unchanged: 185,
      Skipped: 0,
    });
    renderTriagePage();
    await screen.findByText('No harvested events yet');

    await userEvent.click(screen.getByRole('button', { name: 'Refresh events' }));

    expect(
      await screen.findByText('Feed refreshed: 12 new, 3 updated, 185 unchanged.'),
    ).toBeInTheDocument();
    expect(runHarvestMock).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(listHarvestedEventsMock).toHaveBeenCalledTimes(2));
  });

  it('shows an error when the refresh fails', async () => {
    listHarvestedEventsMock.mockResolvedValue({ Items: [], Total: 0 });
    runHarvestMock.mockRejectedValue(
      new Error('Could not fetch the university events feed. Try again shortly.'),
    );
    renderTriagePage();
    await screen.findByText('No harvested events yet');

    await userEvent.click(screen.getByRole('button', { name: 'Refresh events' }));

    expect(
      await screen.findByText(
        'Could not fetch the university events feed. Try again shortly.',
      ),
    ).toBeInTheDocument();
  });
});
