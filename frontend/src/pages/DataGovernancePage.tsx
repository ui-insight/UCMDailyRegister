import { useMemo, useState } from 'react';

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

const VALUE_GROUPS = [
  'Submission_Category',
  'Newsletter_Type',
  'Target_Newsletter',
  'Submission_Status',
  'Newsletter_Status',
  'Version_Type',
  'Headline_Case',
  'Rule_Set',
  'Severity',
  'Schedule_Mode',
];

function col(
  name: string,
  description: string,
  classification: DataClassification = 'Internal',
  pii = false,
  allowedValueGroup?: string,
): GovernanceColumn {
  return { name, description, classification, pii, allowedValueGroup };
}

const GOVERNANCE_TABLES: GovernanceTable[] = [
  {
    name: 'allowed_values',
    area: 'Controlled vocabularies',
    status: 'UDM-derived pattern',
    steward: 'UCM operations',
    description: 'Central governed value list for categorical fields, adapted from OpenERA AllowedValues.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Value_Group', 'Vocabulary family used by API, forms, and settings.', 'Public'),
      col('Code', 'Machine-readable value within the group.', 'Public'),
      col('Label', 'Human-readable value shown in the user interface.', 'Public'),
      col('Display_Order', 'Sort order for menus and settings views.', 'Public'),
      col('Is_Active', 'Soft-disable flag for values that should no longer be selected.', 'Internal'),
      col('Visibility_Role', 'Public or staff visibility scope for submission categories.', 'Internal'),
      col('Description', 'Steward-facing explanation of the value.', 'Public'),
    ],
  },
  {
    name: 'submissions',
    area: 'Content intake',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Submitted newsletter or SLC event content with workflow, submitter, image, and routing metadata.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Category', 'Content category code.', 'Public', false, 'Submission_Category'),
      col('Target_Newsletter', 'Publication routing code: TDR, My UI, both, or SLC-only none.', 'Public', false, 'Target_Newsletter'),
      col('Original_Headline', 'Submitted headline text.', 'Public'),
      col('Original_Body', 'Submitted body text.', 'Public'),
      col('Submitter_Name', 'Submitter contact name.', 'Confidential', true),
      col('Submitter_Email', 'Submitter contact email.', 'Confidential', true),
      col('Submitter_Notes', 'Free-text instructions from submitter; may contain incidental PII.', 'Confidential', true),
      col('Assigned_Editor', 'Staff owner for editorial follow-up.', 'Internal', true),
      col('Editorial_Notes', 'Staff-only editorial notes; may contain incidental PII.', 'Internal', true),
      col('Has_Image', 'Whether an uploaded image is attached.', 'Public'),
      col('Image_Path', 'Server-side image path using UUID naming.', 'Internal'),
      col('Survey_End_Date', 'Optional survey close date used for survey handling.', 'Public'),
      col('Status', 'Editorial workflow state.', 'Internal', false, 'Submission_Status'),
      col('Show_In_SLC_Calendar', 'Whether the submission appears in the SLC calendar feed.', 'Internal'),
      col('Event_Classification', 'Strategic or signature event label for SLC visibility.', 'Internal'),
      col('Created_At', 'Server creation timestamp.', 'Internal'),
      col('Updated_At', 'Server update timestamp.', 'Internal'),
    ],
  },
  {
    name: 'submission_links',
    area: 'Content intake',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Normalized hyperlinks attached to submitted content.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Submission_Id', 'Foreign key to submissions.', 'Internal'),
      col('Url', 'Destination URL supplied with the submission.', 'Public'),
      col('Anchor_Text', 'Optional display text for the link.', 'Public'),
      col('Display_Order', 'Ordering of links inside the submission.', 'Public'),
    ],
  },
  {
    name: 'submission_schedule_requests',
    area: 'Content scheduling',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Requested run dates, recurrence settings, flexibility notes, and skipped occurrence dates.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Submission_Id', 'Foreign key to submissions.', 'Internal'),
      col('Requested_Date', 'Primary requested publication date.', 'Public'),
      col('Second_Requested_Date', 'Secondary requested date when an item targets both newsletters.', 'Public'),
      col('Repeat_Count', 'Legacy number of requested runs.', 'Internal'),
      col('Repeat_Note', 'Legacy free-text repeat instructions.', 'Confidential', true),
      col('Is_Flexible', 'Whether editors may choose an alternate date.', 'Internal'),
      col('Flexible_Deadline', 'Latest acceptable date or flexibility note.', 'Confidential', true),
      col('Recurrence_Type', 'Recurrence rule type for repeated runs.', 'Internal'),
      col('Recurrence_Interval', 'Interval for recurring requests.', 'Internal'),
      col('Recurrence_End_Date', 'End date for recurrence expansion.', 'Internal'),
      col('Excluded_Dates', 'JSON list of skipped or rescheduled occurrence dates.', 'Internal'),
    ],
  },
  {
    name: 'edit_versions',
    area: 'Editorial history',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Append-only snapshots of original, AI-suggested, and editor-final copy.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Submission_Id', 'Foreign key to submissions.', 'Internal'),
      col('Version_Type', 'Editing stage represented by the snapshot.', 'Internal', false, 'Version_Type'),
      col('Headline', 'Headline text at this version.', 'Public'),
      col('Body', 'Body text at this version.', 'Public'),
      col('Headline_Case', 'Headline casing policy applied to this version.', 'Internal', false, 'Headline_Case'),
      col('Flags', 'JSON list of AI or rule findings.', 'Internal'),
      col('Changes_Made', 'JSON list of generated or editor-facing change summaries.', 'Internal'),
      col('AI_Provider', 'LLM provider used for AI-generated versions.', 'Internal'),
      col('AI_Model', 'LLM model used for AI-generated versions.', 'Internal'),
      col('Editor_Instructions', 'Free-text editor instructions passed into an edit run.', 'Internal'),
      col('Created_At', 'Immutable version creation timestamp.', 'Internal'),
    ],
  },
  {
    name: 'newsletters',
    area: 'Newsletter assembly',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Dated editions of The Daily Register or My UI.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Type', 'Publication code.', 'Public', false, 'Newsletter_Type'),
      col('Publish_Date', 'Issue date.', 'Public'),
      col('Status', 'Issue lifecycle state.', 'Internal', false, 'Newsletter_Status'),
      col('Created_At', 'Server creation timestamp.', 'Internal'),
      col('Updated_At', 'Server update timestamp.', 'Internal'),
    ],
  },
  {
    name: 'newsletter_items',
    area: 'Newsletter assembly',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Placement of a finalized submission into a newsletter issue and section.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Id', 'Foreign key to newsletters.', 'Internal'),
      col('Submission_Id', 'Foreign key to submissions.', 'Internal'),
      col('Section_Id', 'Foreign key to newsletter_sections.', 'Internal'),
      col('Position', 'Ordering within the section.', 'Public'),
      col('Final_Headline', 'Final published headline.', 'Public'),
      col('Final_Body', 'Final published body.', 'Public'),
      col('Run_Number', 'Occurrence number for repeated publication.', 'Internal'),
    ],
  },
  {
    name: 'newsletter_external_items',
    area: 'Newsletter assembly',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Placement of imported calendar, job, or other external content into a newsletter issue.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Id', 'Foreign key to newsletters.', 'Internal'),
      col('Section_Id', 'Foreign key to newsletter_sections.', 'Internal'),
      col('Source_Type', 'External source category, such as calendar_event or job_posting.', 'Public'),
      col('Source_Id', 'Source-system identifier.', 'Internal'),
      col('Source_Url', 'Source-system URL.', 'Public'),
      col('Event_Start', 'Event start timestamp where applicable.', 'Public'),
      col('Event_End', 'Event end timestamp where applicable.', 'Public'),
      col('Location', 'Event location where applicable.', 'Public'),
      col('Position', 'Ordering within the section.', 'Public'),
      col('Final_Headline', 'Final published headline.', 'Public'),
      col('Final_Body', 'Final published body.', 'Public'),
    ],
  },
  {
    name: 'newsletter_sections',
    area: 'Newsletter assembly',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Governed section taxonomy and layout requirements for each newsletter type.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Type', 'Publication code.', 'Public', false, 'Newsletter_Type'),
      col('Name', 'Human-readable section name.', 'Public'),
      col('Slug', 'Machine-readable section identifier.', 'Public'),
      col('Display_Order', 'Default section order.', 'Public'),
      col('Description', 'Section purpose.', 'Public'),
      col('Requires_Image', 'Whether items in the section need an image.', 'Internal'),
      col('Image_Dimensions', 'Expected image dimensions.', 'Internal'),
      col('Is_Active', 'Soft-retirement flag.', 'Internal'),
    ],
  },
  {
    name: 'recurring_messages',
    area: 'Recurring editorial content',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Staff-managed reusable copy surfaced on a configured cadence.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Type', 'Publication code.', 'Public', false, 'Newsletter_Type'),
      col('Section_Id', 'Foreign key to newsletter_sections.', 'Internal'),
      col('Headline', 'Reusable message headline.', 'Public'),
      col('Body', 'Reusable message body.', 'Public'),
      col('Start_Date', 'First eligible publish date.', 'Internal'),
      col('Recurrence_Type', 'Recurrence rule type.', 'Internal'),
      col('Recurrence_Interval', 'Interval for recurring messages.', 'Internal'),
      col('End_Date', 'Optional final eligible date.', 'Internal'),
      col('Excluded_Dates', 'JSON list of skipped dates.', 'Internal'),
      col('Is_Active', 'Soft-disable flag.', 'Internal'),
      col('Created_At', 'Server creation timestamp.', 'Internal'),
      col('Updated_At', 'Server update timestamp.', 'Internal'),
    ],
  },
  {
    name: 'recurring_message_issue_overrides',
    area: 'Recurring editorial content',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Issue-specific exceptions, currently used to preserve skipped recurring messages.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Recurring_Message_Id', 'Foreign key to recurring_messages.', 'Internal'),
      col('Newsletter_Id', 'Foreign key to newsletters.', 'Internal'),
      col('Override_Action', 'Issue-level action, currently skip.', 'Internal'),
      col('Created_At', 'Server creation timestamp.', 'Internal'),
    ],
  },
  {
    name: 'style_rules',
    area: 'AI editorial policy',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Database-managed style rules injected into the AI editing system prompt.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Rule_Set', 'Shared, TDR, or My UI rule scope.', 'Internal', false, 'Rule_Set'),
      col('Category', 'Editorial rule category.', 'Internal'),
      col('Rule_Key', 'Machine-readable rule key.', 'Internal'),
      col('Rule_Text', 'Natural-language editing instruction.', 'Internal'),
      col('Is_Active', 'Whether future AI edits should use the rule.', 'Internal'),
      col('Severity', 'Rule severity for editor attention.', 'Internal', false, 'Severity'),
    ],
  },
  {
    name: 'schedule_configs',
    area: 'Publication schedule',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Publication cadence and submission deadline rules by newsletter type and schedule mode.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Type', 'Publication code.', 'Public', false, 'Newsletter_Type'),
      col('Mode', 'Academic year, summer, or winter break schedule mode.', 'Internal', false, 'Schedule_Mode'),
      col('Submission_Deadline_Description', 'Human-readable deadline rule.', 'Public'),
      col('Deadline_Day_Of_Week', 'Deadline weekday used in calculations.', 'Internal'),
      col('Deadline_Time', 'Deadline time used in calculations.', 'Internal'),
      col('Publish_Day_Of_Week', 'Publish weekday where applicable.', 'Internal'),
      col('Is_Daily', 'Whether the mode publishes every weekday.', 'Internal'),
      col('Active_Start_Month', 'Month when this mode starts.', 'Internal'),
      col('Active_End_Month', 'Month when this mode ends.', 'Internal'),
      col('Holiday_Shift_Enabled', 'Whether holiday-aware shifting applies.', 'Internal'),
    ],
  },
  {
    name: 'blackout_dates',
    area: 'Publication schedule',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Dates when one or all newsletters should not publish.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Blackout_Date', 'Suppressed publication date.', 'Public'),
      col('Newsletter_Type', 'Optional publication scope; null applies broadly.', 'Public', false, 'Newsletter_Type'),
      col('Description', 'Reason for the blackout.', 'Public'),
      col('Is_Active', 'Soft-disable flag.', 'Internal'),
    ],
  },
  {
    name: 'schedule_mode_overrides',
    area: 'Publication schedule',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Manual date-range override that forces a newsletter into a configured schedule mode.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Type', 'Publication code.', 'Public', false, 'Newsletter_Type'),
      col('Override_Mode', 'Schedule mode to apply during the range.', 'Internal', false, 'Schedule_Mode'),
      col('Start_Date', 'Inclusive override start date.', 'Internal'),
      col('End_Date', 'Inclusive override end date.', 'Internal'),
      col('Description', 'Reason for the override.', 'Internal'),
      col('Created_At', 'Server creation timestamp.', 'Internal'),
    ],
  },
  {
    name: 'custom_publish_dates',
    area: 'Publication schedule',
    status: 'Communications extension',
    steward: 'UCM editorial staff',
    description: 'Ad hoc publish dates used during winter break or other non-standard schedules.',
    columns: [
      col('Id', 'UUID primary key.', 'Internal'),
      col('Newsletter_Type', 'Publication code.', 'Public', false, 'Newsletter_Type'),
      col('Publish_Date', 'Manual issue date.', 'Public'),
      col('Description', 'Reason for the custom publish date.', 'Internal'),
      col('Created_At', 'Server creation timestamp.', 'Internal'),
    ],
  },
];

const GOVERNANCE_GAPS = [
  'No OpenERA-style DataDictionary table or read API exists yet; this tab is a static app catalog.',
  'No automated drift check compares ORM metadata, docs, seed vocabularies, and the catalog.',
  'The portfolio data-governance registry still needs to be refreshed for the full UCM schema.',
  'SLC-only submission values are implemented in code but need first-class vocabulary governance.',
];

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

  const columns = useMemo(
    () => GOVERNANCE_TABLES.flatMap((table) => table.columns.map((column) => ({ table, column }))),
    [],
  );

  const stats = useMemo(() => {
    const classificationBreakdown = columns.reduce<Record<DataClassification, number>>(
      (acc, { column }) => {
        acc[column.classification] += 1;
        return acc;
      },
      { Public: 0, Internal: 0, Confidential: 0, Restricted: 0 },
    );

    const statusBreakdown = GOVERNANCE_TABLES.reduce<Record<ExtensionStatus, number>>(
      (acc, table) => {
        acc[table.status] += 1;
        return acc;
      },
      {
        'UDM-derived pattern': 0,
        'Communications extension': 0,
        'Operational support': 0,
      },
    );

    return {
      tableCount: GOVERNANCE_TABLES.length,
      columnCount: columns.length,
      piiCount: columns.filter(({ column }) => column.pii).length,
      classificationBreakdown,
      statusBreakdown,
    };
  }, [columns]);

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
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Governance</h1>
          <p className="mt-1 max-w-3xl text-sm text-gray-600">
            UCM extends the OpenERA UDM pattern into newsletter production: one UDM-derived vocabulary table, fifteen communications-domain tables, and a documented gap to full DataDictionary parity.
          </p>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Tables" value={stats.tableCount} tone="clearwater" />
        <StatCard label="Columns" value={stats.columnCount} tone="neutral" />
        <StatCard label="PII Fields" value={stats.piiCount} tone="gold" />
        <StatCard label="Value Groups" value={VALUE_GROUPS.length} tone="info" />
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="rounded-lg bg-white p-4 shadow">
          <h2 className="text-sm font-semibold text-gray-900">UDM Extension Map</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            {Object.entries(stats.statusBreakdown).map(([status, count]) => (
              <div key={status} className="rounded-md border border-gray-200 p-3">
                <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status as ExtensionStatus]}`}>
                  {status}
                </span>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{count}</p>
                <p className="text-xs text-gray-500">tables</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(stats.classificationBreakdown).map(([classification, count]) => (
              <span
                key={classification}
                className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium ${CLASSIFICATION_STYLES[classification as DataClassification]}`}
              >
                {classification}
                <span className="font-semibold">{count}</span>
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-lg bg-white p-4 shadow">
          <h2 className="text-sm font-semibold text-gray-900">Documentation Status</h2>
          <p className="mt-2 text-sm text-gray-600">
            The repo now has a human-readable UDM alignment report and this interactive catalog. It is still short of OpenERA governance parity.
          </p>
          <ul className="mt-3 space-y-2 text-xs text-gray-600">
            {GOVERNANCE_GAPS.map((gap) => (
              <li key={gap} className="rounded-md bg-gray-50 px-3 py-2">{gap}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="rounded-lg bg-white p-4 shadow">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search tables, columns, allowed values, descriptions"
            className="min-w-64 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-clearwater-500 focus:outline-none focus:ring-2 focus:ring-ui-clearwater-100"
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-ui-clearwater-500 focus:outline-none focus:ring-2 focus:ring-ui-clearwater-100"
          >
            <option value="">All UDM statuses</option>
            <option value="UDM-derived pattern">UDM-derived pattern</option>
            <option value="Communications extension">Communications extension</option>
            <option value="Operational support">Operational support</option>
          </select>
          <select
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
                  <span className={`text-sm text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                    {'>'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-gray-900">{table.name}</span>
                      <span className="text-xs text-gray-400">{table.columns.length} columns</span>
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
                  <span className="hidden text-right text-xs text-gray-400 sm:block">{table.area}</span>
                </button>

                {isExpanded && (
                  <div className="border-t border-gray-100">
                    {filteredColumns.length === 0 ? (
                      <div className="px-5 py-4 text-sm text-gray-400">No columns match the current filters.</div>
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

      <p className="text-center text-xs text-gray-400">
        Showing {filteredTables.length} of {GOVERNANCE_TABLES.length} tables
      </p>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: 'clearwater' | 'neutral' | 'gold' | 'info';
}) {
  const styles = {
    clearwater: 'border-ui-clearwater-100 bg-ui-clearwater-50 text-ui-clearwater-800',
    neutral: 'border-gray-200 bg-white text-gray-800',
    gold: 'border-ui-gold-100 bg-ui-gold-50 text-ui-gold-800',
    info: 'border-status-info-100 bg-status-info-100 text-status-info-800',
  };

  return (
    <div className={`rounded-lg border p-4 shadow-sm ${styles[tone]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="mt-1 text-xs font-medium">{label}</div>
    </div>
  );
}
