import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

interface ScheduleConfig {
  id: string;
  newsletter_type: string;
  mode: string;
  submission_deadline_description: string;
  deadline_day_of_week: number | null;
  deadline_time: string;
  publish_day_of_week: number | null;
  is_daily: boolean;
  active_start_month: number | null;
  active_end_month: number | null;
}

interface ActiveSchedule {
  config: ScheduleConfig;
  next_publish_date: string;
  submission_deadline: string;
}

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const MONTH_NAMES = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export default function SettingsPage() {
  const [scheduleConfigs, setScheduleConfigs] = useState<ScheduleConfig[]>([]);
  const [activeTdr, setActiveTdr] = useState<ActiveSchedule | null>(null);
  const [activeMyui, setActiveMyui] = useState<ActiveSchedule | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [configs, tdr, myui] = await Promise.all([
        apiFetch<ScheduleConfig[]>('/schedule/configs'),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=tdr').catch(() => null),
        apiFetch<ActiveSchedule>('/schedule/active?newsletter_type=myui').catch(() => null),
      ]);
      setScheduleConfigs(configs);
      setActiveTdr(tdr);
      setActiveMyui(myui);
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>

      {/* LLM Provider */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Provider</h3>
        <p className="text-sm text-gray-600 mb-4">
          The LLM provider is configured via environment variables. Set <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">LLM_PROVIDER</code> to
          "claude" or "openai" and provide the corresponding API key.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">Claude (Anthropic)</h4>
            <dl className="text-xs space-y-1">
              <div className="flex gap-2">
                <dt className="text-gray-500 w-32">Env variable:</dt>
                <dd className="font-mono text-gray-700">ANTHROPIC_API_KEY</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-gray-500 w-32">Model:</dt>
                <dd className="font-mono text-gray-700">CLAUDE_MODEL</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-gray-500 w-32">Default model:</dt>
                <dd className="text-gray-700">claude-sonnet-4-20250514</dd>
              </div>
            </dl>
          </div>
          <div className="border rounded-lg p-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">OpenAI</h4>
            <dl className="text-xs space-y-1">
              <div className="flex gap-2">
                <dt className="text-gray-500 w-32">Env variable:</dt>
                <dd className="font-mono text-gray-700">OPENAI_API_KEY</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-gray-500 w-32">Model:</dt>
                <dd className="font-mono text-gray-700">OPENAI_MODEL</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-gray-500 w-32">Default model:</dt>
                <dd className="text-gray-700">gpt-4o</dd>
              </div>
            </dl>
          </div>
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
                  <dd className="text-gray-900 capitalize">{activeTdr.config.mode.replace('_', ' ')}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Schedule</dt>
                  <dd className="text-gray-700 text-xs">{activeTdr.config.submission_deadline_description}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Next Publish Date</dt>
                  <dd className="text-gray-900 font-medium">
                    {new Date(activeTdr.next_publish_date).toLocaleDateString('en-US', {
                      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Submission Deadline</dt>
                  <dd className="text-amber-700 font-medium">
                    {new Date(activeTdr.submission_deadline).toLocaleString('en-US', {
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
                  <dd className="text-gray-900 capitalize">{activeMyui.config.mode.replace('_', ' ')}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Schedule</dt>
                  <dd className="text-gray-700 text-xs">{activeMyui.config.submission_deadline_description}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Next Publish Date</dt>
                  <dd className="text-gray-900 font-medium">
                    {new Date(activeMyui.next_publish_date).toLocaleDateString('en-US', {
                      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Submission Deadline</dt>
                  <dd className="text-amber-700 font-medium">
                    {new Date(activeMyui.submission_deadline).toLocaleString('en-US', {
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
                <tr key={config.id}>
                  <td className="py-2 font-medium text-gray-900">
                    {config.newsletter_type === 'tdr' ? 'TDR' : 'My UI'}
                  </td>
                  <td className="py-2 text-gray-700 capitalize">
                    {config.mode.replace('_', ' ')}
                  </td>
                  <td className="py-2 text-gray-700">
                    {config.is_daily
                      ? 'Daily (weekdays)'
                      : config.publish_day_of_week !== null
                        ? `Weekly (${DAY_NAMES[config.publish_day_of_week]})`
                        : 'Not published'}
                  </td>
                  <td className="py-2 text-gray-700 text-xs">
                    {config.submission_deadline_description}
                  </td>
                  <td className="py-2 text-gray-700">
                    {config.active_start_month && config.active_end_month
                      ? `${MONTH_NAMES[config.active_start_month]} - ${MONTH_NAMES[config.active_end_month]}`
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
