import RichBody from './RichBody';

interface SideBySideViewProps {
  originalHeadline: string;
  originalBody: string;
  aiHeadline: string;
  aiBody: string;
}

export default function SideBySideView({
  originalHeadline,
  originalBody,
  aiHeadline,
  aiBody,
}: SideBySideViewProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Original column */}
      <div className="space-y-3">
        <h4 className="text-xs font-medium text-gray-500 uppercase">Original</h4>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Headline
          </label>
          <p className="text-sm font-medium text-gray-900 bg-gray-50 p-3 rounded">
            {originalHeadline}
          </p>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Body
          </label>
          <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded whitespace-pre-wrap">
            {originalBody}
          </p>
        </div>
      </div>

      {/* AI Suggested column */}
      <div className="space-y-3">
        <h4 className="text-xs font-medium text-gray-500 uppercase">AI Suggested</h4>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Headline
          </label>
          <p className="text-sm font-medium text-gray-900 bg-green-50 p-3 rounded">
            {aiHeadline}
          </p>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Body
          </label>
          <RichBody text={aiBody} className="text-sm text-gray-700 bg-green-50 p-3 rounded" />
        </div>
      </div>
    </div>
  );
}
