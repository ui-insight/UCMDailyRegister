# Deployment

## Prerequisites

| Tool       | Version   | Notes                            |
|------------|-----------|----------------------------------|
| Python     | 3.12+     | Required for backend             |
| Node.js    | 22+       | Required for frontend            |
| PostgreSQL | 15+       | Production only (SQLite for dev) |
| Docker     | 24+       | Required for production deploys  |

## Local Development Setup

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -e ".[dev]"

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

Create a `.env` file in the project root (for Docker) or `backend/` directory (for local dev):

```bash
# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./ucm_newsletter.db

# LLM Provider ("claude", "openai", or "mindrouter")
LLM_PROVIDER=claude

# Anthropic (required when LLM_PROVIDER=claude)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-20250514

# OpenAI (required when LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# MindRouter — University of Idaho on-prem AI (required when LLM_PROVIDER=mindrouter)
MINDROUTER_API_KEY=mr2_...
MINDROUTER_ENDPOINT_URL=https://mindrouter.uidaho.edu/v1/chat/completions
MINDROUTER_MODEL=Qwen/Qwen3-32B

# CORS (development)
CORS_ORIGINS=http://localhost:5173
```

!!! warning "Port Conflict"
    Port 8000 may be in use by another application. This project defaults to **port 8001** for the backend.

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

## Docker Production Deployment

The project uses Docker Compose with two application containers connected to an
external PostgreSQL network:

```
┌──────────────────────────────────────────────────────────┐
│  Docker Network (custom 10.x.x.x subnet)                │
│                                                          │
│  ┌────────────┐   ┌────────────┐                        │
│  │  frontend   │──>│  backend   │──> external Postgres  │
│  │  (nginx)    │   │ (uvicorn)  │    on insight-db-net  │
│  │  :80        │   │  :8001     │                        │
│  └──────┬─────┘   └────────────┘                        │
│         │                                                │
└─────────┼────────────────────────────────────────────────┘
          │
     HOST_PORT (9280/9290)
```

- **frontend** (nginx) -- the only container with a host port mapping. Serves the React build and reverse-proxies `/api/` to the backend.
- **backend** (uvicorn) -- internal only, port 8001 on the Docker network.
- **database** -- external PostgreSQL instance reachable on the `insight-db-net` Docker network.

`docker-compose.yml` does not create a database container. You must supply
`DATABASE_URL` in the environment and ensure the shared `insight-db-net`
external network already exists on the target host.

### Target Server

| Setting  | Value                                |
|----------|--------------------------------------|
| Host     | `devops@openera.insight.uidaho.edu`  |
| Repo     | `/home/devops/UCMDailyRegister`      |
| Network  | Custom `10.x.x.x` subnet (not Docker default `172.x.x.x`) |

### Environments

| Environment | URL                                   | Host Port | Subnet          | Env File    |
|-------------|---------------------------------------|-----------|-----------------|-------------|
| **prod**    | `https://ucmnews.insight.uidaho.edu`  | 9280      | 10.20.9.0/24    | `.env.prod` |
| **dev**     | `https://ucmnews-dev.insight.uidaho.edu` | 9290   | 10.20.10.0/24   | `.env`      |

!!! warning "Separate Subnets"
    Prod and dev run in parallel on the same host using different Docker project names and non-overlapping subnets. The dev environment uses `10.20.10.0/24` to avoid collisions with prod's `10.20.9.0/24`.

### Quick Deploy

```bash
# SSH into the server
ssh devops@openera.insight.uidaho.edu
cd /home/devops/UCMDailyRegister

# Pull latest code
git pull origin main

# Deploy prod
./deploy.sh prod

# Deploy dev
./deploy.sh dev
```

The deploy script rebuilds the stack, runs `alembic upgrade head`, and then
smoke-tests the frontend and key API routes before returning success.

### Environment File Template

Create `.env.prod` (or `.env` for dev) in the project root on the server:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://ucm:<password>@insight-db:5432/ucm_newsletter
# For dev, point to the dev database instead:
# DATABASE_URL=postgresql+asyncpg://ucm:<password>@insight-db:5432/ucm_newsletter_dev

# LLM Provider
LLM_PROVIDER=mindrouter

# MindRouter
MINDROUTER_API_KEY=mr2_...
MINDROUTER_ENDPOINT_URL=https://mindrouter.uidaho.edu/v1/chat/completions
MINDROUTER_MODEL=openai/gpt-oss-120b

# Docker
HOST_PORT=9280          # 9290 for dev
DOCKER_SUBNET=10.20.9.0/24  # 10.20.10.0/24 for dev
```

### Nginx Proxy Timeouts

The frontend nginx config includes extended timeouts for the `/api/` proxy to accommodate slower on-prem model inference:

| Directive              | Value  | Purpose                                   |
|------------------------|--------|-------------------------------------------|
| `proxy_read_timeout`   | 300s   | MindRouter AI edits can take several minutes |
| `proxy_connect_timeout`| 10s    | Fast fail on backend unreachable          |
| `proxy_send_timeout`   | 60s    | Allow large request bodies                |

### Checking Status

```bash
# List all running containers
docker ps --filter "name=ucmnews"

# Check backend logs
docker logs ucmnews-prod-backend-1 --tail 50

# Run the full deploy workflow
./deploy.sh prod

# Verify LLM provider config
curl -s http://localhost:9280/api/v1/settings/ai | python3 -m json.tool

# Smoke checks
curl http://localhost:9280/api/v1/health
curl http://localhost:9280/api/v1/submissions/?limit=1
```

## Production Considerations

??? info "Production Checklist"
    - **Database** -- set `DATABASE_URL` explicitly to the assigned shared Postgres database
    - **CORS** -- restrict `CORS_ORIGINS` to the production frontend domain
    - **File uploads** -- configure persistent storage for submission images (Docker volume or mounted directory)
    - **HTTPS** -- terminate TLS at a reverse proxy (nginx, Caddy, or cloud load balancer)
    - **Secrets** -- load API keys from environment variables, not committed `.env` files
    - **Migrations** -- use `./deploy.sh <dev|prod>` so `alembic upgrade head` runs before smoke checks
    - **Backups** -- the `pgdata` Docker volume should be backed up regularly
