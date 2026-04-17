"""Liveness and readiness endpoints.

`/health` is a liveness probe — returns 200 unconditionally once the app
process is running. Use for basic up/down monitoring.

`/readyz` is a readiness probe — returns 503 if any load-bearing reference
table is empty. Use for orchestrator health checks. An empty reference table
means seeding failed or was skipped, and the app will serve broken
dropdowns, validations, and FK lookups.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.allowed_value import AllowedValue
from app.models.schedule_config import ScheduleConfig
from app.models.section import NewsletterSection
from app.models.style_rule import StyleRule

router = APIRouter(tags=["health"])

REQUIRED_VOCABULARIES = {
    "allowed_values": AllowedValue,
    "newsletter_sections": NewsletterSection,
    "schedule_configs": ScheduleConfig,
    "style_rules": StyleRule,
}


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/readyz")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    counts: dict[str, int] = {}
    for name, model in REQUIRED_VOCABULARIES.items():
        result = await db.execute(select(func.count()).select_from(model))
        counts[name] = result.scalar_one()

    empty = sorted(name for name, count in counts.items() if count == 0)

    if empty:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "empty_tables": empty,
                "counts": counts,
                "hint": "run `python -m app.db.seed` or verify entrypoint ran",
            },
        )

    return {"status": "ready", "counts": counts}
