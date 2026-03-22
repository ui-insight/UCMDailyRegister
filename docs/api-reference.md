# API Reference

All endpoints are prefixed with `/api/v1`. Responses use JSON. Errors return standard `{ "detail": "..." }` bodies.

## Health

| Method | Path              | Description          |
|--------|-------------------|----------------------|
| GET    | `/api/v1/health`  | Returns service status and version |

## Submissions

| Method | Path                                          | Description                          |
|--------|-----------------------------------------------|--------------------------------------|
| POST   | `/api/v1/submissions`                         | Create a new submission              |
| GET    | `/api/v1/submissions`                         | List submissions (with filters)      |
| GET    | `/api/v1/submissions/{id}`                    | Get a single submission              |
| PUT    | `/api/v1/submissions/{id}`                    | Update a submission                  |
| DELETE | `/api/v1/submissions/{id}`                    | Delete a submission                  |

### Submission Links

| Method | Path                                                  | Description                  |
|--------|-------------------------------------------------------|------------------------------|
| POST   | `/api/v1/submissions/{id}/links`                      | Add a link to a submission   |
| GET    | `/api/v1/submissions/{id}/links`                      | List links for a submission  |
| DELETE | `/api/v1/submissions/{id}/links/{link_id}`            | Remove a link                |

### Schedule Requests

| Method | Path                                                          | Description                          |
|--------|---------------------------------------------------------------|--------------------------------------|
| POST   | `/api/v1/submissions/{id}/schedule-requests`                  | Add a schedule request               |
| GET    | `/api/v1/submissions/{id}/schedule-requests`                  | List schedule requests               |
| DELETE | `/api/v1/submissions/{id}/schedule-requests/{request_id}`     | Remove a schedule request            |

### Images

| Method | Path                                                  | Description                    |
|--------|-------------------------------------------------------|--------------------------------|
| POST   | `/api/v1/submissions/{id}/images`                     | Upload an image attachment     |
| GET    | `/api/v1/submissions/{id}/images`                     | List images for a submission   |
| DELETE | `/api/v1/submissions/{id}/images/{image_id}`          | Remove an image                |

## AI Edits

| Method | Path                                                  | Description                            |
|--------|-------------------------------------------------------|----------------------------------------|
| POST   | `/api/v1/ai-edits/{id}/edit`                          | Trigger AI edit for a submission       |
| GET    | `/api/v1/ai-edits/{id}/versions`                      | List all edit versions                 |
| GET    | `/api/v1/ai-edits/{id}/versions/{version_id}`         | Get a specific edit version            |
| POST   | `/api/v1/ai-edits/{id}/finalize`                      | Save the editor's final version        |

!!! info "Edit Triggering"
    `POST /ai-edits/{id}/edit` triggers the full AI editing pipeline: pre-analysis, LLM call, post-processing, and diff generation. The response includes the edited text, confidence score, flags, embedded links, and the provider/model used.

The edit response includes `AI_Provider` and `AI_Model` fields so the UI can display which LLM produced the suggestion.

## Newsletters

| Method | Path                                                  | Description                            |
|--------|-------------------------------------------------------|----------------------------------------|
| POST   | `/api/v1/newsletters`                                 | Create a new newsletter issue          |
| GET    | `/api/v1/newsletters`                                 | List newsletters (with filters)        |
| GET    | `/api/v1/newsletters/{id}`                            | Get a newsletter with items            |
| PATCH  | `/api/v1/newsletters/{id}/status?status=...`          | Update newsletter status               |
| DELETE | `/api/v1/newsletters/{id}`                            | Delete a newsletter                    |

### Newsletter Items

| Method | Path                                                          | Description                      |
|--------|---------------------------------------------------------------|----------------------------------|
| POST   | `/api/v1/newsletters/{id}/items`                              | Add an item to the newsletter    |
| PATCH  | `/api/v1/newsletters/{id}/items/{item_id}`                    | Update item (section, order)     |
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
| GET    | `/api/v1/newsletters/{id}/export`                     | Export newsletter as .docx             |

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
| PUT    | `/api/v1/style-rules/{id}`                    | Update a rule                        |
| DELETE | `/api/v1/style-rules/{id}`                    | Delete a rule                        |

## Sections

| Method | Path                                  | Description                                  |
|--------|---------------------------------------|----------------------------------------------|
| GET    | `/api/v1/sections`                    | List all sections (filter by newsletter type) |

## Schedule

| Method | Path                                          | Description                          |
|--------|-----------------------------------------------|--------------------------------------|
| GET    | `/api/v1/schedule/configs`                    | List all schedule configs            |
| GET    | `/api/v1/schedule/active`                     | Get the currently active config      |

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
      "active_model": "GPT-OSS-120B",
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
          "model": "GPT-OSS-120B",
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
