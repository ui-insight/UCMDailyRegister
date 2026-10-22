export default function PrivacyNotice({ slcOnly = false }: { slcOnly?: boolean }) {
  return (
    <aside aria-label="How we use your information" className="rounded-md bg-gray-50 p-4 text-sm text-gray-600">
      <p className="font-medium text-gray-800">How we use your information</p>
      <p className="mt-1">
        UCM uses your name and email to follow up about this submission. Contact fields are
        not automatically published. {slcOnly
          ? 'SLC event details are shared with authorized university reviewers.'
          : 'Announcement copy may be published. Editors may send copy, notes, links and editing instructions to university or external AI services.'}
      </p>
      <p className="mt-1">
        Include only information needed for the announcement or event. Do not include student
        records, health or financial information, passwords, or other sensitive data in text,
        links or images. Contact information you put in the copy may appear with that copy.
      </p>
    </aside>
  );
}
