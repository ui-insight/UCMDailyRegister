import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

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
}

interface ActiveSchedule {
  Config: ScheduleConfig;
  Next_Publish_Date: string;
  Submission_Deadline: string;
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

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const MONTH_NAMES = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

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

export default function SettingsPage() {
  const [scheduleConfigs, setScheduleConfigs] = useState<ScheduleConfig[]>([]);
  const [activeTdr, setActiveTdr] = useState<ActiveSchedule | null>(null);
  const [activeMyui, setActiveMyui] = useState<ActiveSchedule | null>(null);
  const [aiSettings, setAiSettings] = useState<AISettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [configs, tdr, myui, ai] = await Promise.all([
        apiFetch<ScheduleConfig[]>('/schedule/configs').catch(() => [] as ScheduleConfig[]),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=tdr').catch(() => null),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=myui').catch(() => null),
        apiFetch<AISettings>('/settings/ai').catch(() => null),
      ]);
      setScheduleConfigs(configs);
      setActiveTdr(tdr);
      setActiveMyui(myui);
      setAiSettings(ai);
    } catch (err) {
      console.error('Failed to load settings:', err);
      setLoadError('Failed to load settings. The backend may be unavailable.');
    } finally {
      setLoading(false);
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

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>

      {/* LLM Provider */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
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
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Schedule</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* TDR */}
          <div className="border rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">The Daily Register</h4>
            {activeTdr ? (
              <dl className="text-sm space-y-2">
                <div>
                  <dt className="text-xs text-gray-500">Mode</dt>
                  <dd className="text-gray-900 capitalize">{activeTdr.Config.Mode.replace('_', ' ')}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Schedule</dt>
                  <dd className="text-gray-700 text-xs">{activeTdr.Config.Submission_Deadline_Description}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Next Publish Date</dt>
                  <dd className="text-gray-900 font-medium">
                    {new Date(activeTdr.Next_Publish_Date).toLocaleDateString('en-US', {
                      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Submission Deadline</dt>
                  <dd className="text-ui-gold-700 font-medium">
                    {new Date(activeTdr.Submission_Deadline).toLocaleString('en-US', {
                      weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit',
                    })}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-xs text-gray-500">No active config</p>
            )}
          </div>

          {/* My UI */}
          <div className="border rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">My UI</h4>
            {activeMyui ? (
              <dl className="text-sm space-y-2">
                <div>
                  <dt className="text-xs text-gray-500">Mode</dt>
                  <dd className="text-gray-900 capitalize">{activeMyui.Config.Mode.replace('_', ' ')}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Schedule</dt>
                  <dd className="text-gray-700 text-xs">{activeMyui.Config.Submission_Deadline_Description}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Next Publish Date</dt>
                  <dd className="text-gray-900 font-medium">
                    {new Date(activeMyui.Next_Publish_Date).toLocaleDateString('en-US', {
                      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Submission Deadline</dt>
                  <dd className="text-ui-gold-700 font-medium">
                    {new Date(activeMyui.Submission_Deadline).toLocaleString('en-US', {
                      weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit',
                    })}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-xs text-gray-500">No active config</p>
            )}
          </div>
        </div>
      </div>

      {/* All Schedule Configs */}
      <div className="bg-white rounded-lg shadow p-6">
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
              </tr>
            </thead>
            <tbody className="divide-y">
              {scheduleConfigs.map((config) => (
                <tr key={config.Id}>
                  <td className="py-2 font-medium text-gray-900">
                    {config.Newsletter_Type === 'tdr' ? 'TDR' : 'My UI'}
                  </td>
                  <td className="py-2 text-gray-700 capitalize">
                    {config.Mode.replace('_', ' ')}
                  </td>
                  <td className="py-2 text-gray-700">
                    {config.Is_Daily
                      ? 'Daily (weekdays)'
                      : config.Publish_Day_Of_Week !== null
                        ? `Weekly (${DAY_NAMES[config.Publish_Day_Of_Week]})`
                        : 'Not published'}
                  </td>
                  <td className="py-2 text-gray-700 text-xs">
                    {config.Submission_Deadline_Description}
                  </td>
                  <td className="py-2 text-gray-700">
                    {config.Active_Start_Month && config.Active_End_Month
                      ? `${MONTH_NAMES[config.Active_Start_Month]} - ${MONTH_NAMES[config.Active_End_Month]}`
                      : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
