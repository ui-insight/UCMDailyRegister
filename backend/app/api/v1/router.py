from fastapi import APIRouter

from app.api.v1.submissions import router as submissions_router

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health_check():
    return {"status": "ok"}


router.include_router(submissions_router)
