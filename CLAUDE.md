# UCM Daily Register — Claude Code Conventions

## Project Overview

AI-assisted newsletter production pipeline for the University of Idaho's University Communications and Marketing (UCM) team. Produces two newsletters: **The Daily Register (TDR)** for faculty/staff and **My UI** for students.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 (async) + SQLite (dev) / PostgreSQL (prod)
- **Frontend:** React + TypeScript + TailwindCSS + Vite
- **AI:** Abstracted LLM provider (Claude + OpenAI), switchable via `LLM_PROVIDER` env var
- **Docs:** MkDocs Material → GitHub Pages

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --port 8001 --reload

# Frontend
cd frontend
npm install && npm run dev
```

## Build & Test

```bash
# Backend tests
cd backend && pytest

# Frontend build
cd frontend && npm run build

# Lint
cd backend && ruff check .
cd frontend && npm run lint
```

## Architecture

- **Data Model:** Uses `PascalCase_With_Underscores` column naming (UDM convention shared with VERASUnlimited)
- **Controlled Vocabularies:** All enums stored in `AllowedValue` table, not hard-coded
- **Service Layer:** API routes delegate to service functions in `app/services/`
- **AI Pipeline:** Style rules loaded from DB → injected into LLM system prompt → structured JSON response → diff generation

## Key Conventions

- Import SQLAlchemy as `import sqlalchemy as sa` — always use `sa.` prefix
- All relationships use `lazy="selectin"` for async compatibility
- Pydantic schemas follow `Create`, `Update`, `Response`, `DetailResponse` naming
- Schema field names match model column names (`PascalCase_With_Underscores`)
- TypeScript interfaces mirror Pydantic schemas exactly
- Every model module has a multi-paragraph docstring explaining domain context
- Backend port: **8001** (8000 is occupied on dev machine)
- Frontend Vite dev server proxies `/api` to `http://localhost:8001`

## Project Structure

```
backend/
  app/
    api/v1/         # Route handlers (thin — delegate to services)
    models/         # SQLAlchemy ORM models
    schemas/        # Pydantic request/response schemas
    services/       # Business logic
    services/ai/    # LLM provider abstraction + editing pipeline
    utils/          # Text processing, export, hyperlinks
    db/             # Engine, base, seed data
  data/             # JSON seed files (sections, style rules, schedule, allowed values)
  tests/            # pytest async tests
frontend/
  src/
    api/            # Typed API client functions
    types/          # TypeScript interfaces
    components/     # React components (editor, submission, layout)
    pages/          # Route pages
docs/               # MkDocs documentation source
```

## Environment Variables

See `.env.example` for all configuration options.
