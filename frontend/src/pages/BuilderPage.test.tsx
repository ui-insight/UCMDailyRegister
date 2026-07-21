import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BuilderPage from './BuilderPage';

const newsletterApiMocks = vi.hoisted(() => ({
  addAcademicDate: vi.fn(),
  addCalendarEvent: vi.fn(),
  addJobPosting: vi.fn(),
  assembleNewsletter: vi.fn(),
  getNewsletter: vi.fn(),
  listCalendarEvents: vi.fn(),
  listJobPostings: vi.fn(),
  listNewsletters: vi.fn(),
  listSections: vi.fn(),
  removeNewsletterExternalItem: vi.fn(),
  removeNewsletterItem: vi.fn(),
  reorderNewsletterItems: vi.fn(),
  updateNewsletterStatus: vi.fn(),
}));

vi.mock('../api/newsletters', () => ({
  ...newsletterApiMocks,
  getExportUrl: (newsletterId: string) => `/api/v1/newsletters/${newsletterId}/export`,
}));

vi.mock('../api/recurringMessages', () => ({
  addRecurringMessageToNewsletter: vi.fn(),
  listRecurringMessageCandidates: vi.fn().mockResolvedValue([]),
  skipRecurringMessageForNewsletter: vi.fn(),
}));

const myUiSections = [
  {
    Id: 'section-news',
    Newsletter_Type: 'myui' as const,
    Name: 'News and Updates',
    Slug: 'news-and-updates',
    Display_Order: 1,
    Description: null,
    Requires_Image: false,
    Image_Dimensions: null,
    Is_Active: true,
  },
  {
    Id: 'section-academic',
    Newsletter_Type: 'myui' as const,
    Name: 'Academic Dates and Deadlines',
    Slug: 'academic-dates-and-deadlines',
    Display_Order: 5,
    Description: 'Include 30 days of upcoming information.',
    Requires_Image: false,
    Image_Dimensions: null,
    Is_Active: true,
  },
];

const tdrSections = [
  {
    Id: 'section-employee-announcements',
    Newsletter_Type: 'tdr' as const,
    Name: 'Employee Announcements',
    Slug: 'employee-announcements',
    Display_Order: 9,
    Description: null,
    Requires_Image: false,
    Image_Dimensions: null,
    Is_Active: true,
  },
  {
    Id: 'section-student-reminders',
    Newsletter_Type: 'tdr' as const,
    Name: 'Reminders for your students',
    Slug: 'reminders-for-your-students',
    Display_Order: 10,
    Description: null,
    Requires_Image: false,
    Image_Dimensions: null,
    Is_Active: true,
  },
];

const newsletter = {
  Id: 'newsletter-1',
  Newsletter_Type: 'myui' as const,
  Publish_Date: '2026-08-24',
  Status: 'draft',
  Created_At: '2026-08-01T12:00:00Z',
  Updated_At: '2026-08-01T12:00:00Z',
  Items: [],
  External_Items: [],
};

const tdrNewsletter = {
  ...newsletter,
  Id: 'tdr-newsletter-1',
  Newsletter_Type: 'tdr' as const,
  Publish_Date: '2026-08-25',
  Items: [
    {
      Id: 'newsletter-item-1',
      Newsletter_Id: 'tdr-newsletter-1',
      Submission_Id: 'submission-1',
      Section_Id: 'section-employee-announcements',
      Position: 0,
      Final_Headline: 'Registration reminder',
      Final_Body: 'Please remind students to register.',
      Run_Number: 1,
    },
  ],
};

const academicDateItem = {
  Id: 'academic-date-1',
  Newsletter_Id: newsletter.Id,
  Section_Id: 'section-academic',
  Source_Type: 'academic_date',
  Source_Id: 'manual-academic-date-1',
  Source_Url: 'https://www.uidaho.edu/registrar/dates-deadlines',
  Event_Start: '2026-09-02T00:00:00',
  Event_End: null,
  Location: null,
  Position: 0,
  Final_Headline: 'Wednesday, Sept. 2 — Register, add or wait list without permission',
  Final_Body: 'Full-term deadline.',
};

beforeEach(() => {
  vi.clearAllMocks();
  newsletterApiMocks.listSections.mockImplementation(async (newsletterType?: string) => (
    newsletterType === 'myui' ? myUiSections : tdrSections
  ));
  newsletterApiMocks.listNewsletters.mockResolvedValue([]);
  newsletterApiMocks.listCalendarEvents.mockResolvedValue([]);
  newsletterApiMocks.listJobPostings.mockResolvedValue([]);
  newsletterApiMocks.assembleNewsletter.mockImplementation(async (request) => (
    request.Newsletter_Type === 'tdr' ? tdrNewsletter : newsletter
  ));
  newsletterApiMocks.addAcademicDate.mockResolvedValue(academicDateItem);
  newsletterApiMocks.getNewsletter.mockResolvedValue({
    ...newsletter,
    External_Items: [academicDateItem],
  });
});

describe('BuilderPage staff-only sections', () => {
  it('shows student reminders after employee announcements and in the move menu', async () => {
    const user = userEvent.setup();
    render(<BuilderPage />);

    const publishDateInput = document.querySelector<HTMLInputElement>('input[type="date"]');
    expect(publishDateInput).not.toBeNull();
    await user.clear(publishDateInput!);
    await user.type(publishDateInput!, '2026-08-25');
    await user.click(screen.getAllByRole('button', { name: 'Assemble Newsletter' })[0]);

    const sectionHeadings = await screen.findAllByRole('heading', { level: 4 });
    expect(sectionHeadings.map((heading) => heading.textContent)).toEqual([
      'Employee Announcements',
      'Reminders for your students',
    ]);

    const moveMenu = screen.getByTitle('Move to section');
    expect(
      within(moveMenu).getByRole('option', { name: 'Reminders for your students' }),
    ).toHaveValue('section-student-reminders');
  });
});

describe('BuilderPage academic dates', () => {
  it('lets a My UI editor paste and add a registrar deadline', async () => {
    const user = userEvent.setup();
    render(<BuilderPage />);

    await user.selectOptions(screen.getAllByRole('combobox')[0], 'myui');
    const publishDateInput = document.querySelector<HTMLInputElement>('input[type="date"]');
    expect(publishDateInput).not.toBeNull();
    await user.clear(publishDateInput!);
    await user.type(publishDateInput!, '2026-08-24');
    await user.click(screen.getAllByRole('button', { name: 'Assemble Newsletter' })[0]);

    expect(await screen.findByRole('link', { name: /open registrar calendar/i })).toHaveAttribute(
      'href',
      'https://www.uidaho.edu/registrar/dates-deadlines',
    );

    const deadlineDate = screen.getByLabelText('Deadline date');
    expect(deadlineDate).toHaveAttribute('min', '2026-08-24');
    expect(deadlineDate).toHaveAttribute('max', '2026-09-23');
    await user.type(deadlineDate, '2026-09-02');
    await user.type(
      screen.getByLabelText('Academic date or deadline'),
      'Register, add or wait list without permission',
    );
    await user.type(screen.getByLabelText('Details (optional)'), 'Full-term deadline.');
    await user.click(screen.getByRole('button', { name: 'Add academic date' }));

    await waitFor(() => {
      expect(newsletterApiMocks.addAcademicDate).toHaveBeenCalledWith('newsletter-1', {
        Academic_Date: '2026-09-02',
        Title: 'Register, add or wait list without permission',
        Description: 'Full-term deadline.',
      });
    });
  });
});
