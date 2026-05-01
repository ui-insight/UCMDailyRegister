import { useState } from 'react';
import { Button } from '../common';

interface AIEditControlsProps {
  onTriggerEdit: (newsletterType: 'tdr' | 'myui', editorInstructions?: string) => void;
  onAcceptEdit: () => void;
  onRejectEdit: () => void;
  loading: boolean;
  hasAIEdit: boolean;
  // Accepts "none" so SLC-only submissions type-check, though AI editing is never
  // triggered for them — all button branches below gate on 'tdr'/'myui'/'both'.
  targetNewsletter: 'tdr' | 'myui' | 'both' | 'none';
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
  const [editorFeedback, setEditorFeedback] = useState('');
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
              <Button
                onClick={() => onTriggerEdit('tdr')}
                disabled={loading}
                variant="primary"
                className="flex-1"
              >
                {loading ? 'Processing...' : 'TDR (Daily Register)'}
              </Button>
            )}
            {(targetNewsletter === 'myui' || targetNewsletter === 'both') && (
              <Button
                onClick={() => onTriggerEdit('myui')}
                disabled={loading}
                className="flex-1 bg-ui-clearwater-600 hover:bg-ui-clearwater-700"
              >
                {loading ? 'Processing...' : 'My UI (Student)'}
              </Button>
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
            <Button
              onClick={onAcceptEdit}
              variant="success"
              className="flex-1"
              title="Accept the AI-suggested edit as the final version"
            >
              Accept AI Edit
            </Button>
            <Button
              onClick={onRejectEdit}
              variant="secondary"
              className="flex-1"
            >
              Edit Manually
            </Button>
          </div>

          <div className="space-y-2 rounded-md border border-gray-200 bg-gray-50 p-3">
            <label htmlFor="editor-ai-feedback" className="block text-xs font-medium text-gray-600">
              Editor feedback
            </label>
            <textarea
              id="editor-ai-feedback"
              value={editorFeedback}
              onChange={(event) => setEditorFeedback(event.target.value)}
              rows={3}
              placeholder="e.g., tighten the first sentence and make the tone less formal"
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
            />
            <div className="flex gap-2">
              {(targetNewsletter === 'tdr' || targetNewsletter === 'both') && (
                <Button
                  onClick={() => onTriggerEdit('tdr', editorFeedback)}
                  disabled={loading || !editorFeedback.trim()}
                  variant="secondary"
                  size="sm"
                  className="flex-1"
                >
                  {loading ? '...' : 'Revise TDR'}
                </Button>
              )}
              {(targetNewsletter === 'myui' || targetNewsletter === 'both') && (
                <Button
                  onClick={() => onTriggerEdit('myui', editorFeedback)}
                  disabled={loading || !editorFeedback.trim()}
                  variant="secondary"
                  size="sm"
                  className="flex-1"
                >
                  {loading ? '...' : 'Revise My UI'}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
