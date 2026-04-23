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
2. **AI Editing** -- submissions are processed by an LLM (Claude, OpenAI, or MindRouter) guided by UCM style rules stored in the database.
3. **Human Review** -- editors review AI suggestions in a side-by-side diff view, accept or revise edits, and finalize copy.
4. **Newsletter Assembly** -- finalized items, recurring editorial messages, and imported external content are placed into newsletter sections, reordered, and previewed.
5. **Word Export** -- the assembled newsletter is exported to a `.docx` file matching UCM's existing templates.

## Tech Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Frontend   | React, TypeScript, TailwindCSS v4, Vite           |
| Backend    | FastAPI, Python 3.12+                              |
| ORM        | SQLAlchemy 2.x (async)                             |
| Database   | SQLite (development), PostgreSQL (prod)            |
| AI         | Abstracted LLM layer (Claude, OpenAI, MindRouter) |
| Export     | python-docx                                        |
| Deployment | Docker Compose (nginx + uvicorn + PostgreSQL)      |

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
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
| 2     | Submission Intake              | Complete    |
| 3     | AI Editing Pipeline            | Complete    |
| 4     | Editor Dashboard               | Complete    |
| 5     | Newsletter Builder & Export    | Complete    |
| 6     | Style Rules & Settings UI      | Complete    |
| 7     | Polish & Testing               | Complete    |

## Recent Updates

- **Apr 2026** -- Data model and UDM alignment documentation refreshed to describe the current 16-table communications-domain extension surface.
- **Mar 2026** -- Recurring message library: staff can manage reusable editorial content, assign it to sections, and auto-surface it in the builder with issue-level skip and restore controls.
- **Mar 2026** -- Side-by-side comparison view: editors can toggle between inline diff and two-column original-vs-AI layout when reviewing edits.
- **Feb 2026** -- MindRouter integration: on-prem AI via the University of Idaho's `mindrouter.uidaho.edu` service, switchable alongside Claude and OpenAI.
- **Feb 2026** -- UI branding alignment: Pride Gold, Clearwater colors, Public Sans typography, and official U of I logo throughout the frontend.
- **Feb 2026** -- Settings page shows active LLM provider, model, and endpoint configuration in real time.
