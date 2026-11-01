import { Link, useLocation } from 'react-router-dom';
import { retiredToolNameFor } from '../utils/retiredTools';

/**
 * Notice shown at the old SLC and Event Services URLs. The page is public:
 * it reveals nothing about the hidden tools' data.
 */
export default function RetiredToolPage() {
  const location = useLocation();
  const toolName = retiredToolNameFor(location.pathname);

  return (
    <div className="min-h-screen bg-white">
      <header className="bg-gray-900">
        <div className="mx-auto max-w-3xl px-6 py-4">
          <img
            src="/ui-logo-gold-white-horizontal.png"
            alt="University of Idaho"
            className="h-8 w-auto"
          />
        </div>
      </header>

      <main className="mx-auto max-w-xl px-6 py-16">
        <p className="text-sm text-ui-silver">UCM News</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ui-black">
          {toolName} is no longer part of UCM News
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-gray-600">
          UCM News now focuses on producing The Daily Register and My UI, so this tool
          has been taken out of the application. Nothing you entered has been deleted.
        </p>
        <p className="mt-3 text-sm leading-relaxed text-gray-600">
          If you have questions about it, contact University Communications and Marketing.
        </p>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            to="/"
            className="inline-flex items-center rounded-lg bg-ui-gold-500 px-4 py-2.5 text-sm font-semibold text-ui-black transition hover:bg-ui-gold-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 focus-visible:ring-offset-2"
          >
            Go to UCM News
          </Link>
          <Link
            to="/submit"
            className="inline-flex items-center rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-ui-black transition hover:border-gray-400 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 focus-visible:ring-offset-2"
          >
            Submit a newsletter item
          </Link>
        </div>
      </main>
    </div>
  );
}
