import SubmissionForm from '../components/submission/SubmissionForm';

export default function SubmitPage() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Submit an Announcement</h2>
      <p className="text-gray-500 mb-6">
        Submit news, events, job postings, and other announcements for The Daily Register or My UI.
      </p>
      <SubmissionForm />
    </div>
  );
}
