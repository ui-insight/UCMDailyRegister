import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

export default function DashboardPage() {
  const [health, setHealth] = useState<string>('checking...');

  useEffect(() => {
    apiFetch<{ status: string }>('/health')
      .then((data) => setHealth(data.status))
      .catch(() => setHealth('error'));
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Editor Dashboard</h2>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-sm text-gray-500">
          API Status: <span className={health === 'ok' ? 'text-green-600 font-medium' : 'text-red-600'}>{health}</span>
        </p>
        <p className="text-gray-600 mt-4">Submission list and filters coming in Phase 4.</p>
      </div>
    </div>
  );
}
