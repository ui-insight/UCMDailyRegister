FROM python:3.11-slim@sha256:65bd3d9f1d7fa268dd1909973ba7eb4bdf41f6dcf2cfbe76ba9528b170f3fd79

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install the locked runtime set from uv.lock into the image's Python. The app
# itself runs from /app and is not installed as a package.
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/usr/local UV_LINK_MODE=copy UV_NO_CACHE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --inexact --extra postgres --no-install-project

COPY . .

RUN mkdir -p /app/uploads && chmod +x /app/docker-entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log", "--log-config", "logging.json"]
