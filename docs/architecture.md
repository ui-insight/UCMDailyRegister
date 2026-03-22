# System Architecture

## Three-Tier Architecture

The application follows a standard three-tier design:

```
React SPA (Vite)  --->  FastAPI REST API  --->  SQLite / PostgreSQL
   Port 5173               Port 8001              File / TCP
```

- **Presentation** -- React single-page application served by Vite in development and nginx in production. Communicates exclusively through the REST API. Styled with Tailwind CSS v4 using University of Idaho brand tokens (see [Branding](branding.md)).
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
        |  - Call provider (Claude / OpenAI / MindRouter)
        |  - Post-process (headline case, diff)
        v
  EditVersion records stored (original -> ai_suggested -> editor_final)
        |
        v
  Editor reviews in dashboard, finalizes copy
        |
        v
  Newsletter assembled (submissions, recurring messages, and imported external items placed in sections, reordered)
        |
        v
  Word document exported (.docx)
```

## Service Layer

Business logic is organized into focused service modules rather than being embedded in route handlers:

| Service                | Responsibility                                       |
|------------------------|------------------------------------------------------|
| `submission_service`   | CRUD for submissions, links, schedule requests        |
| `newsletter_service`   | Newsletter assembly, item ordering, export            |
| `recurring_message_service` | Recurring message CRUD, cadence resolution, issue skips |
| `schedule_service`     | Schedule configs, active schedule resolution          |
| `ai.editor`           | LLM prompt construction, pre/post-processing          |
| `ai.factory`          | Provider factory (Claude, OpenAI, MindRouter)         |
| `ai.claude_provider`  | Anthropic Claude API adapter                          |
| `ai.openai_provider`  | OpenAI API adapter                                    |
| `ai.mindrouter_provider` | MindRouter on-prem adapter (httpx, OpenAI-compatible) |
| `style_rule_service`  | Style rule CRUD, rule set filtering                   |

## LLM Abstraction

The AI layer uses a provider factory pattern so the LLM backend can be switched via environment variable:

```python
# .env
LLM_PROVIDER=mindrouter   # or "claude" or "openai"
```

Each provider implements the `LLMProvider` abstract base class (`complete` and `complete_json` methods), and the factory instantiates the correct adapter at startup. This keeps route handlers and the editing pipeline independent of any specific LLM vendor.

See [AI Editing](ai-editing.md) for full details on the provider interface and MindRouter specifics.

## Directory Structure

```
UCMDailyRegister-App/
  backend/
    app/
      api/v1/          # Route modules (submissions, newsletters, settings, etc.)
      db/              # Database engine, session, seed script
      models/          # SQLAlchemy ORM models
      schemas/         # Pydantic request/response schemas
      services/        # Business logic services
        ai/            # LLM abstraction and editing pipeline
      config.py        # Pydantic-based settings (reads .env)
      main.py          # FastAPI app factory
    data/              # JSON seed files
    tests/             # pytest async tests
    pyproject.toml     # Dependencies and project metadata
  frontend/
    src/
      components/      # React components (editor, submission, layout)
      pages/           # Route-level views
      api/             # Typed API client functions
      types/           # TypeScript interfaces
      index.css        # Tailwind v4 @theme with brand tokens
    index.html         # Entry point (Google Fonts, page title)
    nginx.conf         # Production reverse proxy config
    vite.config.ts
  docs/                # MkDocs documentation (this site)
  docker-compose.yml   # Three-service stack (frontend, backend, db)
  .env.example         # Environment variable template
  mkdocs.yml           # Documentation site config
```

!!! tip "Async Everywhere"
    All database operations use SQLAlchemy's async engine and `AsyncSession`. Route handlers are `async def` and service functions are awaited throughout.
