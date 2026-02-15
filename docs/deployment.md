# Deployment

## Prerequisites

| Tool       | Version   | Notes                            |
|------------|-----------|----------------------------------|
| Python     | 3.12+     | Required for backend             |
| Node.js    | 22+       | Required for frontend            |
| PostgreSQL | 15+       | Production only (SQLite for dev) |
| Docker     | 24+       | Optional, for containerized DB   |

## Local Development Setup

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (see below)

# Seed the database
python -m app.db.seed

# Start the dev server
uvicorn app.main:app --port 8001 --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The Vite dev server starts on port **5173** and proxies `/api` requests to the backend at port **8001**.

### Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# LLM Provider
LLM_PROVIDER=claude          # or "openai"
ANTHROPIC_API_KEY=sk-ant-... # if using Claude
OPENAI_API_KEY=sk-...        # if using OpenAI

# CORS (development)
CORS_ORIGINS=http://localhost:5173
```

!!! warning "Port Conflict"
    Port 8000 may be in use by another application. This project defaults to **port 8001** for the backend.

## Docker PostgreSQL

For local development with PostgreSQL instead of SQLite, use docker-compose:

```bash
docker-compose up -d db
```

Then update your `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://ucm:ucm_password@localhost:5432/ucm_newsletter
```

## Database Seeding

The seed script populates the database with initial reference data:

```bash
cd backend
source .venv/bin/activate
python -m app.db.seed
```

This creates:

- **14 newsletter sections** (9 for TDR, 5 for My UI)
- **37 style rules** (shared + newsletter-specific)
- **4 schedule configs** (daily weekday for TDR, weekly Monday for My UI)
- **AllowedValue records** across all 10 value groups

!!! note "Idempotent Seeding"
    The seed script checks for existing data before inserting. It is safe to run multiple times.

## Running Dev Servers

Start both servers in separate terminals:

**Terminal 1 -- Backend:**
```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --port 8001 --reload
```

**Terminal 2 -- Frontend:**
```bash
cd frontend
npm run dev
```

Access the application at `http://localhost:5173`. The API is also directly available at `http://localhost:8001/api/v1/`.

Interactive API docs are served at `http://localhost:8001/docs` (Swagger UI) and `http://localhost:8001/redoc` (ReDoc).

## Production Considerations

??? info "Production Checklist"
    - **Database** -- use PostgreSQL with `postgresql+asyncpg://` connection string
    - **CORS** -- restrict `CORS_ORIGINS` to the production frontend domain
    - **File uploads** -- configure persistent storage for submission images (S3 or mounted volume)
    - **HTTPS** -- terminate TLS at a reverse proxy (nginx, Caddy, or cloud load balancer)
    - **Process manager** -- run uvicorn behind gunicorn with uvicorn workers: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker`
    - **Secrets** -- load API keys from a secrets manager, not `.env` files
    - **Migrations** -- run `alembic upgrade head` as part of the deployment pipeline
