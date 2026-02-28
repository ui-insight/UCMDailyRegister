interface AIEditControlsProps {
  onTriggerEdit: (newsletterType: 'tdr' | 'myui') => void;
  onAcceptEdit: () => void;
  onRejectEdit: () => void;
  loading: boolean;
  hasAIEdit: boolean;
  targetNewsletter: 'tdr' | 'myui' | 'both';
  confidence?: number;
}

export default function AIEditControls({
  onTriggerEdit,
  onAcceptEdit,
  onRejectEdit,
  loading,
  hasAIEdit,
  targetNewsletter,
  confidence,
}: AIEditControlsProps) {
  const confidenceColor =
    confidence === undefined
      ? 'text-gray-400'
      : confidence >= 0.8
        ? 'text-green-600'
        : confidence >= 0.5
          ? 'text-ui-gold-600'
          : 'text-red-600';

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">AI Edit Controls</h3>

      {loading && (
        <div className="mb-3 p-3 bg-ui-gold-50 border border-ui-gold-200 rounded-md">
          <div className="flex items-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-ui-gold-600 border-t-transparent rounded-full" />
            <span className="text-sm text-ui-gold-700 font-medium">AI is editing...</span>
          </div>
          <p className="text-xs text-ui-gold-600 mt-1">This may take a few seconds.</p>
        </div>
      )}

      {/* Trigger buttons */}
      {!hasAIEdit && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 mb-2">Run AI editing for:</p>
          <div className="flex gap-2">
            {(targetNewsletter === 'tdr' || targetNewsletter === 'both') && (
              <button
                onClick={() => onTriggerEdit('tdr')}
                disabled={loading}
                className="flex-1 px-3 py-2 text-sm font-medium rounded-md bg-ui-gold-600 text-white hover:bg-ui-gold-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Processing...' : 'TDR (Daily Register)'}
              </button>
            )}
            {(targetNewsletter === 'myui' || targetNewsletter === 'both') && (
              <button
                onClick={() => onTriggerEdit('myui')}
                disabled={loading}
                className="flex-1 px-3 py-2 text-sm font-medium rounded-md bg-ui-clearwater-600 text-white hover:bg-ui-clearwater-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Processing...' : 'My UI (Student)'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* After AI edit */}
      {hasAIEdit && (
        <div className="space-y-3">
          {confidence !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">AI Confidence</span>
              <span className={`text-sm font-medium ${confidenceColor}`}>
                {Math.round(confidence * 100)}%
              </span>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={onAcceptEdit}
              className="flex-1 px-3 py-2 text-sm font-medium rounded-md bg-green-600 text-white hover:bg-green-700"
            >
              Accept & Finalize
            </button>
            <button
              onClick={onRejectEdit}
              className="flex-1 px-3 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200"
            >
              Edit Manually
            </button>
          </div>

          <div className="flex gap-2">
            {(targetNewsletter === 'tdr' || targetNewsletter === 'both') && (
              <button
                onClick={() => onTriggerEdit('tdr')}
                disabled={loading}
                className="flex-1 px-2 py-1.5 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
              >
                {loading ? '...' : 'Re-run TDR'}
              </button>
            )}
            {(targetNewsletter === 'myui' || targetNewsletter === 'both') && (
              <button
                onClick={() => onTriggerEdit('myui')}
                disabled={loading}
                className="flex-1 px-2 py-1.5 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
              >
                {loading ? '...' : 'Re-run My UI'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
