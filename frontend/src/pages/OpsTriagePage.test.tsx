import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  acknowledgeOpsUpstreamChange,
  addOpsNeed,
  listOpsEvents,
  removeOpsNeed,
  setOpsNeedVerdict,
  updateOpsEvent,
} from '../api/opsEvents';
import type { OpsEvent, OpsNeed } from '../types/harvestedEvent';
import { getSubmitterRole } from '../utils/submitterRole';
import OpsTriagePage from './OpsTriagePage';

vi.mock('../api/opsEvents', () => ({
  acknowledgeOpsUpstreamChange: vi.fn(),
  addOpsNeed: vi.fn(),
  listOpsEvents: vi.fn(),
  removeOpsNeed: vi.fn(),
  setOpsNeedVerdict: vi.fn(),
  updateOpsEvent: vi.fn(),
}));

vi.mock('../utils/submitterRole', () => ({
  getSubmitterRole: vi.fn(),
}));

const listOpsEventsMock = vi.mocked(listOpsEvents);
const updateOpsEventMock = vi.mocked(updateOpsEvent);
const addOpsNeedMock = vi.mocked(addOpsNeed);
const acknowledgeOpsUpstreamChangeMock = vi.mocked(acknowledgeOpsUpstreamChange);
const removeOpsNeedMock = vi.mocked(removeOpsNeed);
const setOpsNeedVerdictMock = vi.mocked(setOpsNeedVerdict);

function makeNeed(overrides: Partial<OpsNeed> = {}): OpsNeed {
  return {
    Need: 'catering',
    Confidence: 'high',
    Rationale: "Says 'reception to follow'.",
    Verdict: 'suggested',
    Source: 'ai',
    ...overrides,
  };
}
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
    Ops_Upstream_Changed_At: null,
    Needs: [],
    Needs_Assessed: false,
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

  it('renders suggested-need chips with confidence and rationale', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [
        makeOpsEvent({
          Needs_Assessed: true,
          Needs: [
            makeNeed(),
            makeNeed({
              Need: 'outdoor_space',
              Confidence: 'medium',
              Rationale: 'Held on the Tower Lawn.',
            }),
          ],
        }),
      ],
      Total: 1,
    });
    renderOpsTriagePage();

    const cateringChip = await screen.findByTitle(
      "high confidence — Says 'reception to follow'.",
    );
    expect(cateringChip).toHaveTextContent('Catering');
    expect(
      screen.getByTitle('medium confidence — Held on the Tower Lawn.'),
    ).toHaveTextContent('Outdoor Space');
  });

  it('confirms and rejects suggested needs', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [
        makeOpsEvent({
          Needs_Assessed: true,
          Needs: [makeNeed(), makeNeed({ Need: 'tabling', Confidence: 'low' })],
        }),
      ],
      Total: 1,
    });
    setOpsNeedVerdictMock.mockResolvedValue(
      makeOpsEvent({
        Needs_Assessed: true,
        Needs: [
          makeNeed({ Verdict: 'confirmed' }),
          makeNeed({ Need: 'tabling', Confidence: 'low' }),
        ],
      }),
    );
    renderOpsTriagePage();
    await screen.findByText('Catering');

    await userEvent.click(
      screen.getByRole('button', { name: 'Confirm Catering for Screen on the Green' }),
    );
    expect(setOpsNeedVerdictMock).toHaveBeenCalledWith(
      'harvested-1', 'catering', 'confirmed',
    );
    expect(await screen.findByText('✓ Catering')).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole('button', { name: 'Reject Tabling for Screen on the Green' }),
    );
    expect(setOpsNeedVerdictMock).toHaveBeenLastCalledWith(
      'harvested-1', 'tabling', 'rejected',
    );
  });

  it('restores a rejected need', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [
        makeOpsEvent({
          Needs_Assessed: true,
          Needs: [makeNeed({ Verdict: 'rejected' })],
        }),
      ],
      Total: 1,
    });
    setOpsNeedVerdictMock.mockResolvedValue(
      makeOpsEvent({ Needs_Assessed: true, Needs: [makeNeed()] }),
    );
    renderOpsTriagePage();
    await screen.findByText('Catering');

    await userEvent.click(
      screen.getByRole('button', { name: 'Restore Catering for Screen on the Green' }),
    );
    expect(setOpsNeedVerdictMock).toHaveBeenCalledWith(
      'harvested-1', 'catering', 'suggested',
    );
  });

  it('adds a need the AI missed and removes a staff-added one', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent({ Needs_Assessed: true, Needs: [] })],
      Total: 1,
    });
    const staffNeed = makeNeed({
      Need: 'alcohol_service',
      Confidence: null,
      Rationale: '',
      Verdict: 'confirmed',
      Source: 'staff',
    });
    addOpsNeedMock.mockResolvedValue(
      makeOpsEvent({ Needs_Assessed: true, Needs: [staffNeed] }),
    );
    removeOpsNeedMock.mockResolvedValue(
      makeOpsEvent({ Needs_Assessed: true, Needs: [] }),
    );
    renderOpsTriagePage();
    await screen.findByText('No service needs detected');

    await userEvent.selectOptions(
      screen.getByLabelText('Add need to Screen on the Green'),
      'alcohol_service',
    );
    expect(addOpsNeedMock).toHaveBeenCalledWith('harvested-1', 'alcohol_service');
    expect(await screen.findByText('✓ Alcohol Service')).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole('button', {
        name: 'Remove Alcohol Service from Screen on the Green',
      }),
    );
    expect(removeOpsNeedMock).toHaveBeenCalledWith('harvested-1', 'alcohol_service');
    expect(
      await screen.findByText('No service needs detected'),
    ).toBeInTheDocument();
  });

  it('requests the selected need filter from the API', async () => {
    listOpsEventsMock.mockResolvedValue({ Items: [], Total: 0 });
    renderOpsTriagePage();
    await screen.findByText('No upcoming events');

    await userEvent.selectOptions(screen.getByLabelText('Need'), 'catering');

    expect(listOpsEventsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ need: 'catering' }),
    );
  });

  it('shows an unobtrusive note for assessed events with no needs', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent({ Needs_Assessed: true, Needs: [] })],
      Total: 1,
    });
    renderOpsTriagePage();

    expect(
      await screen.findByText('No service needs detected'),
    ).toBeInTheDocument();
  });

  it('marks unassessed events as awaiting assessment', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent()],
      Total: 1,
    });
    renderOpsTriagePage();

    expect(
      await screen.findByText('Awaiting AI assessment'),
    ).toBeInTheDocument();
  });

  it('marks canceled events', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent({ Is_Canceled: true })],
      Total: 1,
    });
    renderOpsTriagePage();

    expect(await screen.findByText('Canceled')).toBeInTheDocument();
  });

  it('marks an event reviewed and shows the badge', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent()],
      Total: 1,
    });
    updateOpsEventMock.mockResolvedValue(
      makeOpsEvent({ Ops_Review_Status: 'reviewed' }),
    );
    renderOpsTriagePage();
    await screen.findByText('Screen on the Green');

    await userEvent.click(
      screen.getByRole('checkbox', { name: 'Mark Screen on the Green reviewed' }),
    );

    expect(updateOpsEventMock).toHaveBeenCalledWith('harvested-1', {
      Ops_Review_Status: 'reviewed',
    });
    // Both the toggle and the new status badge render "Reviewed".
    expect(await screen.findAllByText('Reviewed')).toHaveLength(2);
    expect(
      screen.getByRole('checkbox', { name: 'Mark Screen on the Green reviewed' }),
    ).toBeChecked();
  });

  it('dismisses an event out of the default view and restores it from the dismissed view', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent()],
      Total: 1,
    });
    updateOpsEventMock.mockResolvedValue(
      makeOpsEvent({ Ops_Review_Status: 'dismissed' }),
    );
    renderOpsTriagePage();
    await screen.findByText('Screen on the Green');

    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));

    expect(updateOpsEventMock).toHaveBeenCalledWith('harvested-1', {
      Ops_Review_Status: 'dismissed',
    });
    expect(screen.queryByText('Screen on the Green')).not.toBeInTheDocument();

    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent({ Ops_Review_Status: 'dismissed' })],
      Total: 1,
    });
    await userEvent.selectOptions(screen.getByLabelText('Status'), 'dismissed');

    expect(await screen.findByText('Screen on the Green')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Restore' }),
    ).toBeInTheDocument();
  });

  it('requests the selected status filter from the API', async () => {
    listOpsEventsMock.mockResolvedValue({ Items: [], Total: 0 });
    renderOpsTriagePage();
    await screen.findByText('No upcoming events');

    await userEvent.selectOptions(screen.getByLabelText('Status'), 'reviewed');

    expect(listOpsEventsMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ review_status: 'reviewed' }),
    );
  });

  it('surfaces update errors', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent()],
      Total: 1,
    });
    updateOpsEventMock.mockRejectedValue(new Error('Update failed'));
    renderOpsTriagePage();
    await screen.findByText('Screen on the Green');

    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));

    expect(await screen.findByText('Update failed')).toBeInTheDocument();
  });

  it('badges reviewed events changed upstream and acknowledges the change', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [
        makeOpsEvent({
          Ops_Review_Status: 'reviewed',
          Ops_Upstream_Changed_At: isoDaysFromNow(0),
        }),
      ],
      Total: 1,
    });
    acknowledgeOpsUpstreamChangeMock.mockResolvedValue(
      makeOpsEvent({ Ops_Review_Status: 'reviewed', Ops_Upstream_Changed_At: null }),
    );
    renderOpsTriagePage();

    expect(
      await screen.findByText(/Updated upstream — the event details changed/),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Acknowledge' }));

    expect(acknowledgeOpsUpstreamChangeMock).toHaveBeenCalledWith('harvested-1');
    expect(
      screen.queryByText(/Updated upstream/),
    ).not.toBeInTheDocument();
  });

  it('shows the canceled variant of the upstream badge', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [
        makeOpsEvent({
          Ops_Review_Status: 'reviewed',
          Ops_Upstream_Changed_At: isoDaysFromNow(0),
          Is_Canceled: true,
        }),
      ],
      Total: 1,
    });
    renderOpsTriagePage();

    expect(
      await screen.findByText(/Canceled upstream — this event was canceled/),
    ).toBeInTheDocument();
  });

  it('shows no upstream badge on unreviewed events', async () => {
    listOpsEventsMock.mockResolvedValue({
      Items: [makeOpsEvent({ Ops_Upstream_Changed_At: isoDaysFromNow(0) })],
      Total: 1,
    });
    renderOpsTriagePage();
    await screen.findByText('Screen on the Green');

    expect(screen.queryByText(/Updated upstream/)).not.toBeInTheDocument();
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
