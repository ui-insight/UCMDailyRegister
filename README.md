# UCM Daily Register

AI-assisted newsletter production pipeline for the University of Idaho's University Communications and Marketing (UCM) team.

## Features

- **Submission Intake** — Web form for community members to submit announcements, events, job postings, and news items
- **AI-Assisted Editing** — Automated style editing using Claude or OpenAI with AP style and U of I style guide enforcement
- **Editorial Review** — Word-level diff viewer, flag system, accept/reject/modify workflow
- **Newsletter Assembly** — Auto-populate newsletters from approved submissions, organized by section
- **Recurring Message Library** — Staff-managed reusable editorial content with cadence rules and issue-level skip/restore controls
- **Word Export** — Generate formatted .docx files with U of I branding
- **Style Rules Engine** — Data-driven editorial rules injected into LLM prompts, editable via UI

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Frontend | React 19, TypeScript, TailwindCSS, Vite |
| AI | Claude (Anthropic) / OpenAI, switchable via env var |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Docs | MkDocs Material → GitHub Pages |

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env  # Edit with your API keys
uvicorn app.main:app --port 8001 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System design and data flow |
| [Data Model](docs/data-model.md) | Entity definitions and relationships |
| [AI Editing](docs/ai-editing.md) | LLM pipeline and prompt design |
| [API Reference](docs/api-reference.md) | REST endpoint documentation |
| [Deployment](docs/deployment.md) | Local, Docker, and production setup |
| [Contributing](docs/contributing.md) | Development conventions and workflow |

## Data Model

### Core Entities

| Entity | Description |
|--------|-------------|
| Submission | Community-submitted announcement with headline, body, links, schedule preferences |
| EditVersion | Tracks original → AI suggested → editor final text versions |
| Newsletter | A dated issue of TDR or My UI |
| NewsletterItem | Places a submission into a newsletter section at a position |
| RecurringMessage | Centrally managed editorial content that appears on a cadence |
| NewsletterSection | Section definitions per newsletter type (9 TDR, 5 My UI) |
| StyleRule | Editorial rules loaded into LLM prompts (37 seeded rules) |
| ScheduleConfig | Academic year and summer deadline configurations |
| AllowedValue | Controlled vocabularies for all categorical fields |

### Seed Data

- **14** newsletter sections (9 TDR + 5 My UI)
- **37** editorial style rules (shared + newsletter-specific)
- **4** schedule configurations (academic + summer for each newsletter)
- **10** AllowedValue groups with controlled vocabulary codes

## API Endpoints

| Resource | Endpoints |
|----------|-----------|
| Submissions | CRUD, image upload, link/schedule management |
| AI Edits | Trigger edit, list versions, save final |
| Newsletters | CRUD, assemble, add/reorder items, export .docx |
| Recurring Messages | Staff CRUD plus issue-specific add/skip handling |
| Sections | List by newsletter type |
| Schedule | Active config with computed deadlines |
| Style Rules | CRUD with filtering |
| Allowed Values | List by group |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers
│   │   ├── models/          # SQLAlchemy models (PascalCase columns)
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic + AI pipeline
│   │   ├── utils/           # Text processing, export
│   │   └── db/              # Engine, base, seed
│   ├── data/                # JSON seed files
│   └── tests/               # pytest async tests
├── frontend/
│   └── src/
│       ├── api/             # Typed API clients
│       ├── types/           # TypeScript interfaces
│       ├── components/      # React components
│       └── pages/           # Route pages
├── docs/                    # MkDocs documentation
├── CLAUDE.md                # Claude Code conventions
├── .env.example             # Environment variable template
├── docker-compose.yml       # PostgreSQL for production dev
└── mkdocs.yml               # Documentation site config
```

## License

University of Idaho — Internal Use

## Contributing

See [Contributing Guide](docs/contributing.md) for development setup and conventions.
