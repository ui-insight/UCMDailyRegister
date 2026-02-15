# System Architecture

## Three-Tier Architecture

The application follows a standard three-tier design:

```
React SPA (Vite)  --->  FastAPI REST API  --->  SQLite / PostgreSQL
   Port 5173               Port 8001              File / TCP
```

- **Presentation** -- React single-page application served by Vite in development. Communicates exclusively through the REST API.
- **Application** -- FastAPI backend providing versioned endpoints under `/api/v1/`. All business logic lives in service modules.
- **Data** -- SQLAlchemy async ORM with SQLite for local development and PostgreSQL for production. Alembic manages schema migrations.

## Data Flow

The primary data pipeline moves a submission from intake through AI editing to final newsletter export:

```
Contributor submits announcement
        |
        v
  Submission record created (with Links, ScheduleRequests)
        |
        v
  AI Edit Pipeline triggered
        |  - Load style rules from DB
        |  - Construct LLM prompt
        |  - Call provider (Claude / OpenAI)
        |  - Post-process (headline case, diff)
        v
  EditVersion records stored (original -> ai_suggested -> editor_final)
        |
        v
  Editor reviews in dashboard, finalizes copy
        |
        v
  Newsletter assembled (items placed in sections, reordered)
        |
        v
  Word document exported (.docx)
```

## Service Layer

Business logic is organized into focused service modules rather than being embedded in route handlers:

| Service                | Responsibility                                      |
|------------------------|-----------------------------------------------------|
| `submission_service`   | CRUD for submissions, links, schedule requests       |
| `newsletter_service`   | Newsletter assembly, item ordering, export           |
| `schedule_service`     | Schedule configs, active schedule resolution         |
| `ai.editor`           | LLM prompt construction, pre/post-processing         |
| `ai.providers`        | Provider factory, Claude and OpenAI adapters          |
| `style_rule_service`  | Style rule CRUD, rule set filtering                  |

## LLM Abstraction

The AI layer uses a provider factory pattern so the LLM backend can be switched via environment variable:

```python
# .env
LLM_PROVIDER=claude   # or "openai"
```

Each provider implements a common interface (`generate_edit`), and the factory instantiates the correct adapter at startup. This keeps route handlers and the editing pipeline independent of any specific LLM vendor.

## Directory Structure

```
UCMDailyRegister-App/
  backend/
    app/
      api/v1/          # Route modules (submissions, newsletters, etc.)
      db/              # Database engine, session, seed script
      models/          # SQLAlchemy ORM models
      schemas/         # Pydantic request/response schemas
      services/        # Business logic services
        ai/            # LLM abstraction and editing pipeline
      main.py          # FastAPI app factory
    alembic/           # Migration scripts
    requirements.txt
  frontend/
    src/
      components/      # React components
      pages/           # Route-level views
      api/             # API client functions
      types/           # TypeScript interfaces
    vite.config.ts
  docs/                # MkDocs documentation (this site)
```

!!! tip "Async Everywhere"
    All database operations use SQLAlchemy's async engine and `AsyncSession`. Route handlers are `async def` and service functions are awaited throughout.
