import type { Submission } from '../../types/submission';

interface OriginalSubmissionFieldsProps {
  submission: Pick<Submission, 'Original_Headline' | 'Original_Body' | 'Links'>;
}

/**
 * The submitter's original headline, body and links, read-only. Shared by the
 * Edit page's "Original submission" column and the Builder's original-entry
 * panel so both show the same reference copy.
 */
export default function OriginalSubmissionFields({ submission }: OriginalSubmissionFieldsProps) {
  const links = [...submission.Links].sort((a, b) => a.Display_Order - b.Display_Order);
  return (
    <>
      <div>
        <p className="mb-1 text-xs font-medium text-gray-500">Headline</p>
        <p className="break-words text-sm font-medium text-gray-900">
          {submission.Original_Headline}
        </p>
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-gray-500">Body</p>
        <p className="break-words whitespace-pre-wrap text-sm leading-6 text-gray-700">
          {submission.Original_Body}
        </p>
      </div>
      {links.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-gray-500">Submitted links</p>
          <ul className="space-y-1">
            {links.map((link) => (
              <li key={link.Id} className="text-sm text-gray-700">
                {link.Anchor_Text?.trim() && (
                  <span className="font-medium">{link.Anchor_Text} — </span>
                )}
                <span className="break-all text-gray-500">{link.Url}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
