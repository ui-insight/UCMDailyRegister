# UCM Newsletter Builder

The UCM Newsletter Builder is an AI-assisted production pipeline for the University of Idaho's University Communications and Marketing (UCM) office. It streamlines the creation of two campus newsletters:

- **The Daily Register (TDR)** -- faculty and staff newsletter, published every weekday
- **My UI** -- student newsletter, published weekly on Mondays

## Workflow

The system follows a five-stage pipeline:

```
Submission Intake --> AI Editing --> Human Review --> Newsletter Assembly --> Word Export
```

1. **Submission Intake** -- campus contributors submit announcements through a web form with scheduling preferences, links, and optional images.
2. **AI Editing** -- submissions are processed by an LLM (Claude or OpenAI) guided by UCM style rules stored in the database.
3. **Human Review** -- editors review AI suggestions in a side-by-side diff view, accept or revise edits, and finalize copy.
4. **Newsletter Assembly** -- finalized items are placed into newsletter sections, reordered, and previewed.
5. **Word Export** -- the assembled newsletter is exported to a `.docx` file matching UCM's existing templates.

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Frontend   | React, TypeScript, TailwindCSS, Vite    |
| Backend    | FastAPI, Python 3.12+                   |
| ORM        | SQLAlchemy 2.x (async)                  |
| Database   | SQLite (development), PostgreSQL (prod) |
| AI         | Abstracted LLM layer (Claude + OpenAI)  |
| Export     | python-docx                             |

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.db.seed
uvicorn app.main:app --port 8001 --reload

# Frontend
cd frontend
npm install
npm run dev
```

!!! info "Port Note"
    The backend runs on port **8001** by default. The Vite dev server proxies `/api` requests to this port.

## Project Status

| Phase | Description                    | Status      |
|-------|--------------------------------|-------------|
| 1     | Foundation & Scaffold          | Complete    |
| 2     | Submission Intake              | Not Started |
| 3     | AI Editing Pipeline            | Not Started |
| 4     | Editor Dashboard               | Not Started |
| 5     | Newsletter Builder & Export    | Not Started |
| 6     | Style Rules & Settings UI      | Not Started |
| 7     | Polish & Testing               | Not Started |
