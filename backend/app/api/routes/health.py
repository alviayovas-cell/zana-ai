from fastapi import APIRouter
from app.core.config import settings
from app.schemas.chat import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
    )
