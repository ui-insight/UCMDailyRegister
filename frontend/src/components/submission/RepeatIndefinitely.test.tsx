import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { listAllowedValues } from '../../api/allowedValues';
import { getValidDates } from '../../api/schedule';
import type { AllowedValue } from '../../types/allowedValue';
import SubmissionForm from './SubmissionForm';
import { buildSubmissionPayload, type SubmissionFormValues } from './submissionPayload';

// "Repeat indefinitely" is a staff-only choice on the submission form (#538).

const submitterRoleMock = vi.hoisted(() => ({ value: 'public' }));

vi.mock('../../api/allowedValues', () => ({ listAllowedValues: vi.fn() }));
vi.mock('../../api/schedule', () => ({ getValidDates: vi.fn() }));
vi.mock('../../api/submissions', () => ({ createSubmission: vi.fn() }));
vi.mock('../../auth/tokenStore', () => ({ getIdentity: () => null }));
vi.mock('../../utils/submitterRole', () => ({
  getSubmitterRole: () => submitterRoleMock.value,
}));

const categories: AllowedValue[] = [
  {
    Id: 'faculty_staff',
    Value_Group: 'Submission_Category',
    Code: 'faculty_staff',
    Label: 'Employee News (Faculty/Staff)',
    Display_Order: 0,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: null,
  },
];

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true, now: new Date(2026, 4, 1, 9, 0, 0) });
  vi.clearAllMocks();
  submitterRoleMock.value = 'public';
  vi.mocked(listAllowedValues).mockResolvedValue(categories);
  vi.mocked(getValidDates).mockResolvedValue({
    dates: [{ date: '2026-05-05', newsletters: ['tdr'] }],
    blackout_dates: [],
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe('Repeat indefinitely on the submission form', () => {
  it('lets staff repeat indefinitely, which makes the end date optional', async () => {
    submitterRoleMock.value = 'staff';
    const user = userEvent.setup();
    render(<SubmissionForm />);

    await user.selectOptions(await screen.findByLabelText('Repeat on a cadence'), 'weekly');
    const endDate = screen.getByLabelText('Stop after');
    expect(endDate).toBeRequired();
    await user.type(endDate, '2026-06-30');

    await user.click(screen.getByRole('checkbox', { name: 'Repeat indefinitely' }));

    expect(endDate).not.toBeRequired();
    expect(endDate).toBeDisabled();
    expect(endDate).toHaveValue('');
    expect(screen.getByText(/repeats until UCM staff set an end date/i)).toBeInTheDocument();

    await user.click(screen.getByRole('checkbox', { name: 'Repeat indefinitely' }));
    expect(endDate).toBeRequired();
    expect(endDate).toBeEnabled();
  });

  it('hides the option for one-time staff schedules', async () => {
    submitterRoleMock.value = 'staff';
    render(<SubmissionForm />);

    await screen.findByLabelText('Repeat on a cadence');
    expect(screen.queryByRole('checkbox', { name: 'Repeat indefinitely' })).not.toBeInTheDocument();
  });

  it('does not offer the option to non-staff submitters', async () => {
    render(<SubmissionForm />);

    await screen.findByLabelText('Your Name');
    expect(screen.queryByLabelText('Repeat on a cadence')).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox', { name: 'Repeat indefinitely' })).not.toBeInTheDocument();
  });
});

describe('Repeat indefinitely in the submission payload', () => {
  const values = (isStaff: boolean): SubmissionFormValues => ({
    category: 'faculty_staff',
    targetNewsletter: 'tdr',
    headline: 'Weekly reminder',
    body: 'Synthetic body.',
    submitterName: 'Test User',
    submitterEmail: 'test@example.edu',
    notes: '',
    surveyEndDate: '',
    links: [],
    schedule: {
      Requested_Date: '2026-05-05',
      Second_Requested_Date: '',
      Repeat_Count: 1,
      Repeat_Note: '',
      Is_Flexible: false,
      Flexible_Deadline: '',
      Recurrence_Type: 'weekly',
      Recurrence_Interval: 1,
      Recurrence_End_Date: '2026-06-30',
      Repeats_Indefinitely: true,
    },
    preferredStudentDates: [],
    isStaff,
    combinesStudentDates: false,
    isJobOpportunity: false,
    jobUrl: '',
    jobTitle: '',
    jobDepartment: '',
    jobLocation: '',
    jobRemoveDate: '',
  });

  it('sends the flag and no end date for staff', () => {
    const [schedule] = buildSubmissionPayload(values(true)).Schedule_Requests ?? [];
    expect(schedule.Repeats_Indefinitely).toBe(true);
    expect(schedule.Recurrence_End_Date).toBeUndefined();
  });

  it('never sends the flag for non-staff', () => {
    const [schedule] = buildSubmissionPayload(values(false)).Schedule_Requests ?? [];
    expect(schedule.Repeats_Indefinitely).toBeUndefined();
    expect(schedule.Recurrence_Type).toBe('once');
  });
});
