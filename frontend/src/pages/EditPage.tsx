import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSubmission, updateSubmission } from '../api/submissions';
import { triggerAIEdit, listEditVersions, saveEditorFinal } from '../api/aiEdits';
import type { Submission } from '../types/submission';
import type { AIEditResponse, EditVersion, AIFlag, TextDiff } from '../types/aiEdit';
import DiffViewer from '../components/editor/DiffViewer';
import FlagList from '../components/editor/FlagList';
import AIEditControls from '../components/editor/AIEditControls';
import HeadlineEditor from '../components/editor/HeadlineEditor';
import BodyEditor from '../components/editor/BodyEditor';
import ChangesList from '../components/editor/ChangesList';
import SubmissionMeta from '../components/editor/SubmissionMeta';

type Tab = 'original' | 'ai_edit' | 'editor';

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-100 text-blue-800',
  ai_edited: 'bg-purple-100 text-purple-800',
  in_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  scheduled: 'bg-indigo-100 text-indigo-800',
  published: 'bg-gray-100 text-gray-800',
  rejected: 'bg-red-100 text-red-800',
};

export default function EditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [submission, setSubmission] = useState<Submission | null>(null);
  const [versions, setVersions] = useState<EditVersion[]>([]);
  const [aiEditResult, setAiEditResult] = useState<AIEditResponse | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('original');
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Editor state
  const [editHeadline, setEditHeadline] = useState('');
  const [editBody, setEditBody] = useState('');

  useEffect(() => {
    if (id) loadData();
  }, [id]);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const sub = await getSubmission(id);
      setSubmission(sub);

      try {
        const vers = await listEditVersions(id);
        setVersions(vers);
        // If there's an AI suggested version, pre-populate editor fields
        const aiVersion = vers.find((v) => v.Version_Type === 'ai_suggested');
        const editorVersion = vers.find((v) => v.Version_Type === 'editor_final');
        if (editorVersion) {
          setEditHeadline(editorVersion.Headline);
          setEditBody(editorVersion.Body);
          setActiveTab('editor');
        } else if (aiVersion) {
          setEditHeadline(aiVersion.Headline);
          setEditBody(aiVersion.Body);
          setActiveTab('ai_edit');
        } else {
          setEditHeadline(sub.Original_Headline);
          setEditBody(sub.Original_Body);
        }
      } catch {
        // No versions yet — that's fine
        setEditHeadline(sub.Original_Headline);
        setEditBody(sub.Original_Body);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load submission');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerEdit = async (newsletterType: 'tdr' | 'myui') => {
    if (!id) return;
    setAiLoading(true);
    setError(null);
    try {
      const result = await triggerAIEdit(id, newsletterType);
      setAiEditResult(result);
      setEditHeadline(result.Edited_Headline);
      setEditBody(result.Edited_Body);
      setActiveTab('ai_edit');
      // Refresh data
      const sub = await getSubmission(id);
      setSubmission(sub);
      const vers = await listEditVersions(id);
      setVersions(vers);
      showToast('AI edit complete');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'AI edit failed';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setAiLoading(false);
    }
  };

  const handleAcceptEdit = async () => {
    if (!id) return;
    setSaveLoading(true);
    try {
      const aiVersion = versions.find((v) => v.Version_Type === 'ai_suggested');
      await saveEditorFinal(id, {
        Headline: aiVersion?.Headline || editHeadline,
        Body: aiVersion?.Body || editBody,
        Headline_Case: aiVersion?.Headline_Case || undefined,
      });
      showToast('Edit accepted and finalized');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleRejectEdit = () => {
    // Switch to editor tab for manual editing
    setActiveTab('editor');
  };

  const handleSaveFinal = async () => {
    if (!id) return;
    setSaveLoading(true);
    try {
      const aiVersion = versions.find((v) => v.Version_Type === 'ai_suggested');
      await saveEditorFinal(id, {
        Headline: editHeadline,
        Body: editBody,
        Headline_Case: aiVersion?.Headline_Case || undefined,
      });
      showToast('Final version saved');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!id) return;
    try {
      await updateSubmission(id, { Status: 'approved' } as Partial<Submission>);
      showToast('Submission approved');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve');
    }
  };

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), type === 'error' ? 5000 : 3000);
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading submission...</div>;
  }

  if (error && !submission) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="text-sm text-amber-600 hover:text-amber-700"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  if (!submission) return null;

  const aiVersion = versions.find((v) => v.Version_Type === 'ai_suggested');
  const hasAIEdit = !!aiVersion || !!aiEditResult;

  // Build diff data from aiEditResult or reconstruct from versions
  const headlineDiff: TextDiff | null = aiEditResult?.Headline_Diff || null;
  const bodyDiff: TextDiff | null = aiEditResult?.Body_Diff || null;
  const flags: AIFlag[] = aiEditResult?.Flags || aiVersion?.Flags || [];
  const changesMade: string[] = aiEditResult?.Changes_Made || aiVersion?.Changes_Made || [];
  const confidence = aiEditResult?.Confidence;

  const tabs: { id: Tab; label: string; available: boolean }[] = [
    { id: 'original', label: 'Original', available: true },
    { id: 'ai_edit', label: 'AI Suggested', available: hasAIEdit },
    { id: 'editor', label: 'Final Edit', available: true },
  ];

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 text-white px-4 py-2 rounded-lg shadow-lg text-sm ${
          toast.type === 'error' ? 'bg-red-600' : 'bg-green-600'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-400 hover:text-gray-600"
          >
            &larr;
          </button>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Edit Submission</h2>
            <p className="text-xs text-gray-500">ID: {submission.Id}</p>
          </div>
        </div>
        <span
          className={`text-xs px-3 py-1 rounded-full font-medium ${STATUS_COLORS[submission.Status] || 'bg-gray-100'}`}
        >
          {submission.Status.replace('_', ' ')}
        </span>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-4 text-red-400 hover:text-red-600"
          >
            &times;
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main content area — 3 cols */}
        <div className="lg:col-span-3">
          {/* Tabs */}
          <div className="border-b border-gray-200 mb-4">
            <nav className="flex gap-4">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => tab.available && setActiveTab(tab.id)}
                  disabled={!tab.available}
                  className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-amber-500 text-amber-600'
                      : tab.available
                        ? 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        : 'border-transparent text-gray-300 cursor-not-allowed'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          <div className="bg-white rounded-lg shadow p-6">
            {activeTab === 'original' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Original Headline
                  </label>
                  <p className="text-sm font-medium text-gray-900 bg-gray-50 p-3 rounded">
                    {submission.Original_Headline}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Original Body
                  </label>
                  <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded whitespace-pre-wrap">
                    {submission.Original_Body}
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'ai_edit' && hasAIEdit && (
              <div className="space-y-6">
                {/* Diffs */}
                {headlineDiff && (
                  <DiffViewer diff={headlineDiff} label="Headline Changes" />
                )}
                {!headlineDiff && aiVersion && (
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">
                      AI Headline
                    </label>
                    <p className="text-sm font-medium text-gray-900 bg-green-50 p-3 rounded">
                      {aiVersion.Headline}
                    </p>
                  </div>
                )}

                {bodyDiff && <DiffViewer diff={bodyDiff} label="Body Changes" />}
                {!bodyDiff && aiVersion && (
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">
                      AI Body
                    </label>
                    <p className="text-sm text-gray-700 bg-green-50 p-3 rounded whitespace-pre-wrap">
                      {aiVersion.Body}
                    </p>
                  </div>
                )}

                {/* Flags */}
                {flags.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                      Flags ({flags.length})
                    </h4>
                    <FlagList flags={flags} />
                  </div>
                )}

                {/* Changes made */}
                {changesMade.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                      Changes Made
                    </h4>
                    <ChangesList changes={changesMade} />
                  </div>
                )}
              </div>
            )}

            {activeTab === 'editor' && (
              <div className="space-y-4">
                <HeadlineEditor
                  value={editHeadline}
                  onChange={setEditHeadline}
                  headlineCase={aiVersion?.Headline_Case || null}
                />
                <BodyEditor value={editBody} onChange={setEditBody} />
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    onClick={handleSaveFinal}
                    disabled={saveLoading}
                    className="px-4 py-2 text-sm font-medium rounded-md bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50"
                  >
                    {saveLoading ? 'Saving...' : 'Save Final Version'}
                  </button>
                  {submission.Status === 'in_review' && (
                    <button
                      onClick={handleApprove}
                      className="px-4 py-2 text-sm font-medium rounded-md bg-green-600 text-white hover:bg-green-700"
                    >
                      Approve
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar — 1 col */}
        <div className="space-y-4">
          <AIEditControls
            onTriggerEdit={handleTriggerEdit}
            onAcceptEdit={handleAcceptEdit}
            onRejectEdit={handleRejectEdit}
            loading={aiLoading}
            hasAIEdit={hasAIEdit}
            targetNewsletter={submission.Target_Newsletter}
            confidence={confidence}
          />
          <SubmissionMeta submission={submission} />
        </div>
      </div>
    </div>
  );
}
