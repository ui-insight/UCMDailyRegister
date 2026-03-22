from fastapi import APIRouter

from app.api.v1.submissions import router as submissions_router
from app.api.v1.style_rules import router as style_rules_router
from app.api.v1.ai_edits import router as ai_edits_router
from app.api.v1.newsletters import router as newsletters_router
from app.api.v1.recurring_messages import router as recurring_messages_router
from app.api.v1.sections import router as sections_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.allowed_values import router as allowed_values_router
from app.api.v1.settings import router as settings_router

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health_check():
    return {"status": "ok"}


router.include_router(submissions_router)
router.include_router(style_rules_router)
router.include_router(ai_edits_router)
router.include_router(newsletters_router)
router.include_router(recurring_messages_router)
router.include_router(sections_router)
router.include_router(schedule_router)
router.include_router(allowed_values_router)
router.include_router(settings_router)
