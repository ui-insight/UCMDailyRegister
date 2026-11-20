# Data dictionary

Generated from `frontend/src/data/governance-catalog.json`; used by the staff governance page.
Update reviewed metadata in that file, then run `python scripts/check_governance.py --write`.

Catalog review: 2026-10-24; **provisional; owner classification approval pending**.

Labels describe default handling, not institutional classification approval. PII flags include
incidental personal information risk; published release decisions apply to individual content.
Retention categories are defined in [Retention and disposal](retention.md).

**APM 30.11 tiers are proposed — Data Owner to confirm** ([#176](https://github.com/ui-insight/UCMDailyRegister/issues/176)).
The project team proposed these University of Idaho APM 30.11 tiers; they are not institutional classification until the Data Owner approves them (issue #176). A table takes the highest tier of any of its columns.
Handling is the app's local label; APM 30.11 is the proposed University tier. See
[APM 30.11 classification (proposed)](../data-governance.md#apm-3011-classification-proposed).

| APM 30.11 tier (proposed) | Tables | Columns |
| --- | ---: | ---: |
| Low | 10 | 194 |
| Moderate | 11 | 30 |
| High | 0 | 0 |

## `ai_edit_tasks`

Durable staff-only AI edit requests, bounded execution state, restart interruption and committed response copies; source-level retention applies.

Steward role: UCM editorial staff / technical operations. Source: staff / AI editing pipeline.
Retention category: `submission_source`. Extension: Operational support.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | Durable task UUID returned as Task_Id by the staff API. | Internal | Low | No | — |
| `Submission_Id` | Parent source submission; task copies are deleted with the source. | Internal | Low | No | — |
| `Newsletter_Type` | Publication context for this AI request. | Internal | Low | No | Newsletter_Type |
| `Editor_Instructions` | Staff-provided instructions, potentially containing unpublished copy or incidental personal data. | Confidential | Moderate | Yes | — |
| `Status` | Code-validated queued, running, succeeded or failed task state. | Internal | Low | No | — |
| `Source_Fingerprint` | SHA-256 fingerprint of source copy, category, target, notes and links for stale-result checks. | Internal | Low | No | — |
| `Active_Key` | Nullable unique submission/newsletter key preventing duplicate pending work. | Internal | Low | No | — |
| `Run_Id` | Worker attempt UUID used to prevent late invalidated attempts from saving. | Internal | Low | No | — |
| `Result_JSON` | Committed AI edit response including copy, links, flags, diffs and provenance; may repeat personal data. | Confidential | Moderate | Yes | — |
| `Error_Message` | Controlled application failure/retry message; external exception details are excluded. | Internal | Low | No | — |
| `Created_At` | Request acceptance timestamp in UTC. | Internal | Low | No | — |
| `Updated_At` | Latest task transition timestamp in UTC. | Internal | Low | No | — |

## `allowed_values`

Central governed value list for categorical fields, adapted from OpenERA AllowedValues.

Steward role: UCM operations. Source: staff / system.
Retention category: `configuration`. Extension: UDM-derived pattern.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Value_Group` | Vocabulary family used by API, forms, and settings. | Public | Low | No | — |
| `Code` | Machine-readable value within the group. | Public | Low | No | — |
| `Label` | Human-readable value shown in the user interface. | Public | Low | No | — |
| `Display_Order` | Sort order for menus and settings views. | Public | Low | No | — |
| `Is_Active` | Soft-disable flag for values that should no longer be selected. | Internal | Low | No | — |
| `Visibility_Role` | Public or staff visibility scope for submission categories. | Internal | Low | No | — |
| `Description` | Steward-facing explanation of the value. | Public | Low | No | — |

## `audit_events`

Append-only per-user trail of privileged-role API reads and exports, all writes and deletions, 401/403 refusals and sign-in outcomes. Holds no content, query strings, IP addresses or user agents; no update/delete API and no disposal job.

Steward role: Security and operations owner / UCM Data Owner. Source: API middleware / SSO callback.
Retention category: `security_audit`. Extension: Operational support.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | Audit event UUID. | Internal | Low | No | — |
| `Occurred_At` | UTC time the request completed or the sign-in finished. | Internal | Low | No | — |
| `Actor_Ref` | Microsoft Entra object ID (oid) of the signed-in account; null in header mode, for anonymous callers and for sessions minted before the claim existed. Authorized Entra administrators can resolve it to a person, so it is handled as a personal identifier. | Confidential | Moderate | Yes | — |
| `Actor_Role` | Role resolved for the caller: staff, slc, ops, submitter or public. | Internal | Low | No | — |
| `Event_Type` | Code-validated event: record_read, record_export, record_change, record_delete, authorization_failure, sign_in_success or sign_in_failure. | Internal | Low | No | — |
| `Reason_Code` | Fixed reason for a refusal (unauthenticated, forbidden) or failed sign-in (sign_in_failed, no_account, misconfigured, unavailable). | Internal | Low | No | — |
| `Http_Method` | HTTP method of the audited request. | Internal | Low | No | — |
| `Route_Template` | Declared API route template, never the raw URL or query string. | Internal | Low | No | — |
| `Record_Ids` | Path-parameter values shaped like record IDs (UUIDs or integers), keyed by parameter name; other path text is dropped. | Internal | Low | No | — |
| `Changed_Fields` | Top-level JSON body key names of a write that the route's request schema declares; unknown keys and all values are dropped. | Internal | Low | No | — |
| `Status_Code` | HTTP response status; null for sign-in events. | Internal | Low | No | — |

## `blackout_dates`

Dates when one or all newsletters should not publish.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Blackout_Date` | Suppressed publication date. | Public | Low | No | — |
| `Newsletter_Type` | Optional publication scope; null applies broadly. | Public | Low | No | Newsletter_Type |
| `Description` | Reason for the blackout. | Public | Low | No | — |
| `Is_Active` | Soft-disable flag. | Internal | Low | No | — |

## `custom_publish_dates`

Ad hoc publish dates used during winter break or other non-standard schedules.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Type` | Publication code. | Public | Low | No | Newsletter_Type |
| `Publish_Date` | Manual issue date. | Public | Low | No | — |
| `Description` | Reason for the custom publish date. | Internal | Moderate | Yes | — |
| `Created_At` | Server creation timestamp. | Internal | Low | No | — |

## `edit_versions`

Append-only snapshots of original, AI-suggested, and editor-final copy.

Steward role: UCM editorial staff. Source: AI / staff.
Retention category: `submission_source`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | Low | No | — |
| `Version_Type` | Editing stage represented by the snapshot. | Internal | Low | No | Version_Type |
| `Headline` | Headline text at this version. | Internal | Moderate | Yes | — |
| `Body` | Body text at this version. | Internal | Moderate | Yes | — |
| `Headline_Case` | Headline casing policy applied to this version. | Internal | Low | No | Headline_Case |
| `Flags` | JSON list of AI or rule findings. | Internal | Moderate | Yes | — |
| `Changes_Made` | JSON list of generated or editor-facing change summaries. | Internal | Moderate | Yes | — |
| `AI_Provider` | LLM provider used for AI-generated versions. | Internal | Low | No | — |
| `AI_Model` | LLM model used for AI-generated versions. | Internal | Low | No | — |
| `Policy_Fingerprint` | Editorial policy version and hash of the active style rules behind an AI-generated version. | Internal | Low | No | — |
| `Editor_Instructions` | Free-text editor instructions passed into an edit run. | Confidential | Moderate | Yes | — |
| `Created_At` | Immutable version creation timestamp. | Internal | Low | No | — |

## `harvested_events`

External calendar occurrences with independent SLC and ops review lenses.

Steward role: UCM and Event Services. Source: Trumba / staff.
Retention category: `external_working`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Source_Type` | External feed source family. | Internal | Low | No | — |
| `Source_Id` | External event-occurrence identifier. | Internal | Low | No | — |
| `Series_Id` | External repeating-series identifier. | Internal | Low | No | — |
| `Source_Url` | External source link; may include query parameters. | Internal | Low | Yes | — |
| `Title` | Upstream public event title; can name people. | Internal | Low | Yes | — |
| `Description` | Upstream event details; can include personal contact information. | Internal | Low | Yes | — |
| `Location` | Upstream event venue or location. | Internal | Low | No | — |
| `Event_Start` | Event start timestamp. | Internal | Low | No | — |
| `Event_End` | Optional event end timestamp. | Internal | Low | No | — |
| `All_Day` | All-day occurrence indicator. | Internal | Low | No | — |
| `Category_Path` | Upstream category hierarchy. | Internal | Low | No | — |
| `Is_Canceled` | Upstream cancellation marker. | Internal | Low | No | — |
| `Content_Hash` | Hash of source content used to detect upstream changes. | Internal | Low | No | — |
| `SLC_Review_Status` | Independent SLC triage state. | Internal | Low | No | SLC_Review_Status |
| `Ops_Review_Status` | Independent Event Services triage state. | Internal | Low | No | Ops_Review_Status |
| `Ops_Assessed_Content_Hash` | Content hash used for current ops assessment. | Internal | Low | No | — |
| `Upstream_Changed_At` | Time source changed after SLC flagging; cleared by SLC acknowledgment. | Internal | Low | No | — |
| `Ops_Upstream_Changed_At` | Time source changed after ops review; cleared independently by ops. | Internal | Low | No | — |
| `Promoted_Submission_Id` | SLC-only submission created by promotion; cleared if submission is deleted. | Internal | Low | No | — |
| `First_Seen_At` | First harvest timestamp. | Internal | Low | No | — |
| `Last_Seen_At` | Most recent observation timestamp. | Internal | Low | No | — |

## `newsletter_external_items`

Placement of imported calendar, job, or other external content into a newsletter issue.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `publication_archive`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Id` | Foreign key to newsletters. | Internal | Low | No | — |
| `Section_Id` | Foreign key to newsletter_sections. | Internal | Low | No | — |
| `Source_Type` | External source category, such as calendar_event or job_posting. | Public | Low | No | — |
| `Source_Id` | Source-system identifier. | Internal | Low | No | — |
| `Source_Url` | Source-system URL. | Public | Low | Yes | — |
| `Event_Start` | Event start timestamp where applicable. | Public | Low | No | — |
| `Event_End` | Event end timestamp where applicable. | Public | Low | No | — |
| `Location` | Event location where applicable. | Public | Low | No | — |
| `Position` | Ordering within the section. | Public | Low | No | — |
| `Final_Headline` | Final published headline. | Internal | Low | Yes | — |
| `Final_Body` | Final published body. | Internal | Low | Yes | — |

## `newsletter_items`

Placement of a finalized submission into a newsletter issue and section.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `publication_archive`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Id` | Foreign key to newsletters. | Internal | Low | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | Low | No | — |
| `Section_Id` | Foreign key to newsletter_sections. | Internal | Low | No | — |
| `Position` | Ordering within the section. | Public | Low | No | — |
| `Final_Headline` | Final published headline. | Internal | Low | Yes | — |
| `Final_Body` | Final published body. | Internal | Low | Yes | — |
| `Run_Number` | Occurrence number for repeated publication. | Internal | Low | No | — |
| `Manually_Placed` | Staff changed section placement; automatic reassembly preserves it. | Internal | Low | No | — |
| `Source_Version_Id` | Edit-version reference from which issue copy was assembled. | Internal | Low | No | — |
| `Edition_Edited` | Staff changed issue copy; reassembly preserves the edition override. | Internal | Low | No | — |
| `Upstream_Reviewed_Version_Id` | Approved revision reviewed and intentionally not applied to this issue. | Internal | Low | No | — |

## `newsletter_sections`

Governed section taxonomy and layout requirements for each newsletter type.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Type` | Publication code. | Public | Low | No | Newsletter_Type |
| `Name` | Human-readable section name. | Public | Low | No | — |
| `Slug` | Machine-readable section identifier. | Public | Low | No | — |
| `Display_Order` | Default section order. | Public | Low | No | — |
| `Description` | Section purpose. | Public | Low | No | — |
| `Requires_Image` | Whether items in the section need an image. | Internal | Low | No | — |
| `Image_Dimensions` | Expected image dimensions. | Internal | Low | No | — |
| `Is_Active` | Soft-retirement flag. | Internal | Low | No | — |

## `newsletters`

Dated editions of The Daily Register or My UI.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `publication_archive`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Type` | Publication code. | Public | Low | No | Newsletter_Type |
| `Publish_Date` | Issue date. | Public | Low | No | — |
| `Status` | Issue lifecycle state. | Internal | Low | No | Newsletter_Status |
| `Created_At` | Server creation timestamp. | Internal | Low | No | — |
| `Updated_At` | Server update timestamp. | Internal | Low | No | — |

## `ops_need_assessments`

AI-suggested needs and staff verdicts for a harvested event.

Steward role: Event Services. Source: AI / staff.
Retention category: `external_working`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Harvested_Event_Id` | Parent harvested event reference; assessment cascades on event deletion. | Internal | Low | No | — |
| `Need` | Operational service code. | Internal | Low | No | Ops_Need_Type |
| `Confidence` | AI confidence code; null for staff-added needs. | Internal | Low | No | Ops_Need_Confidence |
| `Rationale` | Model or staff explanation; can quote source content and contain personal information. | Internal | Moderate | Yes | — |
| `Verdict` | Staff judgment of the suggested need. | Internal | Low | No | Ops_Need_Verdict |
| `Source` | AI or staff origin of the assessment. | Internal | Low | No | Ops_Need_Source |
| `Created_At` | Record creation timestamp. | Internal | Low | No | — |

## `product_feedback`

User reports and diagnostic context; only staff review the queue.

Steward role: UCM product support. Source: user / browser.
Retention category: `feedback`. Extension: Operational support.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Feedback_Type` | Reported bug or product idea. | Internal | Low | No | — |
| `Summary` | User-entered short report summary; can contain incidental personal information. | Confidential | Moderate | Yes | — |
| `Details` | User-entered report text; can contain incidental sensitive information. | Confidential | Moderate | Yes | — |
| `Contact_Email` | Optional reporter email for follow-up. | Confidential | Moderate | Yes | — |
| `Submitter_Role` | Client-reported UI role; not an authenticated actor identity. | Internal | Low | No | — |
| `Route` | Reported page route; free text from client, potentially identifying. | Internal | Moderate | Yes | — |
| `App_Environment` | Client-reported deployment label. | Internal | Low | No | — |
| `Host` | Client-reported host; operational context. | Internal | Low | Yes | — |
| `Browser` | Client-reported user agent. | Internal | Moderate | Yes | — |
| `Viewport` | Reported viewport dimensions. | Internal | Low | No | — |
| `Status` | Product-feedback workflow status. | Internal | Low | No | — |
| `GitHub_URL` | Optional engineering issue reference; review sharing permissions. | Internal | Low | Yes | — |
| `GitHub_Export_Reviewed_At` | UTC time a staff-confirmed edited export was prepared; not proof an issue was posted. | Internal | Low | No | — |
| `GitHub_Export_SHA256` | Fingerprint of the exact reviewed export artifact; report originals remain unchanged. | Internal | Low | No | — |
| `Notification_Status` | Pending, disabled, failed or sent delivery state. | Internal | Low | No | — |
| `Notification_Attempts` | Number of attempted notification deliveries. | Internal | Low | No | — |
| `Notification_Sent_At` | Latest successful delivery time, if any. | Internal | Low | No | — |
| `Notification_Last_Error` | Exception class for latest delivery failure; older releases could store arbitrary error text. | Confidential | Moderate | Yes | — |
| `Created_At` | Record creation timestamp. | Internal | Low | No | — |
| `Updated_At` | Most recent record update timestamp. | Internal | Low | No | — |

## `recurring_message_issue_overrides`

Issue-specific exceptions, currently used to preserve skipped recurring messages.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Recurring_Message_Id` | Foreign key to recurring_messages. | Internal | Low | No | — |
| `Newsletter_Id` | Foreign key to newsletters. | Internal | Low | No | — |
| `Override_Action` | Issue-level action, currently skip. | Internal | Low | No | — |
| `Created_At` | Server creation timestamp. | Internal | Low | No | — |

## `recurring_messages`

Staff-managed reusable copy surfaced on a configured cadence.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Type` | Publication code. | Public | Low | No | Newsletter_Type |
| `Section_Id` | Foreign key to newsletter_sections. | Internal | Low | No | — |
| `Headline` | Reusable message headline. | Internal | Moderate | Yes | — |
| `Body` | Reusable message body. | Internal | Moderate | Yes | — |
| `Start_Date` | First eligible publish date. | Internal | Low | No | — |
| `Recurrence_Type` | Recurrence rule type. | Internal | Low | No | — |
| `Recurrence_Interval` | Interval for recurring messages. | Internal | Low | No | — |
| `End_Date` | Optional final eligible date. | Internal | Low | No | — |
| `Excluded_Dates` | JSON list of skipped dates. | Internal | Low | No | — |
| `Is_Active` | Soft-disable flag. | Internal | Low | No | — |
| `Created_At` | Server creation timestamp. | Internal | Low | No | — |
| `Updated_At` | Server update timestamp. | Internal | Low | No | — |

## `schedule_configs`

Publication cadence and submission deadline rules by newsletter type and schedule mode.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Type` | Publication code. | Public | Low | No | Newsletter_Type |
| `Mode` | Academic year, summer, or winter break schedule mode. | Internal | Low | No | Schedule_Mode |
| `Submission_Deadline_Description` | Human-readable deadline rule. | Public | Low | No | — |
| `Deadline_Day_Of_Week` | Deadline weekday used in calculations. | Internal | Low | No | — |
| `Deadline_Time` | Deadline time used in calculations. | Internal | Low | No | — |
| `Publish_Day_Of_Week` | Publish weekday where applicable. | Internal | Low | No | — |
| `Is_Daily` | Whether the mode publishes every weekday. | Internal | Low | No | — |
| `Active_Start_Month` | Month when this mode starts. | Internal | Low | No | — |
| `Active_End_Month` | Month when this mode ends. | Internal | Low | No | — |
| `Holiday_Shift_Enabled` | Whether holiday-aware shifting applies. | Internal | Low | No | — |

## `schedule_mode_overrides`

Manual date-range override that forces a newsletter into a configured schedule mode.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Newsletter_Type` | Publication code. | Public | Low | No | Newsletter_Type |
| `Override_Mode` | Schedule mode to apply during the range. | Internal | Low | No | Schedule_Mode |
| `Start_Date` | Inclusive override start date. | Internal | Low | No | — |
| `End_Date` | Inclusive override end date. | Internal | Low | No | — |
| `Description` | Reason for the override. | Internal | Moderate | Yes | — |
| `Created_At` | Server creation timestamp. | Internal | Low | No | — |

## `style_rules`

Database-managed style rules injected into the AI editing system prompt.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.
APM 30.11 table tier: **Low** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Rule_Set` | Shared, TDR, or My UI rule scope. | Internal | Low | No | Rule_Set |
| `Category` | Editorial rule category. | Internal | Low | No | — |
| `Rule_Key` | Machine-readable rule key. | Internal | Low | No | — |
| `Rule_Text` | Natural-language editing instruction. | Internal | Low | Yes | — |
| `Is_Active` | Whether future AI edits should use the rule. | Internal | Low | No | — |
| `Severity` | Rule severity for editor attention. | Internal | Low | No | Severity |

## `submission_links`

Normalized hyperlinks attached to submitted content.

Steward role: UCM editorial staff. Source: submitter / staff.
Retention category: `submission_source`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | Low | No | — |
| `Url` | Destination URL supplied with the submission. | Internal | Moderate | Yes | — |
| `Anchor_Text` | Optional display text for the link. | Internal | Moderate | Yes | — |
| `Display_Order` | Ordering of links inside the submission. | Public | Low | No | — |

## `submission_schedule_requests`

Requested run dates, recurrence settings, flexibility notes, and skipped occurrence dates.

Steward role: UCM editorial staff. Source: submitter / staff.
Retention category: `submission_source`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | Low | No | — |
| `Requested_Date` | Primary requested publication date. | Public | Low | No | — |
| `Second_Requested_Date` | Secondary requested date when an item targets both newsletters. | Public | Low | No | — |
| `Repeat_Count` | Legacy number of requested runs. | Internal | Low | No | — |
| `Repeat_Note` | Legacy free-text repeat instructions. | Confidential | Moderate | Yes | — |
| `Is_Flexible` | Whether editors may choose an alternate date. | Internal | Low | No | — |
| `Flexible_Deadline` | Optional text describing the latest flexible publication deadline. | Confidential | Moderate | Yes | — |
| `Recurrence_Type` | Recurrence rule type for repeated runs. | Internal | Low | No | — |
| `Recurrence_Interval` | Interval for recurring requests. | Internal | Low | No | — |
| `Recurrence_End_Date` | End date for recurrence expansion. | Internal | Low | No | — |
| `Repeats_Indefinitely` | Staff-only choice that a weekly or monthly schedule repeats with no end date; false keeps older open-ended rows running once. | Internal | Low | No | — |
| `Excluded_Dates` | JSON list of skipped or rescheduled occurrence dates. | Internal | Low | No | — |

## `submissions`

Submitted newsletter or SLC event content with workflow, submitter, image, and routing metadata.

Steward role: UCM editorial staff. Source: submitter / staff.
Retention category: `submission_source`. Extension: Communications extension.
APM 30.11 table tier: **Moderate** (proposed — Data Owner to confirm; highest column tier).

| Column | Meaning | Handling | APM 30.11 (proposed) | PII risk | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | Low | No | — |
| `Category` | Content category code. | Public | Low | No | Submission_Category |
| `Target_Newsletter` | Publication routing code: TDR, My UI, both, or SLC-only none. | Public | Low | No | Target_Newsletter |
| `Original_Headline` | Submitted headline text. | Internal | Moderate | Yes | — |
| `Original_Body` | Submitted body text. | Internal | Moderate | Yes | — |
| `Submitter_Name` | Submitter contact name. | Confidential | Moderate | Yes | — |
| `Submitter_Email` | Submitter contact email. | Confidential | Moderate | Yes | — |
| `Submitter_Notes` | Free-text instructions from submitter; may contain incidental PII. | Confidential | Moderate | Yes | — |
| `Assigned_Editor` | Staff owner for editorial follow-up. | Internal | Moderate | Yes | — |
| `Editorial_Notes` | Staff-only editorial notes; may contain incidental PII. | Confidential | Moderate | Yes | — |
| `Has_Image` | Whether an uploaded image is attached. | Public | Low | No | — |
| `Image_Path` | Server-side image path using UUID naming. | Internal | Low | No | — |
| `Survey_End_Date` | Optional survey close date used for survey handling. | Public | Low | No | — |
| `Status` | Editorial workflow state. | Internal | Low | No | Submission_Status |
| `Show_In_SLC_Calendar` | Whether the submission appears in the SLC calendar feed. | Internal | Low | No | — |
| `Event_Classification` | Strategic or signature event label for SLC visibility. | Internal | Low | No | — |
| `Approved_Version_Id` | Explicit approved edit-version reference; cleared when a later draft is saved. | Internal | Low | No | — |
| `Created_At` | Server creation timestamp. | Internal | Low | No | — |
| `Updated_At` | Server update timestamp. | Internal | Low | No | — |
