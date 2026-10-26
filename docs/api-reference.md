# API Reference

All endpoints are prefixed with `/api/v1`. Responses use JSON. Errors return standard `{ "detail": "..." }` bodies.

## Authorization

Public requests carry no credentials. Staff, SLC, and Event Services access
reaches the API one of two ways, selected by `AUTH_PROVIDER`:

- **Session token** (`AUTH_PROVIDER=oidc`): after Microsoft Entra sign-in the
  backend mints a signed session token; the client sends it as
  `Authorization: Bearer <token>`. An invalid or expired token is a `401`.
- **Trusted auth boundary** (`AUTH_PROVIDER=header`): the reverse proxy injects
  `X-Trusted-User-Role` and `X-Trusted-Auth-Secret`, and the backend accepts
  the role only when the secret matches `TRUSTED_ROLE_HEADER_SECRET`.

Each mode honors only its own credential: under `header` a bearer token is
ignored, and under `oidc` the `X-Trusted-*` headers are ignored. Client-supplied
`X-User-Role` is rejected.

## Auth

| Method | Path                      | Description |
|--------|---------------------------|-------------|
| GET    | `/api/v1/auth/config`     | `{ "sso_enabled": bool }`. Unauthenticated; the landing page reads it. |
| GET    | `/api/v1/auth/me`         | The signed-in identity `{ subject, name, role }`. Requires a bearer token. |
| GET    | `/api/v1/auth/sso/login`  | Redirects the browser to Microsoft Entra. Optional `login_hint=<email>` pre-fills Microsoft's form (otherwise the account picker is forced); optional `next=<in-app path>` is remembered and returned in the callback fragment. `oidc` only. |
| GET    | `/api/v1/auth/callback`   | Entra reply URL. Mints a session token and redirects to the SPA's `/sso/callback` with it in the URL fragment (plus `next` if one was given), or with `#error=<reason>`. `oidc` only. |
| GET    | `/api/v1/auth/logout`     | Redirects through Entra's end-session endpoint so both sessions end. `oidc` only. |

Callback `error` reasons: `not_authorized` (signed in, but in no mapped App
Role), `unavailable` (directory lookup failed; retry), `misconfigured` (Graph
refused; needs an administrator), `no_account` (no email claim),
`sign_in_failed` (Entra rejected the exchange).

## Health

| Method | Path              | Description          |
|--------|-------------------|----------------------|
| GET    | `/api/v1/health`  | Returns service status and version |
| GET    | `/api/v1/readyz`  | Readiness probe — verifies load-bearing reference tables are seeded |

## Submissions

| Method | Path                                          | Description                          |
|--------|-----------------------------------------------|--------------------------------------|
| POST   | `/api/v1/submissions`                         | Create a new submission              |
| GET    | `/api/v1/submissions`                         | List submissions (with filters)      |
| GET    | `/api/v1/submissions/{id}`                    | Get a single submission              |
| PATCH  | `/api/v1/submissions/{id}`                    | Update a submission (staff)          |
| DELETE | `/api/v1/submissions/{id}`                    | Delete a submission                  |

### Submission Links

| Method | Path                                                  | Description                  |
|--------|-------------------------------------------------------|------------------------------|
| POST   | `/api/v1/submissions/{id}/links`                      | Add a link to a submission   |
| DELETE | `/api/v1/submissions/{id}/links/{link_id}`            | Remove a link                |

### Schedule Requests

| Method | Path                                                              | Description                          |
|--------|-------------------------------------------------------------------|--------------------------------------|
| POST   | `/api/v1/submissions/{id}/schedule`                               | Add a schedule request (staff)       |
| DELETE | `/api/v1/submissions/{id}/schedule/{schedule_id}`                 | Remove a schedule request            |
| POST   | `/api/v1/submissions/{id}/schedule/{schedule_id}/skip`            | Skip a recurring occurrence (staff)  |
| POST   | `/api/v1/submissions/{id}/schedule/{schedule_id}/reschedule`      | Move a recurring occurrence (staff)  |

### Image

Each submission supports at most one image attachment.

| Method | Path                                                  | Description                    |
|--------|-------------------------------------------------------|--------------------------------|
| POST   | `/api/v1/submissions/{id}/image`                      | Upload the image attachment    |
| GET    | `/api/v1/submissions/{id}/image`                      | Fetch the image bytes          |

## AI Edits

| Method | Path                                                  | Description                            |
|--------|-------------------------------------------------------|----------------------------------------|
| POST   | `/api/v1/ai-edits/{id}/edit`                          | Trigger AI edit for a submission       |
| GET    | `/api/v1/ai-edits/tasks/{task_id}`                    | Read durable task status and result    |
| POST   | `/api/v1/ai-edits/tasks/{task_id}/retry`               | Retry a failed task with unchanged source; active/completed retries reuse the same task |
| GET    | `/api/v1/ai-edits/{id}/versions`                      | List all edit versions                 |
| GET    | `/api/v1/ai-edits/{id}/versions/{version_id}`         | Get a specific edit version            |
| POST   | `/api/v1/ai-edits/{id}/finalize`                      | Save the editor's final version; send `Base_Staff_Revision_Id` (the submission's `Staff_Revision_Id` when loaded) and a newer staff save makes this a 409 whose `detail.Current_Revision` holds the newer text |

!!! info "Edit Triggering"
    `POST /ai-edits/{id}/edit` returns 202 with a durable task ID. Poll the task endpoint for `queued`, `running`, `succeeded` or `failed`; a successful task's `Result` includes the edited text, confidence score, flags, embedded links, and provider/model used. A full queue returns 503 with `Retry-After`; different pending instructions or a changed source on retry return 409. All task endpoints require staff authorization.

The edit response includes `AI_Provider` and `AI_Model` fields so the UI can display which LLM produced the suggestion.

## Newsletters

| Method | Path                                                  | Description                            |
|--------|-------------------------------------------------------|----------------------------------------|
| POST   | `/api/v1/newsletters`                                 | Create a new newsletter issue          |
| GET    | `/api/v1/newsletters`                                 | List newsletters with filters (staff)  |
| GET    | `/api/v1/newsletters/{id}`                            | Get a newsletter with items (staff)    |
| PATCH  | `/api/v1/newsletters/{id}/status?status=...`          | Update newsletter status               |
| DELETE | `/api/v1/newsletters/{id}`                            | Delete a newsletter                    |

### Newsletter Items

| Method | Path                                                          | Description                      |
|--------|---------------------------------------------------------------|----------------------------------|
| POST   | `/api/v1/newsletters/{id}/items`                              | Add an item to the newsletter    |
| PATCH  | `/api/v1/newsletters/{id}/items/{item_id}`                    | Update item (section, order, copy; changed copy sets `Edition_Edited`) |
| POST   | `/api/v1/newsletters/{id}/items/{item_id}/refresh-from-approved` | Replace the item's copy with the submission's approved revision (409 if none) |
| POST   | `/api/v1/newsletters/{id}/items/{item_id}/keep-edition-copy` | Keep the item's copy and stop flagging the current approved revision (409 if none) |
| PATCH  | `/api/v1/newsletters/{id}/external-items/{item_id}`           | Update an imported external item |
| DELETE | `/api/v1/newsletters/{id}/items/{item_id}`                    | Remove an item                   |
| DELETE | `/api/v1/newsletters/{id}/external-items/{item_id}`           | Remove an imported external item |
| PUT    | `/api/v1/newsletters/{id}/reorder`                            | Bulk reorder submission items    |

### Newsletter Builder Imports

| Method | Path                                                                  | Description                                 |
|--------|-----------------------------------------------------------------------|---------------------------------------------|
| GET    | `/api/v1/newsletters/{id}/recurring-messages`                         | List recurring-message candidates for issue |
| POST   | `/api/v1/newsletters/{id}/recurring-messages/{recurring_message_id}`  | Add or restore a recurring message          |
| POST   | `/api/v1/newsletters/{id}/recurring-messages/{recurring_message_id}/skip` | Skip a recurring message for this issue |
| GET    | `/api/v1/newsletters/{id}/calendar-events`                            | List candidate calendar events              |
| POST   | `/api/v1/newsletters/{id}/calendar-events`                            | Import a calendar event                     |
| GET    | `/api/v1/newsletters/{id}/job-postings`                               | List candidate job postings                 |
| POST   | `/api/v1/newsletters/{id}/job-postings`                               | Import a job posting                        |

### Assembly & Export

| Method | Path                                                  | Description                            |
|--------|-------------------------------------------------------|----------------------------------------|
| POST   | `/api/v1/newsletters/assemble`                        | Auto-assemble issue content            |
| GET    | `/api/v1/newsletters/{id}/export`                     | Export newsletter as .docx; inline links become clickable hyperlinks (https and mailto only) |

Newsletter items and external items in newsletter responses include `Link_Findings`: link problems to resolve before export (`unsafe_link`, `tracking_link` with the real `Suggested_Href`, `bare_url`, `missing_submitted_link`). The Builder lists each item's links and these findings, and counts affected items beside **Export Word Doc**.

## Recurring Messages

These endpoints are staff-only and manage centrally maintained editorial content that can be scheduled independently of public submissions.

| Method | Path                                                  | Description                                 |
|--------|-------------------------------------------------------|---------------------------------------------|
| GET    | `/api/v1/recurring-messages`                          | List recurring messages                     |
| POST   | `/api/v1/recurring-messages`                          | Create a recurring message                  |
| GET    | `/api/v1/recurring-messages/{id}`                     | Get a single recurring message              |
| PATCH  | `/api/v1/recurring-messages/{id}`                     | Update a recurring message                  |
| DELETE | `/api/v1/recurring-messages/{id}`                     | Delete a recurring message                  |

## Style Rules

| Method | Path                                          | Description                          |
|--------|-----------------------------------------------|--------------------------------------|
| POST   | `/api/v1/style-rules`                         | Create a style rule                  |
| GET    | `/api/v1/style-rules`                         | List rules (filter by rule set)      |
| GET    | `/api/v1/style-rules/{id}`                    | Get a single rule                    |
| PATCH  | `/api/v1/style-rules/{id}`                    | Update a rule                        |
| DELETE | `/api/v1/style-rules/{id}`                    | Delete a rule                        |

## Sections

| Method | Path                                  | Description                                  |
|--------|---------------------------------------|----------------------------------------------|
| GET    | `/api/v1/sections`                    | List all sections (filter by newsletter type) |

## Schedule

### Configs

| Method | Path                                          | Description                          |
|--------|-----------------------------------------------|--------------------------------------|
| GET    | `/api/v1/schedule/configs`                    | List all schedule configs            |
| GET    | `/api/v1/schedule/active`                     | Get the active config, next publish date, submission deadline, and any active override |
| GET    | `/api/v1/schedule/valid-dates?from=...&to=...`| List valid publication dates in a range, respecting schedule config and blackouts (max range: 366 days) |

### Blackout Dates

Blackout dates block a specific date from being a valid publication date.

| Method | Path                                                  | Description                          |
|--------|-------------------------------------------------------|--------------------------------------|
| GET    | `/api/v1/schedule/blackout-dates`                     | List active blackout dates           |
| POST   | `/api/v1/schedule/blackout-dates`                     | Create a blackout date               |
| DELETE | `/api/v1/schedule/blackout-dates/{blackout_id}`       | Delete a blackout date               |

### Mode Overrides

Mode overrides activate an alternate schedule mode (e.g., winter break) for a date range.

| Method | Path                                                  | Description                          |
|--------|-------------------------------------------------------|--------------------------------------|
| GET    | `/api/v1/schedule/mode-overrides`                     | List schedule mode overrides         |
| POST   | `/api/v1/schedule/mode-overrides`                     | Create a mode override for a date range |
| DELETE | `/api/v1/schedule/mode-overrides/{override_id}`       | Delete a mode override               |

### Custom Publish Dates

Custom publish dates add one-off publication dates outside the regular cadence (typically used during winter break).

| Method | Path                                                  | Description                          |
|--------|-------------------------------------------------------|--------------------------------------|
| GET    | `/api/v1/schedule/custom-dates`                       | List custom publish dates            |
| POST   | `/api/v1/schedule/custom-dates`                       | Add a custom publish date            |
| DELETE | `/api/v1/schedule/custom-dates/{custom_date_id}`      | Delete a custom publish date         |

## Allowed Values

| Method | Path                                          | Description                          |
|--------|-----------------------------------------------|--------------------------------------|
| GET    | `/api/v1/allowed-values`                      | List values (requires `?group=` param)|

??? example "Query Example"
    ```
    GET /api/v1/allowed-values?group=Submission_Category
    ```
    Returns all allowed values for submission categories (Event, Announcement, Deadline, Opportunity, etc.).

## Settings

| Method | Path                                          | Description                                |
|--------|-----------------------------------------------|--------------------------------------------|
| GET    | `/api/v1/settings/ai`                         | Get active LLM provider and configuration  |

The settings endpoint returns read-only configuration data for the frontend Settings page. No secrets are exposed.

??? example "Response Example"
    ```json
    {
      "active_provider": "mindrouter",
      "active_model": "moonshotai/kimi-k3",
      "endpoint_url": "https://mindrouter.uidaho.edu/v1/chat/completions",
      "providers": {
        "claude": {
          "model": "claude-sonnet-4-20250514",
          "configured": false
        },
        "openai": {
          "model": "gpt-4o",
          "configured": false
        },
        "mindrouter": {
          "model": "moonshotai/kimi-k3",
          "endpoint_url": "https://mindrouter.uidaho.edu/v1/chat/completions",
          "configured": true
        }
      }
    }
    ```

    - `active_provider` -- the `LLM_PROVIDER` environment variable value
    - `active_model` -- the model string for the active provider
    - `endpoint_url` -- present only when provider is `mindrouter`
    - `providers[*].configured` -- `true` if the API key environment variable is set (non-empty)

## Feedback

Public `POST /api/v1/feedback` captures a report and returns its created record.
The reported role and browser context are client-provided diagnostic data, not a
verified actor identity. The notifier is disabled.

Staff-only routes:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/feedback` | Review reports |
| GET | `/api/v1/feedback/summary` | Queue/delivery counts |
| PATCH | `/api/v1/feedback/{id}` | Review status and issue reference |
| POST | `/api/v1/feedback/{id}/notification/retry` | Retry configured delivery adapter |
| GET | `/api/v1/feedback/{id}/github-export/preview` | Internal editable draft and advisory email/phone warnings; not a reviewed export |
| POST | `/api/v1/feedback/{id}/github-export` | Prepare explicitly reviewed `Title`/`Body` with `Review_Confirmed: true`; record preparation time/fingerprint |
| GET | `/api/v1/feedback/{id}/github-export` | Retired unreviewed export; returns 410 without report text |

Review/redact the complete title, body and diagnostic context before confirming.
Only the finalized reviewed copy can be copied or opened in a prefilled GitHub
URL. Editing the draft clears confirmation and external actions. Warnings are
advisory and cannot identify every private detail. URL parameters already share
content with GitHub; no issue is automatically posted. The original report is
unchanged. The latest preparation timestamp and artifact SHA-256 record an
export preparation, not delivery. See [Data governance](data-governance.md).

## Harvested events and SLC triage

Staff or SLC role required. These are separate from the PII-redacted submission
calendar feed (`GET /submissions/?slc_calendar_only=true`).

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/slc/harvest` | Upsert Trumba events and queue background ops assessment |
| GET | `/api/v1/slc/harvested-events` | Paginated source occurrences |
| PATCH | `/api/v1/slc/harvested-events/{id}` | SLC review; flagging promotes a submission |
| POST | `/api/v1/slc/harvested-events/{id}/acknowledge-upstream` | Clear SLC change marker |

## Event Services ops triage

Staff or ops role required. Ops and SLC states and acknowledgment markers are
independent. AI suggestions are advisory; staff confirm or reject them.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/ops/harvested-events` | Paginated events, assessments and needs filters |
| PATCH | `/api/v1/ops/harvested-events/{id}` | Review/dismiss/restore ops state |
| POST | `/api/v1/ops/harvested-events/{id}/acknowledge-upstream` | Clear ops change marker |
| POST | `/api/v1/ops/harvested-events/{id}/needs` | Add a staff-origin confirmed need |
| PATCH | `/api/v1/ops/harvested-events/{id}/needs/{need}` | Confirm/reject a suggestion |
| DELETE | `/api/v1/ops/harvested-events/{id}/needs/{need}` | Remove a staff-origin need |

Sections, schedule GETs and AI settings are public metadata today. Schedule
mutations are staff-only. The full dataset/role matrix is maintained in
[Data governance](data-governance.md).
