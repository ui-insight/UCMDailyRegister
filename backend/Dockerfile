FROM python:3.11-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install the locked runtime set (see scripts/lock_deps.sh). The app itself
# runs from /app and is not installed as a package.
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY . .

RUN mkdir -p /app/uploads && chmod +x /app/docker-entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log", "--log-config", "logging.json"]
