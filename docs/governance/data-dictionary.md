# Data dictionary

Generated from `frontend/src/data/governance-catalog.json`; used by the staff governance page.
Update reviewed metadata in that file, then run `python scripts/check_governance.py --write`.

Catalog review: 2026-10-24; **provisional; owner classification approval pending**.

Labels describe default handling, not institutional classification approval. PII flags include
incidental personal information risk; published release decisions apply to individual content.
Retention categories are defined in [Retention and disposal](retention.md).

## `ai_edit_tasks`

Durable staff-only AI edit requests, bounded execution state, restart interruption and committed response copies; source-level retention applies.

Steward role: UCM editorial staff / technical operations. Source: staff / AI editing pipeline.
Retention category: `submission_source`. Extension: Operational support.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | Durable task UUID returned as Task_Id by the staff API. | Internal | No | — |
| `Submission_Id` | Parent source submission; task copies are deleted with the source. | Internal | No | — |
| `Newsletter_Type` | Publication context for this AI request. | Internal | No | Newsletter_Type |
| `Editor_Instructions` | Staff-provided instructions, potentially containing unpublished copy or incidental personal data. | Confidential | Yes | — |
| `Status` | Code-validated queued, running, succeeded or failed task state. | Internal | No | — |
| `Source_Fingerprint` | SHA-256 fingerprint of source copy, category, target, notes and links for stale-result checks. | Internal | No | — |
| `Active_Key` | Nullable unique submission/newsletter key preventing duplicate pending work. | Internal | No | — |
| `Run_Id` | Worker attempt UUID used to prevent late invalidated attempts from saving. | Internal | No | — |
| `Result_JSON` | Committed AI edit response including copy, links, flags, diffs and provenance; may repeat personal data. | Confidential | Yes | — |
| `Error_Message` | Controlled application failure/retry message; external exception details are excluded. | Internal | No | — |
| `Created_At` | Request acceptance timestamp in UTC. | Internal | No | — |
| `Updated_At` | Latest task transition timestamp in UTC. | Internal | No | — |

## `allowed_values`

Central governed value list for categorical fields, adapted from OpenERA AllowedValues.

Steward role: UCM operations. Source: staff / system.
Retention category: `configuration`. Extension: UDM-derived pattern.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Value_Group` | Vocabulary family used by API, forms, and settings. | Public | No | — |
| `Code` | Machine-readable value within the group. | Public | No | — |
| `Label` | Human-readable value shown in the user interface. | Public | No | — |
| `Display_Order` | Sort order for menus and settings views. | Public | No | — |
| `Is_Active` | Soft-disable flag for values that should no longer be selected. | Internal | No | — |
| `Visibility_Role` | Public or staff visibility scope for submission categories. | Internal | No | — |
| `Description` | Steward-facing explanation of the value. | Public | No | — |

## `blackout_dates`

Dates when one or all newsletters should not publish.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Blackout_Date` | Suppressed publication date. | Public | No | — |
| `Newsletter_Type` | Optional publication scope; null applies broadly. | Public | No | Newsletter_Type |
| `Description` | Reason for the blackout. | Public | No | — |
| `Is_Active` | Soft-disable flag. | Internal | No | — |

## `custom_publish_dates`

Ad hoc publish dates used during winter break or other non-standard schedules.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Type` | Publication code. | Public | No | Newsletter_Type |
| `Publish_Date` | Manual issue date. | Public | No | — |
| `Description` | Reason for the custom publish date. | Internal | Yes | — |
| `Created_At` | Server creation timestamp. | Internal | No | — |

## `edit_versions`

Append-only snapshots of original, AI-suggested, and editor-final copy.

Steward role: UCM editorial staff. Source: AI / staff.
Retention category: `submission_source`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | No | — |
| `Version_Type` | Editing stage represented by the snapshot. | Internal | No | Version_Type |
| `Headline` | Headline text at this version. | Internal | Yes | — |
| `Body` | Body text at this version. | Internal | Yes | — |
| `Headline_Case` | Headline casing policy applied to this version. | Internal | No | Headline_Case |
| `Flags` | JSON list of AI or rule findings. | Internal | Yes | — |
| `Changes_Made` | JSON list of generated or editor-facing change summaries. | Internal | Yes | — |
| `AI_Provider` | LLM provider used for AI-generated versions. | Internal | No | — |
| `AI_Model` | LLM model used for AI-generated versions. | Internal | No | — |
| `Editor_Instructions` | Free-text editor instructions passed into an edit run. | Confidential | Yes | — |
| `Created_At` | Immutable version creation timestamp. | Internal | No | — |

## `harvested_events`

External calendar occurrences with independent SLC and ops review lenses.

Steward role: UCM and Event Services. Source: Trumba / staff.
Retention category: `external_working`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Source_Type` | External feed source family. | Internal | No | — |
| `Source_Id` | External event-occurrence identifier. | Internal | No | — |
| `Series_Id` | External repeating-series identifier. | Internal | No | — |
| `Source_Url` | External source link; may include query parameters. | Internal | Yes | — |
| `Title` | Upstream public event title; can name people. | Internal | Yes | — |
| `Description` | Upstream event details; can include personal contact information. | Internal | Yes | — |
| `Location` | Upstream event venue or location. | Internal | No | — |
| `Event_Start` | Event start timestamp. | Internal | No | — |
| `Event_End` | Optional event end timestamp. | Internal | No | — |
| `All_Day` | All-day occurrence indicator. | Internal | No | — |
| `Category_Path` | Upstream category hierarchy. | Internal | No | — |
| `Is_Canceled` | Upstream cancellation marker. | Internal | No | — |
| `Content_Hash` | Hash of source content used to detect upstream changes. | Internal | No | — |
| `SLC_Review_Status` | Independent SLC triage state. | Internal | No | SLC_Review_Status |
| `Ops_Review_Status` | Independent Event Services triage state. | Internal | No | Ops_Review_Status |
| `Ops_Assessed_Content_Hash` | Content hash used for current ops assessment. | Internal | No | — |
| `Upstream_Changed_At` | Time source changed after SLC flagging; cleared by SLC acknowledgment. | Internal | No | — |
| `Ops_Upstream_Changed_At` | Time source changed after ops review; cleared independently by ops. | Internal | No | — |
| `Promoted_Submission_Id` | SLC-only submission created by promotion; cleared if submission is deleted. | Internal | No | — |
| `First_Seen_At` | First harvest timestamp. | Internal | No | — |
| `Last_Seen_At` | Most recent observation timestamp. | Internal | No | — |

## `newsletter_external_items`

Placement of imported calendar, job, or other external content into a newsletter issue.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `publication_archive`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Id` | Foreign key to newsletters. | Internal | No | — |
| `Section_Id` | Foreign key to newsletter_sections. | Internal | No | — |
| `Source_Type` | External source category, such as calendar_event or job_posting. | Public | No | — |
| `Source_Id` | Source-system identifier. | Internal | No | — |
| `Source_Url` | Source-system URL. | Public | Yes | — |
| `Event_Start` | Event start timestamp where applicable. | Public | No | — |
| `Event_End` | Event end timestamp where applicable. | Public | No | — |
| `Location` | Event location where applicable. | Public | No | — |
| `Position` | Ordering within the section. | Public | No | — |
| `Final_Headline` | Final published headline. | Internal | Yes | — |
| `Final_Body` | Final published body. | Internal | Yes | — |

## `newsletter_items`

Placement of a finalized submission into a newsletter issue and section.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `publication_archive`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Id` | Foreign key to newsletters. | Internal | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | No | — |
| `Section_Id` | Foreign key to newsletter_sections. | Internal | No | — |
| `Position` | Ordering within the section. | Public | No | — |
| `Final_Headline` | Final published headline. | Internal | Yes | — |
| `Final_Body` | Final published body. | Internal | Yes | — |
| `Run_Number` | Occurrence number for repeated publication. | Internal | No | — |
| `Manually_Placed` | Staff changed section placement; automatic reassembly preserves it. | Internal | No | — |
| `Source_Version_Id` | Edit-version reference from which issue copy was assembled. | Internal | No | — |
| `Edition_Edited` | Staff changed issue copy; reassembly preserves the edition override. | Internal | No | — |
| `Upstream_Reviewed_Version_Id` | Approved revision reviewed and intentionally not applied to this issue. | Internal | No | — |

## `newsletter_sections`

Governed section taxonomy and layout requirements for each newsletter type.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Type` | Publication code. | Public | No | Newsletter_Type |
| `Name` | Human-readable section name. | Public | No | — |
| `Slug` | Machine-readable section identifier. | Public | No | — |
| `Display_Order` | Default section order. | Public | No | — |
| `Description` | Section purpose. | Public | No | — |
| `Requires_Image` | Whether items in the section need an image. | Internal | No | — |
| `Image_Dimensions` | Expected image dimensions. | Internal | No | — |
| `Is_Active` | Soft-retirement flag. | Internal | No | — |

## `newsletters`

Dated editions of The Daily Register or My UI.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `publication_archive`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Type` | Publication code. | Public | No | Newsletter_Type |
| `Publish_Date` | Issue date. | Public | No | — |
| `Status` | Issue lifecycle state. | Internal | No | Newsletter_Status |
| `Created_At` | Server creation timestamp. | Internal | No | — |
| `Updated_At` | Server update timestamp. | Internal | No | — |

## `ops_need_assessments`

AI-suggested needs and staff verdicts for a harvested event.

Steward role: Event Services. Source: AI / staff.
Retention category: `external_working`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Harvested_Event_Id` | Parent harvested event reference; assessment cascades on event deletion. | Internal | No | — |
| `Need` | Operational service code. | Internal | No | Ops_Need_Type |
| `Confidence` | AI confidence code; null for staff-added needs. | Internal | No | Ops_Need_Confidence |
| `Rationale` | Model or staff explanation; can quote source content and contain personal information. | Internal | Yes | — |
| `Verdict` | Staff judgment of the suggested need. | Internal | No | Ops_Need_Verdict |
| `Source` | AI or staff origin of the assessment. | Internal | No | Ops_Need_Source |
| `Created_At` | Record creation timestamp. | Internal | No | — |

## `product_feedback`

User reports and diagnostic context; only staff review the queue.

Steward role: UCM product support. Source: user / browser.
Retention category: `feedback`. Extension: Operational support.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Feedback_Type` | Reported bug or product idea. | Internal | No | — |
| `Summary` | User-entered short report summary; can contain incidental personal information. | Confidential | Yes | — |
| `Details` | User-entered report text; can contain incidental sensitive information. | Confidential | Yes | — |
| `Contact_Email` | Optional reporter email for follow-up. | Confidential | Yes | — |
| `Submitter_Role` | Client-reported UI role; not an authenticated actor identity. | Internal | No | — |
| `Route` | Reported page route; free text from client, potentially identifying. | Internal | Yes | — |
| `App_Environment` | Client-reported deployment label. | Internal | No | — |
| `Host` | Client-reported host; operational context. | Internal | Yes | — |
| `Browser` | Client-reported user agent. | Internal | Yes | — |
| `Viewport` | Reported viewport dimensions. | Internal | No | — |
| `Status` | Product-feedback workflow status. | Internal | No | — |
| `GitHub_URL` | Optional engineering issue reference; review sharing permissions. | Internal | Yes | — |
| `GitHub_Export_Reviewed_At` | UTC time a staff-confirmed edited export was prepared; not proof an issue was posted. | Internal | No | — |
| `GitHub_Export_SHA256` | Fingerprint of the exact reviewed export artifact; report originals remain unchanged. | Internal | No | — |
| `Notification_Status` | Pending, disabled, failed or sent delivery state. | Internal | No | — |
| `Notification_Attempts` | Number of attempted notification deliveries. | Internal | No | — |
| `Notification_Sent_At` | Latest successful delivery time, if any. | Internal | No | — |
| `Notification_Last_Error` | Exception class for latest delivery failure; older releases could store arbitrary error text. | Confidential | Yes | — |
| `Created_At` | Record creation timestamp. | Internal | No | — |
| `Updated_At` | Most recent record update timestamp. | Internal | No | — |

## `recurring_message_issue_overrides`

Issue-specific exceptions, currently used to preserve skipped recurring messages.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Recurring_Message_Id` | Foreign key to recurring_messages. | Internal | No | — |
| `Newsletter_Id` | Foreign key to newsletters. | Internal | No | — |
| `Override_Action` | Issue-level action, currently skip. | Internal | No | — |
| `Created_At` | Server creation timestamp. | Internal | No | — |

## `recurring_messages`

Staff-managed reusable copy surfaced on a configured cadence.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Type` | Publication code. | Public | No | Newsletter_Type |
| `Section_Id` | Foreign key to newsletter_sections. | Internal | No | — |
| `Headline` | Reusable message headline. | Internal | Yes | — |
| `Body` | Reusable message body. | Internal | Yes | — |
| `Start_Date` | First eligible publish date. | Internal | No | — |
| `Recurrence_Type` | Recurrence rule type. | Internal | No | — |
| `Recurrence_Interval` | Interval for recurring messages. | Internal | No | — |
| `End_Date` | Optional final eligible date. | Internal | No | — |
| `Excluded_Dates` | JSON list of skipped dates. | Internal | No | — |
| `Is_Active` | Soft-disable flag. | Internal | No | — |
| `Created_At` | Server creation timestamp. | Internal | No | — |
| `Updated_At` | Server update timestamp. | Internal | No | — |

## `schedule_configs`

Publication cadence and submission deadline rules by newsletter type and schedule mode.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Type` | Publication code. | Public | No | Newsletter_Type |
| `Mode` | Academic year, summer, or winter break schedule mode. | Internal | No | Schedule_Mode |
| `Submission_Deadline_Description` | Human-readable deadline rule. | Public | No | — |
| `Deadline_Day_Of_Week` | Deadline weekday used in calculations. | Internal | No | — |
| `Deadline_Time` | Deadline time used in calculations. | Internal | No | — |
| `Publish_Day_Of_Week` | Publish weekday where applicable. | Internal | No | — |
| `Is_Daily` | Whether the mode publishes every weekday. | Internal | No | — |
| `Active_Start_Month` | Month when this mode starts. | Internal | No | — |
| `Active_End_Month` | Month when this mode ends. | Internal | No | — |
| `Holiday_Shift_Enabled` | Whether holiday-aware shifting applies. | Internal | No | — |

## `schedule_mode_overrides`

Manual date-range override that forces a newsletter into a configured schedule mode.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Newsletter_Type` | Publication code. | Public | No | Newsletter_Type |
| `Override_Mode` | Schedule mode to apply during the range. | Internal | No | Schedule_Mode |
| `Start_Date` | Inclusive override start date. | Internal | No | — |
| `End_Date` | Inclusive override end date. | Internal | No | — |
| `Description` | Reason for the override. | Internal | Yes | — |
| `Created_At` | Server creation timestamp. | Internal | No | — |

## `style_rules`

Database-managed style rules injected into the AI editing system prompt.

Steward role: UCM editorial staff. Source: staff / system.
Retention category: `configuration`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Rule_Set` | Shared, TDR, or My UI rule scope. | Internal | No | Rule_Set |
| `Category` | Editorial rule category. | Internal | No | — |
| `Rule_Key` | Machine-readable rule key. | Internal | No | — |
| `Rule_Text` | Natural-language editing instruction. | Internal | Yes | — |
| `Is_Active` | Whether future AI edits should use the rule. | Internal | No | — |
| `Severity` | Rule severity for editor attention. | Internal | No | Severity |

## `submission_links`

Normalized hyperlinks attached to submitted content.

Steward role: UCM editorial staff. Source: submitter / staff.
Retention category: `submission_source`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | No | — |
| `Url` | Destination URL supplied with the submission. | Internal | Yes | — |
| `Anchor_Text` | Optional display text for the link. | Internal | Yes | — |
| `Display_Order` | Ordering of links inside the submission. | Public | No | — |

## `submission_schedule_requests`

Requested run dates, recurrence settings, flexibility notes, and skipped occurrence dates.

Steward role: UCM editorial staff. Source: submitter / staff.
Retention category: `submission_source`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Submission_Id` | Foreign key to submissions. | Internal | No | — |
| `Requested_Date` | Primary requested publication date. | Public | No | — |
| `Second_Requested_Date` | Secondary requested date when an item targets both newsletters. | Public | No | — |
| `Repeat_Count` | Legacy number of requested runs. | Internal | No | — |
| `Repeat_Note` | Legacy free-text repeat instructions. | Confidential | Yes | — |
| `Is_Flexible` | Whether editors may choose an alternate date. | Internal | No | — |
| `Flexible_Deadline` | Optional text describing the latest flexible publication deadline. | Confidential | Yes | — |
| `Recurrence_Type` | Recurrence rule type for repeated runs. | Internal | No | — |
| `Recurrence_Interval` | Interval for recurring requests. | Internal | No | — |
| `Recurrence_End_Date` | End date for recurrence expansion. | Internal | No | — |
| `Excluded_Dates` | JSON list of skipped or rescheduled occurrence dates. | Internal | No | — |

## `submissions`

Submitted newsletter or SLC event content with workflow, submitter, image, and routing metadata.

Steward role: UCM editorial staff. Source: submitter / staff.
Retention category: `submission_source`. Extension: Communications extension.

| Column | Meaning | Handling | PII risk | Vocabulary |
| --- | --- | --- | --- | --- |
| `Id` | UUID primary key. | Internal | No | — |
| `Category` | Content category code. | Public | No | Submission_Category |
| `Target_Newsletter` | Publication routing code: TDR, My UI, both, or SLC-only none. | Public | No | Target_Newsletter |
| `Original_Headline` | Submitted headline text. | Internal | Yes | — |
| `Original_Body` | Submitted body text. | Internal | Yes | — |
| `Submitter_Name` | Submitter contact name. | Confidential | Yes | — |
| `Submitter_Email` | Submitter contact email. | Confidential | Yes | — |
| `Submitter_Notes` | Free-text instructions from submitter; may contain incidental PII. | Confidential | Yes | — |
| `Assigned_Editor` | Staff owner for editorial follow-up. | Internal | Yes | — |
| `Editorial_Notes` | Staff-only editorial notes; may contain incidental PII. | Confidential | Yes | — |
| `Has_Image` | Whether an uploaded image is attached. | Public | No | — |
| `Image_Path` | Server-side image path using UUID naming. | Internal | No | — |
| `Survey_End_Date` | Optional survey close date used for survey handling. | Public | No | — |
| `Status` | Editorial workflow state. | Internal | No | Submission_Status |
| `Show_In_SLC_Calendar` | Whether the submission appears in the SLC calendar feed. | Internal | No | — |
| `Event_Classification` | Strategic or signature event label for SLC visibility. | Internal | No | — |
| `Approved_Version_Id` | Explicit approved edit-version reference; cleared when a later draft is saved. | Internal | No | — |
| `Created_At` | Server creation timestamp. | Internal | No | — |
| `Updated_At` | Server update timestamp. | Internal | No | — |
