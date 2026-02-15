# Data Model

## Naming Convention

All database columns use **PascalCase_With_Underscores** (e.g., `Submission_Title`, `Is_Active`, `Created_At`). This matches the existing UCM data conventions and is enforced consistently across all models.

## Entity Overview

| Entity            | Purpose                                              |
|-------------------|------------------------------------------------------|
| AllowedValue      | Controlled vocabulary for categorical fields          |
| Submission        | Campus announcement submitted for newsletter          |
| SubmissionLink    | URLs attached to a submission                         |
| ScheduleRequest   | Requested publication dates for a submission          |
| EditVersion       | Immutable snapshot of text at each editing stage      |
| Newsletter        | A single issue of TDR or My UI                       |
| NewsletterItem    | A submission placed into a newsletter with ordering   |
| NewsletterSection | Named section within a newsletter type                |
| StyleRule         | Editorial rule applied during AI editing              |
| ScheduleConfig    | Publishing schedule parameters per newsletter type    |

## Entity Details

### AllowedValue

Provides controlled vocabularies for dropdowns and validation. Each row belongs to a `Value_Group` and stores a `Value_Key` / `Display_Label` pair.

**Value Groups (10):**

| Group               | Example Values                                  |
|---------------------|------------------------------------------------|
| Submission_Category | Event, Announcement, Deadline, Opportunity      |
| Newsletter_Type     | TDR, MyUI                                       |
| Target_Newsletter   | TDR_Only, MyUI_Only, Both                       |
| Submission_Status   | Draft, Submitted, In_Review, Approved, Rejected |
| Newsletter_Status   | Draft, Assembled, Published                     |
| Version_Type        | Original, AI_Suggested, Editor_Final            |
| Headline_Case       | Title_Case, Sentence_Case                       |
| Rule_Set            | Shared, TDR, MyUI                               |
| Severity            | Error, Warning, Suggestion                      |
| Schedule_Mode       | Daily_Weekday, Weekly_Monday                    |

### Submission

The core content entity. Each submission contains a title, body text, submitter info, category, target newsletter, and status.

| Key Column          | Type     | Notes                          |
|---------------------|----------|--------------------------------|
| Submission_ID       | UUID PK  | Auto-generated                 |
| Submission_Title    | String   | Headline text                  |
| Body_Text           | Text     | Full announcement content      |
| Submitter_Email     | String   | Contact for the submitter      |
| Category            | String   | FK to AllowedValue             |
| Target_Newsletter   | String   | TDR_Only, MyUI_Only, or Both   |
| Status              | String   | Current workflow status         |

**Relationships:** has many `SubmissionLink`, has many `ScheduleRequest`, has many `EditVersion`.

### SubmissionLink

URLs associated with a submission (e.g., event registration, info pages).

### ScheduleRequest

Requested publication dates. A submission targeting "Both" newsletters may have separate schedule requests for TDR and My UI.

### EditVersion

Immutable audit trail of text transformations. Each version captures the text at one stage.

| Key Column          | Type     | Notes                                  |
|---------------------|----------|----------------------------------------|
| Version_ID          | UUID PK  |                                        |
| Submission_ID       | UUID FK  | Parent submission                      |
| Version_Type        | String   | Original, AI_Suggested, Editor_Final   |
| Title_Text          | String   | Title at this stage                    |
| Body_Text           | Text     | Body at this stage                     |
| Diff_JSON           | JSON     | Computed diff from previous version    |

!!! warning "Immutability"
    EditVersion records are never updated after creation. Each editing action produces a new row, preserving the complete history.

### Newsletter + NewsletterItem

A `Newsletter` represents one issue (e.g., TDR for 2026-02-15). `NewsletterItem` is the join entity linking finalized submissions into a newsletter with section assignment and sort order.

### NewsletterSection

Predefined sections seeded into the database. The system ships with 14 sections (9 for TDR, 5 for My UI).

### StyleRule

Editorial rules loaded by the AI editing pipeline. Each rule has a `Rule_Set` (Shared, TDR, or MyUI), `Severity`, and natural-language `Rule_Text` that gets injected into the LLM prompt.

### ScheduleConfig

Defines publishing cadence per newsletter type (daily weekday for TDR, weekly Monday for My UI). The `schedule_service` resolves which config is currently active.

## Relationship Diagram

```
AllowedValue (standalone lookup)

Submission ──< SubmissionLink
           ──< ScheduleRequest
           ──< EditVersion

Newsletter ──< NewsletterItem >── Submission
           ──< NewsletterItem >── NewsletterSection

StyleRule (standalone, loaded by AI pipeline)
ScheduleConfig (standalone, per newsletter type)
```
