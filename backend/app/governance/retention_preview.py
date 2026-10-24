"""Count aged data for retention review without returning content or deleting it.

The caller supplies a cutoff approved for inventory. Age is not a disposal
permission: this tool cannot evaluate institutional holds or archive policy.
"""

import argparse
import asyncio
import json
from datetime import date, datetime, time

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import ProductFeedback
from app.models.ai_edit_task import AIEditTask
from app.models.harvested_event import HarvestedEvent
from app.models.newsletter import NewsletterItem
from app.models.ops_need_assessment import OpsNeedAssessment
from app.models.submission import Submission


async def preview(db: AsyncSession, before: date) -> dict:
    cutoff = datetime.combine(before, time.min)
    aged = sa.select(Submission.Id).where(Submission.Updated_At < cutoff)

    async def count(model, *conditions) -> int:
        result = await db.execute(sa.select(sa.func.count()).select_from(model).where(*conditions))
        return result.scalar_one()

    external_ids = sa.select(HarvestedEvent.Id).where(
        sa.func.coalesce(HarvestedEvent.Event_End, HarvestedEvent.Event_Start) < cutoff
    )
    return {
        "mode": "inventory_only",
        "before": before.isoformat(),
        "disposal_authorized": False,
        "aged_submissions": await count(Submission, Submission.Id.in_(aged)),
        "associated_ai_edit_tasks": await count(AIEditTask, AIEditTask.Submission_Id.in_(aged)),
        "aged_sources_with_issue_references": await count(
            Submission, Submission.Id.in_(aged),
            sa.exists().where(NewsletterItem.Submission_Id == Submission.Id),
        ),
        "aged_sources_with_image_references": await count(
            Submission, Submission.Id.in_(aged), Submission.Image_Path.is_not(None),
        ),
        "aged_feedback_by_last_update": await count(
            ProductFeedback, ProductFeedback.Updated_At < cutoff,
        ),
        "aged_harvested_events": await count(HarvestedEvent, HarvestedEvent.Id.in_(external_ids)),
        "associated_ops_assessments": await count(
            OpsNeedAssessment, OpsNeedAssessment.Harvested_Event_Id.in_(external_ids),
        ),
    }


async def _run(before: date) -> None:
    from app.db.engine import async_session_factory, engine

    try:
        async with async_session_factory() as db:
            print(json.dumps(await preview(db, before), indent=2))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    asyncio.run(_run(args.before))


if __name__ == "__main__":
    main()
