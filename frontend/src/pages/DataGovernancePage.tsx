import { useMemo, useState } from 'react';
import catalog from '../data/governance-catalog.json';

type DataClassification = 'Public' | 'Internal' | 'Confidential' | 'Restricted';
type ExtensionStatus = 'UDM-derived pattern' | 'Communications extension' | 'Operational support';

interface GovernanceColumn {
  name: string;
  description: string;
  classification: DataClassification;
  pii: boolean;
  allowedValueGroup?: string;
}

interface GovernanceTable {
  name: string;
  area: string;
  status: ExtensionStatus;
  description: string;
  steward: string;
  columns: GovernanceColumn[];
  retentionCategory: string;
  sourceSystem: string;
}

const CLASSIFICATION_STYLES: Record<DataClassification, string> = {
  Public: 'bg-status-success-100 text-status-success-800',
  Internal: 'bg-status-info-100 text-status-info-800',
  Confidential: 'bg-status-warning-100 text-status-warning-800',
  Restricted: 'bg-status-error-100 text-status-error-800',
};

const STATUS_STYLES: Record<ExtensionStatus, string> = {
  'UDM-derived pattern': 'bg-ui-clearwater-50 text-ui-clearwater-800',
  'Communications extension': 'bg-ui-gold-50 text-ui-gold-800',
  'Operational support': 'bg-status-muted-100 text-status-muted-800',
};

const GOVERNANCE_TABLES = catalog.tables as GovernanceTable[];

function getTableClassification(table: GovernanceTable): DataClassification {
  if (table.columns.some((column) => column.classification === 'Restricted')) return 'Restricted';
  if (table.columns.some((column) => column.classification === 'Confidential')) return 'Confidential';
  if (table.columns.some((column) => column.classification === 'Internal')) return 'Internal';
  return 'Public';
}

export default function DataGovernancePage() {
  const [search, setSearch] = useState('');
  const [classificationFilter, setClassificationFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [piiOnly, setPiiOnly] = useState(false);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set(['submissions']));

  const filteredTables = useMemo(() => {
    const term = search.trim().toLowerCase();
    return GOVERNANCE_TABLES.filter((table) => {
      if (statusFilter && table.status !== statusFilter) return false;

      const matchingColumns = table.columns.filter((column) => {
        if (classificationFilter && column.classification !== classificationFilter) return false;
        if (piiOnly && !column.pii) return false;
        if (!term) return true;
        return (
          column.name.toLowerCase().includes(term) ||
          column.description.toLowerCase().includes(term) ||
          (column.allowedValueGroup || '').toLowerCase().includes(term)
        );
      });

      if (matchingColumns.length > 0) return true;
      if (classificationFilter || piiOnly) return false;
      if (!term) return true;

      return (
        table.name.toLowerCase().includes(term) ||
        table.area.toLowerCase().includes(term) ||
        table.status.toLowerCase().includes(term) ||
        table.description.toLowerCase().includes(term)
      );
    });
  }, [classificationFilter, piiOnly, search, statusFilter]);

  const getFilteredColumns = (table: GovernanceTable) => {
    const term = search.trim().toLowerCase();
    return table.columns.filter((column) => {
      if (classificationFilter && column.classification !== classificationFilter) return false;
      if (piiOnly && !column.pii) return false;
      if (!term) return true;
      return (
        column.name.toLowerCase().includes(term) ||
        column.description.toLowerCase().includes(term) ||
        (column.allowedValueGroup || '').toLowerCase().includes(term)
      );
    });
  };

  const toggleTable = (name: string) => {
    setExpandedTables((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const expandAll = () => setExpandedTables(new Set(filteredTables.map((table) => table.name)));
  const collapseAll = () => setExpandedTables(new Set());

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Data Governance</h1>
      </header>

      <p className="text-sm text-gray-600">
        Catalog reviewed {catalog.reviewedAt}. Classifications are provisional pending Data Owner review.
        PII flags include incidental personal information in free text.
      </p>

      <section className="rounded-lg bg-white p-4 shadow">
        <div className="flex flex-wrap items-center gap-3">
          <input
            aria-label="Search governance catalog"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search tables, columns, allowed values, descriptions"
            className="min-w-64 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-clearwater-500 focus:outline-none focus:ring-2 focus:ring-ui-clearwater-100"
          />
          <select aria-label="UDM status"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-ui-clearwater-500 focus:outline-none focus:ring-2 focus:ring-ui-clearwater-100"
          >
            <option value="">All UDM statuses</option>
            <option value="UDM-derived pattern">UDM-derived pattern</option>
            <option value="Communications extension">Communications extension</option>
            <option value="Operational support">Operational support</option>
          </select>
          <select aria-label="Data classification"
            value={classificationFilter}
            onChange={(event) => setClassificationFilter(event.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-ui-clearwater-500 focus:outline-none focus:ring-2 focus:ring-ui-clearwater-100"
          >
            <option value="">All classifications</option>
            <option value="Public">Public</option>
            <option value="Internal">Internal</option>
            <option value="Confidential">Confidential</option>
            <option value="Restricted">Restricted</option>
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={piiOnly}
              onChange={(event) => setPiiOnly(event.target.checked)}
              className="rounded border-gray-300 text-ui-clearwater-600 focus:ring-ui-clearwater-500"
            />
            PII only
          </label>
          <div className="ml-auto flex gap-2">
            <button type="button" onClick={expandAll} className="text-xs font-medium text-ui-clearwater-700 hover:text-ui-clearwater-900">
              Expand all
            </button>
            <button type="button" onClick={collapseAll} className="text-xs font-medium text-gray-500 hover:text-gray-700">
              Collapse all
            </button>
          </div>
        </div>
      </section>

      <section className="space-y-2">
        {filteredTables.length === 0 ? (
          <div className="rounded-lg bg-white p-8 text-center text-sm text-gray-500 shadow">
            No governance entries match the current filters.
          </div>
        ) : (
          filteredTables.map((table) => {
            const tableClassification = getTableClassification(table);
            const filteredColumns = getFilteredColumns(table);
            const piiCount = table.columns.filter((column) => column.pii).length;
            const isExpanded = expandedTables.has(table.name);

            return (
              <div key={table.name} className="overflow-hidden rounded-lg bg-white shadow">
                <button
                  type="button"
                  onClick={() => toggleTable(table.name)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-gray-50"
                >
                  <span className={`text-sm text-gray-600 transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                    {'>'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-gray-900">{table.name}</span>
                      <span className="text-xs text-gray-600">{table.columns.length} columns</span>
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[table.status]}`}>
                        {table.status}
                      </span>
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${CLASSIFICATION_STYLES[tableClassification]}`}>
                        {tableClassification}
                      </span>
                      {piiCount > 0 && (
                        <span className="rounded bg-status-warning-100 px-2 py-0.5 text-xs font-medium text-status-warning-800">
                          {piiCount} PII
                        </span>
                      )}
                    </div>
                    <p className="mt-1 truncate text-sm text-gray-500">{table.description}</p>
                  </div>
                  <span className="hidden text-right text-xs text-gray-600 sm:block">{table.area}</span>
                </button>

                {isExpanded && (
                  <div className="border-t border-gray-100">
                    <p className="px-5 py-3 text-xs text-gray-500">
                      Steward: {table.steward} · Source: {table.sourceSystem} · Retention: {table.retentionCategory}
                    </p>
                    {filteredColumns.length === 0 ? (
                      <div className="px-5 py-4 text-sm text-gray-600">No columns match the current filters.</div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[760px]">
                          <thead>
                            <tr className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                              <th className="px-5 py-2 font-medium">Column</th>
                              <th className="px-3 py-2 font-medium">Description</th>
                              <th className="px-3 py-2 font-medium">Allowed Value</th>
                              <th className="px-3 py-2 text-center font-medium">PII</th>
                              <th className="px-3 py-2 font-medium">Classification</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {filteredColumns.map((column) => (
                              <tr key={column.name} className="hover:bg-gray-50/60">
                                <td className="px-5 py-3 align-top font-mono text-sm text-gray-800">{column.name}</td>
                                <td className="max-w-xl px-3 py-3 align-top text-sm text-gray-600">{column.description}</td>
                                <td className="px-3 py-3 align-top text-sm text-gray-500">
                                  {column.allowedValueGroup ? (
                                    <span className="rounded bg-gray-100 px-2 py-1 font-mono text-xs text-gray-700">
                                      {column.allowedValueGroup}
                                    </span>
                                  ) : (
                                    <span className="text-gray-300">-</span>
                                  )}
                                </td>
                                <td className="px-3 py-3 text-center align-top">
                                  {column.pii ? (
                                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-status-warning-100 text-xs font-bold text-status-warning-800">
                                      !
                                    </span>
                                  ) : (
                                    <span className="text-gray-300">-</span>
                                  )}
                                </td>
                                <td className="px-3 py-3 align-top">
                                  <span className={`rounded px-2 py-1 text-xs font-medium ${CLASSIFICATION_STYLES[column.classification]}`}>
                                    {column.classification}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </section>

      <p className="text-center text-xs text-gray-600">
        Showing {filteredTables.length} of {GOVERNANCE_TABLES.length} tables
      </p>
    </div>
  );
}
