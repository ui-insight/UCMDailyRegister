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
| POST   | `/api/v1/submissions/{id}/edit`                       | Trigger AI edit for a submission       |
| GET    | `/api/v1/submissions/{id}/versions`                   | List all edit versions                 |
| POST   | `/api/v1/submissions/{id}/versions/{version_id}/finalize` | Finalize an editor version         |

!!! info "Edit Triggering"
    `POST /submissions/{id}/edit` is an asynchronous operation. It creates an `AI_Suggested` EditVersion and returns immediately with the new version ID.

## Newsletters

| Method | Path                                                  | Description                            |
|--------|-------------------------------------------------------|----------------------------------------|
| POST   | `/api/v1/newsletters`                                 | Create a new newsletter issue          |
| GET    | `/api/v1/newsletters`                                 | List newsletters (with filters)        |
| GET    | `/api/v1/newsletters/{id}`                            | Get a newsletter with items            |
| PUT    | `/api/v1/newsletters/{id}`                            | Update newsletter metadata             |
| DELETE | `/api/v1/newsletters/{id}`                            | Delete a newsletter                    |

### Newsletter Items

| Method | Path                                                          | Description                      |
|--------|---------------------------------------------------------------|----------------------------------|
| POST   | `/api/v1/newsletters/{id}/items`                              | Add an item to the newsletter    |
| PUT    | `/api/v1/newsletters/{id}/items/{item_id}`                    | Update item (section, order)     |
| DELETE | `/api/v1/newsletters/{id}/items/{item_id}`                    | Remove an item                   |
| PUT    | `/api/v1/newsletters/{id}/items/reorder`                      | Bulk reorder items               |

### Assembly & Export

| Method | Path                                                  | Description                            |
|--------|-------------------------------------------------------|----------------------------------------|
| POST   | `/api/v1/newsletters/{id}/assemble`                   | Auto-assemble from approved submissions|
| GET    | `/api/v1/newsletters/{id}/export`                     | Export newsletter as .docx             |

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
| GET    | `/api/v1/schedule-configs`                    | List all schedule configs            |
| GET    | `/api/v1/schedule-configs/active`             | Get the currently active config      |

## Allowed Values

| Method | Path                                          | Description                          |
|--------|-----------------------------------------------|--------------------------------------|
| GET    | `/api/v1/allowed-values`                      | List values (requires `?group=` param)|

??? example "Query Example"
    ```
    GET /api/v1/allowed-values?group=Submission_Category
    ```
    Returns all allowed values for submission categories (Event, Announcement, Deadline, Opportunity, etc.).
