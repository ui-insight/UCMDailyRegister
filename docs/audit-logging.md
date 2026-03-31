# Audit Logging & Monitoring

## Overview

This document defines what events should be logged, how logs should be structured, and the monitoring strategy for the UCM Daily Register in production.

---

## Events to Log

### Submission Lifecycle

| Event | Log Level | Data to Include | PII Consideration |
|-------|-----------|----------------|-------------------|
| Submission created | INFO | submission_id, category, target_newsletter, timestamp | Do NOT log submitter_name or email |
| Submission updated | INFO | submission_id, changed_fields, user_role, timestamp | Log field names only, not values |
| Image uploaded | INFO | submission_id, file_size, content_type, timestamp | Do NOT log original filename |
| Submission status change | INFO | submission_id, old_status, new_status, timestamp | — |

### AI Editing Pipeline

| Event | Log Level | Data to Include | PII Consideration |
|-------|-----------|----------------|-------------------|
| AI edit requested | INFO | submission_id, provider, model, timestamp | — |
| AI edit completed | INFO | submission_id, provider, model, token_count, duration_ms, confidence | — |
| AI edit failed | ERROR | submission_id, provider, model, error_type, error_message | Do NOT log prompt content |
| Provider fallback | WARN | submission_id, failed_provider, fallback_provider | — |

### Newsletter Operations

| Event | Log Level | Data to Include | PII Consideration |
|-------|-----------|----------------|-------------------|
| Newsletter created | INFO | newsletter_id, type, publish_date | — |
| Newsletter item added | INFO | newsletter_id, submission_id, section_id | — |
| Newsletter exported | INFO | newsletter_id, format, user_role | — |
| Calendar events imported | INFO | newsletter_id, event_count, source_url | — |
| Job postings imported | INFO | newsletter_id, posting_count, source_url | — |

### Configuration Changes

| Event | Log Level | Data to Include | PII Consideration |
|-------|-----------|----------------|-------------------|
| Style rule created/updated | INFO | rule_id, action, user_role | — |
| Schedule config changed | INFO | config_id, changed_fields | — |
| AI provider setting changed | WARN | old_provider, new_provider | — |

### Security Events

| Event | Log Level | Data to Include | PII Consideration |
|-------|-----------|----------------|-------------------|
| Unauthorized access attempt | WARN | endpoint, user_role_header, client_ip | — |
| Invalid input rejected | WARN | endpoint, validation_error_type | Do NOT log input values |
| Rate limit exceeded | WARN | endpoint, client_ip | — |

---

## Log Format

Use structured JSON logging for machine parseability:

```json
{
  "timestamp": "2026-03-31T14:30:00.000Z",
  "level": "INFO",
  "event": "ai_edit_completed",
  "service": "ucm-newsletter-backend",
  "environment": "prod",
  "data": {
    "submission_id": "a1b2c3d4-...",
    "provider": "mindrouter",
    "model": "openai/gpt-oss-120b",
    "token_count": 1247,
    "duration_ms": 3200,
    "confidence": 0.87
  }
}
```

### Implementation

FastAPI/uvicorn logging can be configured with Python's `logging` module using a JSON formatter:

```python
import logging
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "service": "ucm-newsletter-backend",
            "environment": os.getenv("ENVIRONMENT", "dev"),
        }
        if hasattr(record, "data"):
            log_entry["data"] = record.data
        return json.dumps(log_entry)
```

---

## Log Retention

| Log Type | Retention | Storage |
|----------|-----------|---------|
| Application logs (INFO) | 90 days | Container stdout → log aggregation |
| Security logs (WARN+) | 1 year | Container stdout → log aggregation |
| Error logs | 1 year | Container stdout → log aggregation |

Align with data governance retention policies. PII must never appear in logs.

---

## Monitoring Strategy

### Phase 1: Manual Checks (Current)

The `deploy.sh` smoke tests verify basic functionality after each deployment:

- Frontend root page loads
- SPA routes respond
- API health endpoint responds
- Settings API returns valid JSON
- Submissions API is accessible

### Phase 2: Automated Health Checks (Recommended)

Add Docker health checks to `docker-compose.yml`:

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/api/v1/settings/ai"]
    interval: 60s
    timeout: 10s
    retries: 3
    start_period: 30s

frontend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:80/"]
    interval: 60s
    timeout: 10s
    retries: 3
```

### Phase 3: External Monitoring (Future)

Consider adding:

- **Uptime monitoring:** External ping to `https://ucmnews.insight.uidaho.edu/` (e.g., UptimeRobot, university monitoring tools)
- **Log aggregation:** Forward container logs to a centralized system (ELK, Loki, or university-provided SIEM)
- **Alerting:** Email or Slack notification on container restart, health check failure, or error rate spike

---

## Metrics to Track

| Metric | Source | Purpose |
|--------|--------|---------|
| Submissions per day | Application logs | Usage tracking |
| AI edit success rate | Application logs | Provider reliability |
| AI edit latency (p50, p95) | Application logs | Performance baseline |
| Newsletter exports per week | Application logs | Output tracking |
| Error rate | Application logs | System health |
| Container restarts | Docker | Stability |
| Disk usage | Host OS | Capacity planning |
| Database size | PostgreSQL | Growth tracking |

---

## Open Items

- [ ] Implement structured JSON logging in FastAPI backend
- [ ] Add Docker health checks to docker-compose.yml
- [ ] Set up external uptime monitoring
- [ ] Evaluate university-provided log aggregation options
- [ ] Define alerting thresholds and notification channels
