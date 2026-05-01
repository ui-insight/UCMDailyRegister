import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';
import {
  getBlackoutDates,
  createBlackoutDate,
  deleteBlackoutDate,
  getModeOverrides,
  createModeOverride,
  deleteModeOverride,
  getCustomDates,
  createCustomDate,
  deleteCustomDate,
} from '../api/schedule';
import type { BlackoutDate, ScheduleModeOverride, CustomPublishDate } from '../types/schedule';
import { formatScheduleFrequency } from '../utils/scheduleFrequency';

interface ScheduleConfig {
  Id: string;
  Newsletter_Type: string;
  Mode: string;
  Submission_Deadline_Description: string;
  Deadline_Day_Of_Week: number | null;
  Deadline_Time: string;
  Publish_Day_Of_Week: number | null;
  Is_Daily: boolean;
  Active_Start_Month: number | null;
  Active_End_Month: number | null;
  Holiday_Shift_Enabled: boolean;
}

interface ActiveSchedule {
  config: ScheduleConfig;
  next_publish_date: string;
  submission_deadline: string;
  active_override: ScheduleModeOverride | null;
}

interface ProviderInfo {
  model: string;
  configured: boolean;
  endpoint_url?: string;
}

interface AISettings {
  active_provider: string;
  active_model: string;
  endpoint_url?: string;
  providers: Record<string, ProviderInfo>;
}

const MONTH_NAMES = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const MODE_LABELS: Record<string, string> = {
  academic_year: 'Academic Year',
  summer: 'Summer',
  winter_break: 'Winter Break',
};

const PROVIDER_LABELS: Record<string, { name: string; envKey: string; envModel: string; description: string }> = {
  claude: {
    name: 'Claude (Anthropic)',
    envKey: 'ANTHROPIC_API_KEY',
    envModel: 'CLAUDE_MODEL',
    description: 'Anthropic cloud AI',
  },
  openai: {
    name: 'OpenAI',
    envKey: 'OPENAI_API_KEY',
    envModel: 'OPENAI_MODEL',
    description: 'OpenAI cloud AI',
  },
  mindrouter: {
    name: 'MindRouter',
    envKey: 'MINDROUTER_API_KEY',
    envModel: 'MINDROUTER_MODEL',
    description: 'University of Idaho on-prem AI',
  },
};

const SETTINGS_SECTIONS = [
  { id: 'ai-provider', label: 'AI Provider' },
  { id: 'current-schedule', label: 'Current Schedule' },
  { id: 'mode-overrides', label: 'Mode Overrides' },
  { id: 'custom-dates', label: 'Custom Dates' },
  { id: 'blackouts', label: 'Blackouts' },
  { id: 'schedule-configs', label: 'Schedule Configs' },
] as const;

export default function SettingsPage() {
  const [scheduleConfigs, setScheduleConfigs] = useState<ScheduleConfig[]>([]);
  const [activeTdr, setActiveTdr] = useState<ActiveSchedule | null>(null);
  const [activeMyui, setActiveMyui] = useState<ActiveSchedule | null>(null);
  const [aiSettings, setAiSettings] = useState<AISettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<(typeof SETTINGS_SECTIONS)[number]['id']>('ai-provider');

  // Schedule management state
  const [blackoutDates, setBlackoutDates] = useState<BlackoutDate[]>([]);
  const [modeOverrides, setModeOverrides] = useState<ScheduleModeOverride[]>([]);
  const [customDates, setCustomDates] = useState<CustomPublishDate[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);

  // Form state
  const [newBlackout, setNewBlackout] = useState({ date: '', newsletter_type: '', description: '' });
  const [newOverride, setNewOverride] = useState({ newsletter_type: 'tdr', mode: 'winter_break', start: '', end: '', description: '' });
  const [newCustomDate, setNewCustomDate] = useState({ newsletter_type: 'tdr', date: '', description: '' });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (loading) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) {
          setActiveSection(visible.target.id as (typeof SETTINGS_SECTIONS)[number]['id']);
        }
      },
      { rootMargin: '-96px 0px -60% 0px', threshold: [0.1, 0.4, 0.7] },
    );

    for (const section of SETTINGS_SECTIONS) {
      const node = document.getElementById(section.id);
      if (node) observer.observe(node);
    }

    return () => observer.disconnect();
  }, [loading]);

  const loadData = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [configs, tdr, myui, ai, blackouts, overrides, custom] = await Promise.all([
        apiFetch<ScheduleConfig[]>('/schedule/configs').catch(() => [] as ScheduleConfig[]),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=tdr').catch(() => null),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=myui').catch(() => null),
        apiFetch<AISettings>('/settings/ai').catch(() => null),
        getBlackoutDates().catch(() => [] as BlackoutDate[]),
        getModeOverrides().catch(() => [] as ScheduleModeOverride[]),
        getCustomDates().catch(() => [] as CustomPublishDate[]),
      ]);
      setScheduleConfigs(configs);
      setActiveTdr(tdr);
      setActiveMyui(myui);
      setAiSettings(ai);
      setBlackoutDates(blackouts);
      setModeOverrides(overrides);
      setCustomDates(custom);
    } catch (err) {
      console.error('Failed to load settings:', err);
      setLoadError('Failed to load settings. The backend may be unavailable.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddBlackout = async () => {
    if (!newBlackout.date) return;
    setActionError(null);
    try {
      await createBlackoutDate({
        Blackout_Date: newBlackout.date,
        Newsletter_Type: newBlackout.newsletter_type || null,
        Description: newBlackout.description || null,
      });
      setNewBlackout({ date: '', newsletter_type: '', description: '' });
      const updated = await getBlackoutDates();
      setBlackoutDates(updated);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to add blackout date');
    }
  };

  const handleDeleteBlackout = async (id: string) => {
    setActionError(null);
    try {
      await deleteBlackoutDate(id);
      setBlackoutDates((prev) => prev.filter((b) => b.Id !== id));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete blackout date');
    }
  };

  const handleAddOverride = async () => {
    if (!newOverride.start || !newOverride.end) return;
    setActionError(null);
    try {
      await createModeOverride({
        Newsletter_Type: newOverride.newsletter_type,
        Override_Mode: newOverride.mode,
        Start_Date: newOverride.start,
        End_Date: newOverride.end,
        Description: newOverride.description || null,
      });
      setNewOverride({ newsletter_type: 'tdr', mode: 'winter_break', start: '', end: '', description: '' });
      const [overrides, tdr, myui] = await Promise.all([
        getModeOverrides(),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=tdr').catch(() => null),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=myui').catch(() => null),
      ]);
      setModeOverrides(overrides);
      setActiveTdr(tdr);
      setActiveMyui(myui);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to add mode override');
    }
  };

  const handleDeleteOverride = async (id: string) => {
    setActionError(null);
    try {
      await deleteModeOverride(id);
      setModeOverrides((prev) => prev.filter((o) => o.Id !== id));
      const [tdr, myui] = await Promise.all([
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=tdr').catch(() => null),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=myui').catch(() => null),
      ]);
      setActiveTdr(tdr);
      setActiveMyui(myui);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete mode override');
    }
  };

  const handleAddCustomDate = async () => {
    if (!newCustomDate.date) return;
    setActionError(null);
    try {
      await createCustomDate({
        Newsletter_Type: newCustomDate.newsletter_type,
        Publish_Date: newCustomDate.date,
        Description: newCustomDate.description || null,
      });
      setNewCustomDate({ newsletter_type: 'tdr', date: '', description: '' });
      const updated = await getCustomDates();
      setCustomDates(updated);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to add custom date');
    }
  };

  const handleDeleteCustomDate = async (id: string) => {
    setActionError(null);
    try {
      await deleteCustomDate(id);
      setCustomDates((prev) => prev.filter((c) => c.Id !== id));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete custom date');
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  if (loadError) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{loadError}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-ui-gold-600 text-white rounded-lg hover:bg-ui-gold-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const renderActiveSchedule = (label: string, active: ActiveSchedule | null) => (
    <div className="border rounded-lg p-4">
      <h4 className="text-sm font-semibold text-gray-900 mb-2">{label}</h4>
      {active ? (
        <dl className="text-sm space-y-2">
          <div>
            <dt className="text-xs text-gray-500">Mode</dt>
            <dd className="text-gray-900 capitalize flex items-center gap-2">
              {MODE_LABELS[active.config.Mode] ?? active.config.Mode}
              {active.active_override && (
                <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800">
                  Override
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500">Schedule</dt>
            <dd className="text-gray-700 text-xs">{active.config.Submission_Deadline_Description}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500">Next Publish Date</dt>
            <dd className="text-gray-900 font-medium">
              {new Date(active.next_publish_date + 'T12:00:00').toLocaleDateString('en-US', {
                weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
              })}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500">Submission Deadline</dt>
            <dd className="text-ui-gold-700 font-medium">
              {new Date(active.submission_deadline).toLocaleString('en-US', {
                weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit',
              })}
            </dd>
          </div>
          {active.config.Holiday_Shift_Enabled && (
            <div>
              <dt className="text-xs text-gray-500">Holiday Shift</dt>
              <dd className="text-green-700 text-xs">
                Enabled — if a publish day falls on a holiday, shifts to the next weekday
              </dd>
            </div>
          )}
        </dl>
      ) : (
        <p className="text-xs text-gray-500">No active config</p>
      )}
    </div>
  );

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>

      {actionError && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {actionError}
          <button onClick={() => setActionError(null)} className="ml-2 text-red-500 hover:text-red-700">&times;</button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[12rem_minmax(0,1fr)]">
        <nav className="lg:sticky lg:top-4 lg:self-start" aria-label="Settings sections">
          <div className="rounded-lg border border-gray-200 bg-white p-2 shadow-sm">
            {SETTINGS_SECTIONS.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                onClick={() => setActiveSection(section.id)}
                className={`block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  activeSection === section.id
                    ? 'bg-ui-gold-50 text-ui-gold-800'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                {section.label}
              </a>
            ))}
          </div>
        </nav>

        <div className="min-w-0">

      {/* LLM Provider */}
      <div id="ai-provider" className="scroll-mt-4 bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Provider</h3>
        <p className="text-sm text-gray-600 mb-4">
          The LLM provider is configured via environment variables. Set <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">LLM_PROVIDER</code> to
          &quot;claude&quot;, &quot;openai&quot;, or &quot;mindrouter&quot; and provide the corresponding API key.
        </p>

        {/* Active provider banner */}
        {aiSettings && (
          <div className="mb-4 rounded-lg bg-ui-clearwater-50 border border-ui-clearwater-200 px-4 py-3 flex items-center gap-3">
            <span className="inline-flex items-center rounded-full bg-ui-clearwater-500 px-2.5 py-0.5 text-xs font-medium text-white">
              Active
            </span>
            <span className="text-sm font-medium text-gray-900">
              {PROVIDER_LABELS[aiSettings.active_provider]?.name ?? aiSettings.active_provider}
            </span>
            <span className="text-sm text-gray-500">—</span>
            <span className="text-sm font-mono text-gray-700">{aiSettings.active_model}</span>
            {aiSettings.endpoint_url && (
              <>
                <span className="text-sm text-gray-500">—</span>
                <span className="text-xs font-mono text-gray-500 truncate">{aiSettings.endpoint_url}</span>
              </>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(['claude', 'openai', 'mindrouter'] as const).map((key) => {
            const meta = PROVIDER_LABELS[key];
            const providerInfo = aiSettings?.providers?.[key];
            const isActive = aiSettings?.active_provider === key;

            return (
              <div
                key={key}
                className={`border rounded-lg p-4 relative ${
                  isActive
                    ? 'border-ui-clearwater-400 bg-ui-clearwater-50 ring-1 ring-ui-clearwater-300'
                    : providerInfo?.configured
                      ? 'border-gray-200'
                      : 'border-gray-200 opacity-60'
                }`}
              >
                {isActive && (
                  <span className="absolute -top-2.5 right-3 inline-flex items-center rounded-full bg-ui-clearwater-500 px-2 py-0.5 text-[10px] font-semibold text-white uppercase tracking-wide">
                    Active
                  </span>
                )}
                <h4 className="text-sm font-semibold text-gray-900 mb-1">{meta.name}</h4>
                <p className="text-xs text-gray-500 mb-3">{meta.description}</p>
                <dl className="text-xs space-y-1">
                  <div className="flex gap-2">
                    <dt className="text-gray-500 w-28">API key env:</dt>
                    <dd className="font-mono text-gray-700">{meta.envKey}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="text-gray-500 w-28">Model env:</dt>
                    <dd className="font-mono text-gray-700">{meta.envModel}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="text-gray-500 w-28">Current model:</dt>
                    <dd className="font-mono text-gray-700">
                      {providerInfo?.model ?? '—'}
                    </dd>
                  </div>
                  {key === 'mindrouter' && providerInfo?.endpoint_url && (
                    <div className="flex gap-2">
                      <dt className="text-gray-500 w-28">Endpoint:</dt>
                      <dd className="font-mono text-gray-700 truncate" title={providerInfo.endpoint_url}>
                        {providerInfo.endpoint_url}
                      </dd>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <dt className="text-gray-500 w-28">Key provided:</dt>
                    <dd className={providerInfo?.configured ? 'text-green-600 font-medium' : 'text-gray-400'}>
                      {providerInfo?.configured ? 'Yes' : 'No'}
                    </dd>
                  </div>
                </dl>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active Schedule Info */}
      <div id="current-schedule" className="scroll-mt-4 bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Schedule</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderActiveSchedule('The Daily Register', activeTdr)}
          {renderActiveSchedule('My UI', activeMyui)}
        </div>
      </div>

      {/* Schedule Mode Overrides */}
      <div id="mode-overrides" className="scroll-mt-4 bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Schedule Mode Overrides</h3>
        <p className="text-sm text-gray-600 mb-4">
          Override the auto-detected schedule mode for a date range. Use this to activate summer mode early, set winter break dates, or handle other schedule transitions.
        </p>

        {/* Add form */}
        <div className="flex flex-wrap items-end gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Newsletter</label>
            <select
              value={newOverride.newsletter_type}
              onChange={(e) => setNewOverride((p) => ({ ...p, newsletter_type: e.target.value }))}
              className="block w-28 rounded border-gray-300 text-sm"
            >
              <option value="tdr">TDR</option>
              <option value="myui">My UI</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Mode</label>
            <select
              value={newOverride.mode}
              onChange={(e) => setNewOverride((p) => ({ ...p, mode: e.target.value }))}
              className="block w-36 rounded border-gray-300 text-sm"
            >
              <option value="winter_break">Winter Break</option>
              <option value="summer">Summer</option>
              <option value="academic_year">Academic Year</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Start Date</label>
            <input
              type="date"
              value={newOverride.start}
              onChange={(e) => setNewOverride((p) => ({ ...p, start: e.target.value }))}
              className="block rounded border-gray-300 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">End Date</label>
            <input
              type="date"
              value={newOverride.end}
              onChange={(e) => setNewOverride((p) => ({ ...p, end: e.target.value }))}
              className="block rounded border-gray-300 text-sm"
            />
          </div>
          <div className="flex-1 min-w-[120px]">
            <label className="block text-xs text-gray-500 mb-1">Description</label>
            <input
              type="text"
              value={newOverride.description}
              onChange={(e) => setNewOverride((p) => ({ ...p, description: e.target.value }))}
              placeholder="e.g., Winter break 2026-27"
              className="block w-full rounded border-gray-300 text-sm"
            />
          </div>
          <button
            onClick={handleAddOverride}
            disabled={!newOverride.start || !newOverride.end}
            className="px-3 py-2 bg-ui-gold-600 text-white text-sm rounded hover:bg-ui-gold-700 disabled:opacity-50 transition-colors"
          >
            Add Override
          </button>
        </div>

        {/* List */}
        {modeOverrides.length > 0 ? (
          <div className="divide-y">
            {modeOverrides.map((o) => (
              <div key={o.Id} className="flex items-center justify-between py-2 text-sm">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-gray-900">{o.Newsletter_Type.toUpperCase()}</span>
                  <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                    {MODE_LABELS[o.Override_Mode] ?? o.Override_Mode}
                  </span>
                  <span className="text-gray-600">
                    {new Date(o.Start_Date + 'T12:00:00').toLocaleDateString()} — {new Date(o.End_Date + 'T12:00:00').toLocaleDateString()}
                  </span>
                  {o.Description && <span className="text-gray-400 text-xs">({o.Description})</span>}
                </div>
                <button
                  onClick={() => handleDeleteOverride(o.Id)}
                  className="text-red-500 hover:text-red-700 text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-400">No active overrides — schedule auto-detects by month.</p>
        )}
      </div>

      {/* Custom Publish Dates (Winter Break) */}
      <div id="custom-dates" className="scroll-mt-4 bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Custom Publish Dates</h3>
        <p className="text-sm text-gray-600 mb-4">
          During winter break (or other custom schedule periods), manually set which dates the newsletter will publish.
          These dates are only used when a winter break mode override is active.
        </p>

        {/* Add form */}
        <div className="flex flex-wrap items-end gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Newsletter</label>
            <select
              value={newCustomDate.newsletter_type}
              onChange={(e) => setNewCustomDate((p) => ({ ...p, newsletter_type: e.target.value }))}
              className="block w-28 rounded border-gray-300 text-sm"
            >
              <option value="tdr">TDR</option>
              <option value="myui">My UI</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Publish Date</label>
            <input
              type="date"
              value={newCustomDate.date}
              onChange={(e) => setNewCustomDate((p) => ({ ...p, date: e.target.value }))}
              className="block rounded border-gray-300 text-sm"
            />
          </div>
          <div className="flex-1 min-w-[120px]">
            <label className="block text-xs text-gray-500 mb-1">Description</label>
            <input
              type="text"
              value={newCustomDate.description}
              onChange={(e) => setNewCustomDate((p) => ({ ...p, description: e.target.value }))}
              placeholder="e.g., Last edition before break"
              className="block w-full rounded border-gray-300 text-sm"
            />
          </div>
          <button
            onClick={handleAddCustomDate}
            disabled={!newCustomDate.date}
            className="px-3 py-2 bg-ui-gold-600 text-white text-sm rounded hover:bg-ui-gold-700 disabled:opacity-50 transition-colors"
          >
            Add Date
          </button>
        </div>

        {/* List */}
        {customDates.length > 0 ? (
          <div className="divide-y">
            {customDates.map((c) => (
              <div key={c.Id} className="flex items-center justify-between py-2 text-sm">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-gray-900">{c.Newsletter_Type.toUpperCase()}</span>
                  <span className="text-gray-700">
                    {new Date(c.Publish_Date + 'T12:00:00').toLocaleDateString('en-US', {
                      weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
                    })}
                  </span>
                  {c.Description && <span className="text-gray-400 text-xs">({c.Description})</span>}
                </div>
                <button
                  onClick={() => handleDeleteCustomDate(c.Id)}
                  className="text-red-500 hover:text-red-700 text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-400">No custom dates set.</p>
        )}
      </div>

      {/* Blackout Dates (Holidays) */}
      <div id="blackouts" className="scroll-mt-4 bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Blackout Dates (Holidays &amp; Closures)</h3>
        <p className="text-sm text-gray-600 mb-4">
          Dates when newsletters should not be published. When holiday shift is enabled on a schedule config
          and a publish day falls on a blackout date, the newsletter automatically shifts to the next weekday.
        </p>

        {/* Add form */}
        <div className="flex flex-wrap items-end gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Date</label>
            <input
              type="date"
              value={newBlackout.date}
              onChange={(e) => setNewBlackout((p) => ({ ...p, date: e.target.value }))}
              className="block rounded border-gray-300 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Applies To</label>
            <select
              value={newBlackout.newsletter_type}
              onChange={(e) => setNewBlackout((p) => ({ ...p, newsletter_type: e.target.value }))}
              className="block w-32 rounded border-gray-300 text-sm"
            >
              <option value="">All Newsletters</option>
              <option value="tdr">TDR Only</option>
              <option value="myui">My UI Only</option>
            </select>
          </div>
          <div className="flex-1 min-w-[120px]">
            <label className="block text-xs text-gray-500 mb-1">Reason</label>
            <input
              type="text"
              value={newBlackout.description}
              onChange={(e) => setNewBlackout((p) => ({ ...p, description: e.target.value }))}
              placeholder="e.g., Labor Day, Thanksgiving Break"
              className="block w-full rounded border-gray-300 text-sm"
            />
          </div>
          <button
            onClick={handleAddBlackout}
            disabled={!newBlackout.date}
            className="px-3 py-2 bg-ui-gold-600 text-white text-sm rounded hover:bg-ui-gold-700 disabled:opacity-50 transition-colors"
          >
            Add Blackout
          </button>
        </div>

        {/* List */}
        {blackoutDates.length > 0 ? (
          <div className="divide-y">
            {blackoutDates.map((b) => (
              <div key={b.Id} className="flex items-center justify-between py-2 text-sm">
                <div className="flex items-center gap-3">
                  <span className="text-gray-700 font-medium">
                    {new Date(b.Blackout_Date + 'T12:00:00').toLocaleDateString('en-US', {
                      weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
                    })}
                  </span>
                  <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                    {b.Newsletter_Type ? b.Newsletter_Type.toUpperCase() : 'All'}
                  </span>
                  {b.Description && <span className="text-gray-400 text-xs">{b.Description}</span>}
                </div>
                <button
                  onClick={() => handleDeleteBlackout(b.Id)}
                  className="text-red-500 hover:text-red-700 text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-400">No blackout dates set.</p>
        )}
      </div>

      {/* All Schedule Configs */}
      <div id="schedule-configs" className="scroll-mt-4 bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Schedule Configurations</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="pb-2 text-xs text-gray-500 font-medium">Newsletter</th>
                <th className="pb-2 text-xs text-gray-500 font-medium">Mode</th>
                <th className="pb-2 text-xs text-gray-500 font-medium">Frequency</th>
                <th className="pb-2 text-xs text-gray-500 font-medium">Deadline</th>
                <th className="pb-2 text-xs text-gray-500 font-medium">Active Months</th>
                <th className="pb-2 text-xs text-gray-500 font-medium">Holiday Shift</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {scheduleConfigs.map((config) => (
                <tr key={config.Id}>
                  <td className="py-2 font-medium text-gray-900">
                    {config.Newsletter_Type === 'tdr' ? 'TDR' : 'My UI'}
                  </td>
                  <td className="py-2 text-gray-700 capitalize">
                    {MODE_LABELS[config.Mode] ?? config.Mode}
                  </td>
                  <td className="py-2 text-gray-700">
                    {formatScheduleFrequency(config)}
                  </td>
                  <td className="py-2 text-gray-700 text-xs">
                    {config.Submission_Deadline_Description}
                  </td>
                  <td className="py-2 text-gray-700">
                    {config.Active_Start_Month && config.Active_End_Month
                      ? `${MONTH_NAMES[config.Active_Start_Month]} - ${MONTH_NAMES[config.Active_End_Month]}`
                      : config.Mode === 'winter_break'
                        ? 'Override only'
                        : 'N/A'}
                  </td>
                  <td className="py-2">
                    {config.Holiday_Shift_Enabled ? (
                      <span className="text-green-600 text-xs font-medium">Enabled</span>
                    ) : (
                      <span className="text-gray-400 text-xs">Off</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
        </div>
      </div>
    </div>
  );
}
